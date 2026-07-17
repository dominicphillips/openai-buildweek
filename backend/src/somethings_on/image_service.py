from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import uuid
from pathlib import Path
from typing import Literal, Protocol

from openai import AsyncOpenAI
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict

from .casting import CastingPresetCatalog
from .design_store import SQLiteDesignStore
from .models import (
    AssetRecord,
    CastingControls,
    CastingPresetRecord,
    DesignVersionRecord,
    PresentationCreateInput,
    PresentationRenderRecord,
)

Image.MAX_IMAGE_PIXELS = 25_000_000
_ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}
ImageQuality = Literal["low", "medium", "high"]


class InvalidImageError(ValueError):
    pass


class ImageGenerationUnavailable(RuntimeError):
    pass


class CanonicalDesignAssetRequired(RuntimeError):
    pass


class GarmentPreservationAssessment(BaseModel):
    """Structured vision assessment for a generated lookbook candidate."""

    model_config = ConfigDict(extra="forbid")

    preserves_garment: bool
    changed_or_hidden_details: list[str]
    summary: str


class ImageProvider(Protocol):
    model: str

    async def create(
        self,
        prompt: str,
        reference_path: Path | None = None,
        *,
        quality: ImageQuality = "low",
    ) -> bytes: ...


class GarmentPreservationAssessor(Protocol):
    async def assess_preservation(
        self,
        *,
        canonical_path: Path,
        presentation_content: bytes,
    ) -> GarmentPreservationAssessment: ...


class OpenAIImageProvider:
    """Direct gpt-image-2 rendering plus structured multimodal preservation review."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-image-2",
        assessment_model: str = "gpt-5.6",
    ) -> None:
        self.model = model
        self.assessment_model = assessment_model
        self.client = AsyncOpenAI(api_key=api_key)

    async def create(
        self,
        prompt: str,
        reference_path: Path | None = None,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        if reference_path is None:
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size="1024x1024",
                quality=quality,
            )
        else:
            with reference_path.open("rb") as reference:
                response = await self.client.images.edit(
                    model=self.model,
                    image=reference,
                    prompt=prompt,
                    size="1024x1024",
                    quality=quality,
                )

        if not response.data or not response.data[0].b64_json:
            raise ImageGenerationUnavailable("The image provider returned no image data.")
        try:
            return base64.b64decode(response.data[0].b64_json, validate=True)
        except ValueError as error:
            raise ImageGenerationUnavailable(
                "The image provider returned invalid image data."
            ) from error

    async def assess_preservation(
        self,
        *,
        canonical_path: Path,
        presentation_content: bytes,
    ) -> GarmentPreservationAssessment:
        """Compare garment identity with vision rather than brittle pixel similarity."""

        canonical_content = await asyncio.to_thread(canonical_path.read_bytes)
        response = await self.client.responses.parse(
            model=self.assessment_model,
            store=False,
            max_output_tokens=400,
            instructions=(
                "You are a conservative fashion production reviewer. Compare only the supplied "
                "garment, not the model, body, pose, camera, lighting, wrinkles, or background. "
                "Mark preserves_garment true only when the candidate visibly preserves the "
                "canonical garment's category, silhouette, cut, construction, proportions, "
                "color, graphics, finish, closures, and placement. Normal perspective and fabric "
                "drape are allowed. If an important detail is changed, invented, covered, cropped, "
                "or too unclear to verify, return false and name those details. Do not use pixel "
                "similarity; make a semantic design-preservation judgment."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Image 1: canonical garment design."},
                        {
                            "type": "input_image",
                            "image_url": self._png_data_url(canonical_content),
                            "detail": "high",
                        },
                        {
                            "type": "input_text",
                            "text": "Image 2: generated lookbook candidate to validate.",
                        },
                        {
                            "type": "input_image",
                            "image_url": self._png_data_url(presentation_content),
                            "detail": "high",
                        },
                    ],
                }
            ],
            text_format=GarmentPreservationAssessment,
        )
        for output in response.output:
            if output.type != "message":
                continue
            for item in output.content:
                parsed = getattr(item, "parsed", None)
                if isinstance(parsed, GarmentPreservationAssessment):
                    return parsed
        raise ImageGenerationUnavailable(
            "The garment preservation review did not return a usable result. "
            "Your design is unchanged."
        )

    @staticmethod
    def _png_data_url(content: bytes) -> str:
        return f"data:image/png;base64,{base64.b64encode(content).decode('ascii')}"


class DesignImageService:
    def __init__(
        self,
        *,
        store: SQLiteDesignStore,
        asset_root: Path,
        provider: ImageProvider | None,
        image_model: str,
        casting_catalog: CastingPresetCatalog | None = None,
        preservation_assessor: GarmentPreservationAssessor | None = None,
    ) -> None:
        self.store = store
        self.asset_root = asset_root
        self.provider = provider
        self.image_model = image_model
        self.casting_catalog = casting_catalog
        self.preservation_assessor = preservation_assessor

    async def initialize(self) -> None:
        self.asset_root.mkdir(parents=True, exist_ok=True)

    async def ingest_reference(
        self,
        *,
        project_id: str,
        content: bytes,
        content_type: str,
        original_name: str,
    ) -> AssetRecord:
        if content_type not in _ALLOWED_UPLOAD_TYPES:
            raise InvalidImageError("Use a PNG, JPEG, or WEBP image.")
        normalized, width, height = await asyncio.to_thread(self._normalize_image, content)
        storage_path = await self._write_asset(project_id, normalized)
        return await self.store.add_asset(
            project_id=project_id,
            kind="reference",
            storage_path=storage_path,
            mime_type="image/png",
            width=width,
            height=height,
            sha256=hashlib.sha256(normalized).hexdigest(),
            original_name=Path(original_name).name[:180],
        )

    async def create_revision(
        self,
        *,
        project_id: str,
        requested_change: str,
        preserve: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> DesignVersionRecord:
        if self.provider is None:
            raise ImageGenerationUnavailable(
                "Image generation is not configured. Add OPENAI_API_KEY and restart the service."
            )

        project = await self.store.ensure_project(project_id)
        current = project.current_version
        requested_change = requested_change.strip()[:800]
        if not requested_change:
            raise ValueError("Describe one concrete design change.")
        keep = self._clean_list(preserve)
        exclude = self._clean_list(avoid)
        prompt = self._build_prompt(
            object_name=project.object_name,
            taste_traits=[tag for signal in project.taste_signals for tag in signal.tags],
            requested_change=requested_change,
            preserve=keep,
            avoid=exclude,
            is_edit=bool(current and current.asset_id),
        )

        job = await self.store.create_generation_job(
            project_id=project_id,
            base_version_id=current.id if current else None,
            requested_change=requested_change,
            model=self.image_model,
        )
        await self.store.update_generation_job(job.id, status="running")

        try:
            reference_path = None
            if current and current.asset_id:
                reference_path = await self.resolve_asset(current.asset_id)
            # Design iterations are deliberately fast drafts; refinement can opt into
            # higher fidelity later without making every exploratory branch expensive.
            raw_image = await self.provider.create(prompt, reference_path, quality="low")
            normalized, width, height = await asyncio.to_thread(self._normalize_image, raw_image)
            storage_path = await self._write_asset(project_id, normalized)
            asset = await self.store.add_asset(
                project_id=project_id,
                kind="generated",
                storage_path=storage_path,
                mime_type="image/png",
                width=width,
                height=height,
                sha256=hashlib.sha256(normalized).hexdigest(),
            )
            version = await self.store.add_design_version(
                project_id=project_id,
                parent_version_id=current.id if current else None,
                asset_id=asset.id,
                generation_job_id=job.id,
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
                prompt=prompt,
            )
            await self.store.update_generation_job(
                job.id,
                status="succeeded",
                output_asset_id=asset.id,
            )
            return version
        except Exception as error:
            await self.store.update_generation_job(
                job.id,
                status="failed",
                error_code=self._error_code(error),
            )
            if isinstance(error, ImageGenerationUnavailable | InvalidImageError | ValueError):
                raise
            raise ImageGenerationUnavailable(
                "The image edit could not be completed. The prior version is unchanged."
            ) from error

    async def create_presentation(
        self,
        *,
        project_id: str,
        request: PresentationCreateInput,
    ) -> PresentationRenderRecord:
        project = await self.store.get_project(project_id)
        if self.casting_catalog is None:
            raise ImageGenerationUnavailable(
                "Lookbook casting is unavailable. Your design is unchanged."
            )
        preset = self.casting_catalog.get(request.preset_id)
        if request.design_version_id:
            version = await self.store.get_design_version(
                project_id,
                request.design_version_id,
            )
        else:
            version = project.current_version
        if version is None or version.asset_id is None:
            raise CanonicalDesignAssetRequired(
                "Generate a design version before making a lookbook view."
            )
        if self.provider is None:
            raise ImageGenerationUnavailable(
                "Lookbook rendering is not configured. Your design is unchanged."
            )
        if self.preservation_assessor is None:
            raise ImageGenerationUnavailable(
                "Lookbook preservation review is not configured. Your design is unchanged."
            )

        prompt = self._build_presentation_prompt(
            preset=preset,
            controls=request.controls,
            global_rules=self.casting_catalog.collection.subject_policy.global_prompt_rules,
        )
        render = await self.store.create_presentation_render(
            project_id=project_id,
            design_version_id=version.id,
            preset_id=preset.id,
            controls=request.controls,
            prompt=prompt,
            avoid=preset.avoid_list,
            model=self.image_model,
        )
        await self.store.update_presentation_render(render.id, status="running")

        try:
            reference_path = await self.resolve_asset(version.asset_id)
            # A presentation is a reviewable lookbook artifact, so it uses medium
            # render quality while exploratory garment revisions remain low quality.
            raw_image = await self.provider.create(prompt, reference_path, quality="medium")
            normalized, width, height = await asyncio.to_thread(self._normalize_image, raw_image)
            assessment = await self.preservation_assessor.assess_preservation(
                canonical_path=reference_path,
                presentation_content=normalized,
            )
            if not assessment.preserves_garment:
                return await self.store.update_presentation_render(
                    render.id,
                    status="failed",
                    error_code="garment_drift",
                )
            storage_path = await self._write_asset(project_id, normalized)
            asset = await self.store.add_asset(
                project_id=project_id,
                kind="generated",
                storage_path=storage_path,
                mime_type="image/png",
                width=width,
                height=height,
                sha256=hashlib.sha256(normalized).hexdigest(),
            )
            return await self.store.update_presentation_render(
                render.id,
                status="ready",
                output_asset_id=asset.id,
            )
        except Exception as error:
            await self.store.update_presentation_render(
                render.id,
                status="failed",
                error_code=self._error_code(error),
            )
            if isinstance(error, ImageGenerationUnavailable):
                raise
            raise ImageGenerationUnavailable(
                "That lookbook view did not finish. Your design is unchanged."
            ) from error

    async def resolve_asset(self, asset_id: str) -> Path:
        _, storage_path = await self.store.get_asset_location(asset_id)
        root = self.asset_root.resolve()
        path = (root / storage_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise InvalidImageError("The stored asset is unavailable.")
        return path

    async def _write_asset(self, project_id: str, content: bytes) -> str:
        project_folder = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:18]
        relative_path = Path(project_folder) / f"{uuid.uuid4().hex}.png"
        destination = self.asset_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(destination.write_bytes, content)
        return relative_path.as_posix()

    @staticmethod
    def _normalize_image(content: bytes) -> tuple[bytes, int, int]:
        try:
            with Image.open(io.BytesIO(content)) as source:
                source.verify()
            with Image.open(io.BytesIO(content)) as source:
                image = ImageOps.exif_transpose(source)
                image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                output = io.BytesIO()
                image.save(output, format="PNG", optimize=True)
                return output.getvalue(), image.width, image.height
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise InvalidImageError("The uploaded file is not a safe, readable image.") from error

    @staticmethod
    def _clean_list(values: list[str] | None) -> list[str]:
        if not values:
            return []
        return [value.strip()[:120] for value in values if value.strip()][:8]

    @staticmethod
    def _build_prompt(
        *,
        object_name: str,
        taste_traits: list[str],
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
        is_edit: bool,
    ) -> str:
        mode = (
            "Edit the supplied design study while keeping its identity and camera view stable."
            if is_edit
            else "Create the first original design study from scratch."
        )
        traits = ", ".join(dict.fromkeys(taste_traits)) or "considered proportion and construction"
        keep = ", ".join(preserve) or "the object category and clear front-view readability"
        exclusions = ", ".join(avoid) or "unrequested changes"
        return (
            f"{mode}\n"
            f"Object: {object_name}.\n"
            f"Requested authored change: {requested_change}.\n"
            f"Preserve: {keep}.\n"
            f"Avoid: {exclusions}.\n"
            f"Abstract taste traits: {traits}. Translate these into original proportion, material, "
            "construction, and finish decisions; do not copy any identifiable garment.\n"
            "Show one centered fashion product, full object visible, front view, neutral charcoal "
            "studio background, soft directional light, editorial product-study realism. No "
            "person, no logo, no brand mark, no signature graphic, no readable text, no watermark, "
            "no collage."
        )

    @staticmethod
    def _build_presentation_prompt(
        *,
        preset: CastingPresetRecord,
        controls: CastingControls,
        global_rules: list[str],
    ) -> str:
        control_lines = [
            f"Body build: {controls.body_build}.",
            f"Stature: {controls.stature}.",
            f"Skin tone: {controls.skin_tone}.",
            f"Presentation: {controls.presentation}.",
            f"Adult age: {controls.adult_age}.",
            f"Pose and access: {controls.pose_access}.",
            f"Continuity: {controls.continuity}.",
        ]
        return "\n\n".join(
            (
                preset.prompt_fragment,
                "Independent casting controls:\n" + "\n".join(control_lines),
                "Required collection-wide rules:\n- " + "\n- ".join(global_rules),
                "Avoid:\n- " + "\n- ".join(preset.avoid_list),
            )
        )

    @staticmethod
    def _error_code(error: Exception) -> str:
        code = getattr(error, "code", None)
        if isinstance(code, str) and code:
            return code[:80]
        return type(error).__name__[:80]

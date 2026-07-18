from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
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
    DesignCandidateRecord,
    DesignVersionRecord,
    PresentationCreateInput,
    PresentationRenderRecord,
    TechnicalViewRecord,
    TechnicalViewRole,
)

Image.MAX_IMAGE_PIXELS = 25_000_000
_ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}
ImageQuality = Literal["low", "medium", "high"]
TECHNICAL_VIEW_ROLES: tuple[TechnicalViewRole, ...] = ("back", "left", "right")
_TECHNICAL_VIEW_DIRECTIONS: dict[TechnicalViewRole, str] = {
    "back": "direct back view",
    "left": "left-side profile, with the camera looking at the garment's left side",
    "right": "right-side profile, with the camera looking at the garment's right side",
}
logger = logging.getLogger(__name__)


class InvalidImageError(ValueError):
    pass


class ImageGenerationUnavailable(RuntimeError):
    pass


class CanonicalDesignAssetRequired(RuntimeError):
    pass


class RevisionBaseAssetRequired(RuntimeError):
    pass


def build_technical_view_prompt(*, object_name: str, role: TechnicalViewRole) -> str:
    """Build an inspection-angle edit prompt that forbids garment redesign."""

    direction = _TECHNICAL_VIEW_DIRECTIONS[role]
    return (
        "Edit the supplied exact canonical garment raster into one derived technical "
        "inspection view. Use that raster as the sole visual source of truth.\n"
        f"Object: {object_name}.\n"
        f"Required view: {direction}.\n"
        "Change only the viewpoint. Preserve the exact garment identity, category, silhouette, "
        "cut, measurements, proportions, layering, materials, construction, seam placement, "
        "color, graphics, distressing, finish, trims, closures, hardware, and all authored "
        "details. Do not redesign, restyle, simplify, add, remove, replace, mirror, or reinterpret "
        "the garment. Infer only occluded construction needed to show this angle, conservatively "
        "and consistently with the canonical raster. Keep the full object visible at a comparable "
        "scale on the same neutral studio background with matching lighting. Preserve any "
        "existing authored graphics, markings, and text exactly. Return one garment only. No "
        "person; no new logo, brand mark, readable text, watermark, prop, or collage."
    )


class GarmentPreservationAssessment(BaseModel):
    """Structured vision assessment for a generated lookbook candidate."""

    model_config = ConfigDict(extra="forbid")

    preserves_garment: bool
    changed_or_hidden_details: list[str]
    summary: str


class ImageProvider(Protocol):
    model: str

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes: ...

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes: ...

    async def generate_candidates(
        self,
        prompt: str,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]: ...

    async def edit_candidates(
        self,
        prompt: str,
        reference_path: Path,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]: ...


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

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size="1024x1536",
            quality=quality,
        )
        return self._decode_image_response(response)

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        with reference_path.open("rb") as reference:
            response = await self.client.images.edit(
                model=self.model,
                image=reference,
                prompt=prompt,
                size="1024x1536",
                quality=quality,
            )
        return self._decode_image_response(response)

    async def generate_candidates(
        self,
        prompt: str,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]:
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size="1024x1536",
            quality=quality,
            n=count,
        )
        return self._decode_image_responses(response, expected_count=count)

    async def edit_candidates(
        self,
        prompt: str,
        reference_path: Path,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]:
        with reference_path.open("rb") as reference:
            response = await self.client.images.edit(
                model=self.model,
                image=reference,
                prompt=prompt,
                size="1024x1536",
                quality=quality,
                n=count,
            )
        return self._decode_image_responses(response, expected_count=count)

    @staticmethod
    def _decode_image_response(response: object) -> bytes:
        return OpenAIImageProvider._decode_image_responses(response, expected_count=1)[0]

    @staticmethod
    def _decode_image_responses(response: object, *, expected_count: int) -> list[bytes]:
        data = getattr(response, "data", None)
        if not data or len(data) != expected_count:
            raise ImageGenerationUnavailable("The image did not finish. Try again.")
        decoded: list[bytes] = []
        for item in data:
            encoded = getattr(item, "b64_json", None)
            if not encoded:
                raise ImageGenerationUnavailable("The image did not finish. Try again.")
            try:
                decoded.append(base64.b64decode(encoded, validate=True))
            except ValueError as error:
                raise ImageGenerationUnavailable("The image did not finish. Try again.") from error
        return decoded

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
            "The editorial view could not be checked. The current version is unchanged."
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
        base_version_id: str | None = None,
    ) -> DesignVersionRecord:
        if self.provider is None:
            raise ImageGenerationUnavailable(
                "The studio is not connected yet. Start the image service and try again."
            )

        project = await self.store.ensure_project(project_id)
        base_version = (
            await self.store.get_design_version(project_id, base_version_id)
            if base_version_id is not None
            else project.current_version
        )
        if base_version_id is not None and (base_version is None or base_version.asset_id is None):
            raise RevisionBaseAssetRequired(
                "The selected design version has no raster to edit. Generate the first design "
                "without a base version."
            )
        requested_change = requested_change.strip()[:800]
        if not requested_change:
            raise ValueError("Describe one concrete design change.")
        keep = self._clean_list(preserve)
        exclude = self._clean_list(avoid)
        is_edit = bool(base_version and base_version.asset_id)
        if is_edit:
            prompt = self._build_edit_prompt(
                object_name=project.object_name,
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
            )
        else:
            prompt = self._build_initial_prompt(
                object_name=project.object_name,
                taste_traits=[tag for signal in project.taste_signals for tag in signal.tags],
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
            )

        job = await self.store.create_generation_job(
            project_id=project_id,
            base_version_id=base_version.id if is_edit and base_version else None,
            requested_change=requested_change,
            model=self.image_model,
        )
        await self.store.update_generation_job(job.id, status="running")

        try:
            if base_version and base_version.asset_id:
                reference_path = await self.resolve_asset(base_version.asset_id)
                # Every subsequent instruction is a real Images API edit of the selected
                # immutable raster. There is deliberately no text-only regeneration fallback.
                raw_image = await self.provider.edit(
                    prompt,
                    reference_path,
                    quality="medium",
                )
            else:
                # Only the first raster version is generated without an image reference.
                raw_image = await self.provider.generate(prompt, quality="medium")
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
            if base_version and base_version.status == "concept":
                # The assetless concept is provisional UI state, not garment truth. The first
                # successful generate-only transaction materializes it as ready version 01.
                version = await self.store.materialize_concept_version(
                    project_id=project_id,
                    version_id=base_version.id,
                    asset_id=asset.id,
                    generation_job_id=job.id,
                    requested_change=requested_change,
                    preserve=keep,
                    avoid=exclude,
                    prompt=prompt,
                )
            else:
                version = await self.store.add_design_version(
                    project_id=project_id,
                    parent_version_id=base_version.id if base_version else None,
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

        # The canonical version is durable before any angle rendering begins. Technical-view
        # failures are isolated records and can never roll back or replace garment truth.
        try:
            await self.create_technical_views_for_version(
                project_id=project_id,
                design_version_id=version.id,
            )
        except Exception:
            logger.exception(
                "Could not finish technical-view records for canonical version %s",
                version.id,
            )
        return version

    async def create_candidates(
        self,
        *,
        project_id: str,
        requested_change: str,
        preserve: list[str] | None = None,
        avoid: list[str] | None = None,
        base_version_id: str | None = None,
        count: int = 4,
    ) -> list[DesignCandidateRecord]:
        """Render one four-option set without creating or advancing design truth."""

        if self.provider is None:
            raise ImageGenerationUnavailable(
                "The studio is not connected yet. Start the image service and try again."
            )
        if count != 4:
            raise ValueError("Design candidate sets contain exactly four options.")

        project = await self.store.ensure_project(project_id)
        base_version = (
            await self.store.get_design_version(project_id, base_version_id)
            if base_version_id is not None
            else project.current_version
        )
        if base_version_id is not None and (base_version is None or base_version.asset_id is None):
            raise RevisionBaseAssetRequired(
                "The selected design version has no raster to edit. Generate the first design "
                "without a base version."
            )
        requested_change = requested_change.strip()[:800]
        if not requested_change:
            raise ValueError("Describe one concrete design change.")
        keep = self._clean_list(preserve)
        exclude = self._clean_list(avoid)
        is_edit = bool(base_version and base_version.asset_id)
        if is_edit:
            prompt = self._build_edit_prompt(
                object_name=project.object_name,
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
            )
        else:
            prompt = self._build_initial_prompt(
                object_name=project.object_name,
                taste_traits=[tag for signal in project.taste_signals for tag in signal.tags],
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
            )

        # Even the first generate-only set retains the exact provisional concept id. Selection
        # can therefore materialize only the concept the designer actually saw when rendering.
        source_version_id = base_version.id if base_version else None
        job = await self.store.create_candidate_generation_job(
            project_id=project_id,
            expected_project_updated_at=project.updated_at.isoformat(),
            base_version_id=source_version_id,
            expected_base_asset_id=base_version.asset_id if base_version else None,
            expected_base_status=base_version.status if base_version else None,
            requested_change=requested_change,
            model=self.image_model,
        )
        await self.store.update_generation_job(job.id, status="running")
        persisted_assets: list[AssetRecord] = []
        persisted_paths: list[str] = []

        try:
            if is_edit and base_version and base_version.asset_id:
                reference_path = await self.resolve_asset(base_version.asset_id)
                raw_candidates = await self.provider.edit_candidates(
                    prompt,
                    reference_path,
                    count=count,
                    quality="medium",
                )
            else:
                raw_candidates = await self.provider.generate_candidates(
                    prompt,
                    count=count,
                    quality="medium",
                )
            if not isinstance(raw_candidates, list) or len(raw_candidates) != count:
                raise ImageGenerationUnavailable(
                    "The full set of design options did not finish. Try again."
                )

            # Validate every provider result before any option becomes visible or durable.
            normalized_candidates = [
                await asyncio.to_thread(self._normalize_image, content)
                for content in raw_candidates
            ]
            for normalized, width, height in normalized_candidates:
                storage_path = await self._write_asset(project_id, normalized)
                persisted_paths.append(storage_path)
                asset = await self.store.add_asset(
                    project_id=project_id,
                    kind="generated",
                    storage_path=storage_path,
                    mime_type="image/png",
                    width=width,
                    height=height,
                    sha256=hashlib.sha256(normalized).hexdigest(),
                )
                persisted_assets.append(asset)

            return await self.store.create_design_candidates(
                project_id=project_id,
                generation_job_id=job.id,
                base_version_id=source_version_id,
                requested_change=requested_change,
                preserve=keep,
                avoid=exclude,
                prompt=prompt,
                model=self.image_model,
                asset_ids=[asset.id for asset in persisted_assets],
            )
        except Exception as error:
            await self._discard_candidate_assets(persisted_assets, persisted_paths)
            await self.store.update_generation_job(
                job.id,
                status="failed",
                error_code=self._error_code(error),
            )
            if isinstance(error, ImageGenerationUnavailable | InvalidImageError | ValueError):
                raise
            raise ImageGenerationUnavailable(
                "The design options could not be completed. Your current version is unchanged."
            ) from error

    async def select_candidate(
        self,
        *,
        project_id: str,
        generation_job_id: str,
        candidate_id: str,
    ) -> DesignVersionRecord:
        """Promote one candidate and create its three pending derived-view slots atomically."""

        project = await self.store.get_project(project_id)
        technical_views = [
            (
                role,
                build_technical_view_prompt(object_name=project.object_name, role=role),
                self.image_model,
            )
            for role in TECHNICAL_VIEW_ROLES
        ]
        version, _created = await self.store.select_design_candidate(
            project_id=project_id,
            generation_job_id=generation_job_id,
            candidate_id=candidate_id,
            technical_views=technical_views,
        )
        return version

    async def dismiss_candidate_set(
        self,
        *,
        project_id: str,
        generation_job_id: str,
    ) -> list[DesignCandidateRecord]:
        return await self.store.dismiss_design_candidates(
            project_id=project_id,
            generation_job_id=generation_job_id,
        )

    async def ensure_technical_view_records(
        self,
        *,
        project_id: str,
        design_version_id: str,
    ) -> list[TechnicalViewRecord]:
        project = await self.store.get_project(project_id)
        version = await self.store.get_design_version(project_id, design_version_id)
        if version.status != "ready" or version.asset_id is None:
            raise CanonicalDesignAssetRequired(
                "Generate a design version before making technical views."
            )
        records: list[TechnicalViewRecord] = []
        for role in TECHNICAL_VIEW_ROLES:
            records.append(
                await self.store.ensure_technical_view(
                    project_id=project_id,
                    design_version_id=version.id,
                    role=role,
                    prompt=build_technical_view_prompt(
                        object_name=project.object_name,
                        role=role,
                    ),
                    model=self.image_model,
                )
            )
        return records

    async def create_technical_views_for_version(
        self,
        *,
        project_id: str,
        design_version_id: str,
    ) -> list[TechnicalViewRecord]:
        """Render all three derived angles concurrently without mutating the version."""

        records = await self.ensure_technical_view_records(
            project_id=project_id,
            design_version_id=design_version_id,
        )
        await asyncio.gather(
            *(self._render_technical_view(record) for record in records),
            return_exceptions=True,
        )
        return await self.store.list_technical_views(
            project_id,
            design_version_id=design_version_id,
        )

    async def render_technical_view(
        self,
        *,
        project_id: str,
        design_version_id: str,
        role: TechnicalViewRole,
    ) -> TechnicalViewRecord:
        """Create or retry one angle; ready/running records are idempotent."""

        records = await self.ensure_technical_view_records(
            project_id=project_id,
            design_version_id=design_version_id,
        )
        record = next(item for item in records if item.role == role)
        return await self._render_technical_view(record)

    async def _render_technical_view(
        self,
        record: TechnicalViewRecord,
    ) -> TechnicalViewRecord:
        claimed, should_render = await self.store.claim_technical_view(record.id)
        if not should_render:
            return claimed
        if self.provider is None:
            return await self.store.update_technical_view(
                record.id,
                status="failed",
                error_code="provider_unavailable",
            )

        try:
            version = await self.store.get_design_version(
                record.project_id,
                record.design_version_id,
            )
            if version.status != "ready" or version.asset_id is None:
                raise CanonicalDesignAssetRequired(
                    "Generate a design version before making technical views."
                )
            canonical_path = await self.resolve_asset(version.asset_id)
            # Each angle is an independent Images API edit of the exact immutable canonical
            # raster. No angle is derived from another angle or from text alone.
            raw_image = await self.provider.edit(
                record.prompt,
                canonical_path,
                quality="medium",
            )
            normalized, width, height = await asyncio.to_thread(
                self._normalize_image,
                raw_image,
            )
            storage_path = await self._write_asset(record.project_id, normalized)
            asset = await self.store.add_asset(
                project_id=record.project_id,
                kind="generated",
                storage_path=storage_path,
                mime_type="image/png",
                width=width,
                height=height,
                sha256=hashlib.sha256(normalized).hexdigest(),
            )
            return await self.store.update_technical_view(
                record.id,
                status="ready",
                output_asset_id=asset.id,
            )
        except Exception as error:
            return await self.store.update_technical_view(
                record.id,
                status="failed",
                error_code=self._error_code(error),
            )

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
                "Editorial views are not available right now. The current version is unchanged."
            )
        if self.preservation_assessor is None:
            raise ImageGenerationUnavailable(
                "The editorial view could not be checked. The current version is unchanged."
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
            # Both canonical garment studies and presentation views use medium quality;
            # these rasters are inspected and iterated, not disposable thumbnails.
            raw_image = await self.provider.edit(prompt, reference_path, quality="medium")
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

    async def _discard_candidate_assets(
        self,
        assets: list[AssetRecord],
        storage_paths: list[str],
    ) -> None:
        """Best-effort cleanup for a set that failed before candidates became durable."""

        try:
            await self.store.delete_unlinked_assets([asset.id for asset in assets])
        except Exception:
            logger.exception("Could not remove unlinked candidate asset records")
            return
        root = self.asset_root.resolve()
        for storage_path in storage_paths:
            path = (root / storage_path).resolve()
            if path.is_relative_to(root):
                try:
                    await asyncio.to_thread(path.unlink, missing_ok=True)
                except OSError:
                    logger.exception("Could not remove unlinked candidate image %s", storage_path)

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
    def _build_initial_prompt(
        *,
        object_name: str,
        taste_traits: list[str],
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
    ) -> str:
        requested_change = requested_change.rstrip().rstrip(".")
        traits = ", ".join(dict.fromkeys(taste_traits)) or "considered proportion and construction"
        keep = ", ".join(preserve) or "the object category and clear front-view readability"
        exclusions = ", ".join(avoid) or "unrequested changes"
        return (
            "Create the first original design study from scratch.\n"
            f"Object: {object_name}.\n"
            f"Starting design brief: {requested_change}.\n"
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
    def _build_edit_prompt(
        *,
        object_name: str,
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
    ) -> str:
        requested_change = requested_change.rstrip().rstrip(".")
        keep = ", ".join(preserve) or (
            "object category, silhouette, cut, proportions, materials, construction, color, "
            "graphics, finish, trims, closures, and placement"
        )
        exclusions = ", ".join(avoid) or "any other design change"
        return (
            "Edit the supplied current design image. Use it as the sole visual source of truth.\n"
            f"Object: {object_name}.\n"
            f"Make exactly this one requested visible change: {requested_change}.\n"
            f"Keep unchanged: {keep}.\n"
            f"Avoid: {exclusions}.\n"
            "Everything outside the requested detail must remain visually unchanged, including "
            "the garment identity, camera, framing, background, and lighting. Do not reinterpret "
            "taste traits, redesign the object, add styling, or introduce a second change. Return "
            "one centered edited fashion product with the full object visible. No person, no logo, "
            "no brand mark, no signature graphic, no readable text, no watermark, no collage."
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

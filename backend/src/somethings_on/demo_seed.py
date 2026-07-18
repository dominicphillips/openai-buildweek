from __future__ import annotations

import asyncio
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .design_store import ProjectNotFoundError, SQLiteDesignStore
from .image_service import TECHNICAL_VIEW_ROLES, build_technical_view_prompt
from .models import (
    AssetRecord,
    CastingControls,
    DesignVersionRecord,
    PresentationRenderRecord,
    ProjectSeedInput,
    ProjectSnapshot,
    TasteSignal,
)

DEVDAY_PROJECT_ID = "devday-swag"
DEVDAY_OBJECT_NAME = "DevDay distressed bomber + white T-shirt"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DEVDAY_SOURCE_ROOT = REPOSITORY_ROOT / "app" / "public" / "devday"


class DevDayDemoSeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedDesignVersion:
    filename: str
    sha256: str
    requested_change: str
    preserve: tuple[str, ...]
    avoid: tuple[str, ...]
    prompt: str

    @property
    def source_url(self) -> str:
        return f"app/public/devday/{self.filename}"


@dataclass(frozen=True)
class PreparedPresentation:
    filename: str
    sha256: str
    preset_id: str
    controls: CastingControls
    avoid: tuple[str, ...]
    prompt: str

    @property
    def source_url(self) -> str:
        return f"app/public/devday/{self.filename}"


_COMMON_AVOID = (
    "logos, brand marks, readable text, or watermark",
    "recognizable campaign, celebrity, or identifiable real person",
    "cartoon, drawing, vector, CGI, or collage",
)

PREPARED_DESIGN_VERSIONS = (
    PreparedDesignVersion(
        filename="devday-look-v1.png",
        sha256="8e6f5d8930a1459e80d76498829b765b4053fbde6a87ad8e2e66ac666af87282",
        requested_change=(
            "Create the canonical washed-charcoal flight bomber layered over a blank white T-shirt"
        ),
        preserve=("full garment visibility", "inspection-friendly product view"),
        avoid=_COMMON_AVOID,
        prompt=(
            "Photorealistic high-end fashion design-review product photograph, not illustration "
            "and not CGI. One original distressed washed-charcoal bomber jacket layered open "
            "over one heavyweight blank optic-white T-shirt on a headless ghost mannequin, "
            "complete garments fully visible from collar through hem, front three-quarter view, "
            "no person or skin. Roomy flight proportion, dropped shoulder, matte cotton-nylon "
            "shell, worn rib collar cuffs and hem, two-way metal zip, side-entry welt pockets, "
            "subtle abrasion and repaired wear, tiny restrained safety-orange bartack accents. "
            "The T-shirt has substantial cotton jersey, clean crew neck, blank surface and "
            "visible hem. Neutral near-black charcoal studio sweep, soft controlled overhead "
            "light plus narrow warm edge light, technically legible fabric grain, seams, ribbing "
            "and hardware. Original unbranded design, inspection-friendly negative space. No "
            "logos, brand marks, readable text, watermark, accessories, lower-body styling, "
            "recognizable campaign, cartoon, drawing, vector, collage, distorted garment, "
            "cropped garment, hidden closures."
        ),
    ),
    PreparedDesignVersion(
        filename="devday-look-v2.png",
        sha256="097d6be9c2412493004fc430c18535fe0f12a42561f89669ba8951187788f29a",
        requested_change=(
            "Externalize selected seam allowances and add restrained safety-orange bartacks"
        ),
        preserve=(
            "roomy flight silhouette and length",
            "washed-charcoal shell and rib",
            "blank optic-white T-shirt",
            "camera, crop, background, and lighting",
        ),
        avoid=_COMMON_AVOID,
        prompt=(
            "Edit the supplied current garment image as the sole visual source of truth. Make "
            "exactly one visible design change: convert the bomber's construction expression to "
            "a restrained inside-out treatment, with selected seam allowances and raw "
            "construction lines visibly externalized and a small number of precise safety-orange "
            "bartacks at high-stress joins. KEEP unchanged: the exact bomber category, roomy "
            "flight silhouette, length, dropped shoulder, washed-charcoal color, distressed "
            "matte shell, rib collar cuffs and hem, two-way zip, pocket placement, blank "
            "optic-white heavyweight T-shirt, ghost-mannequin presentation, camera, crop, "
            "charcoal background, lighting, and all proportions. Do not redesign or replace the "
            "garment. No person, skin, logos, text, watermark, extra styling, cartoon, drawing, "
            "CGI or collage."
        ),
    ),
    PreparedDesignVersion(
        filename="devday-look-v3.png",
        sha256="c29dfb9a2e800224057224158d533a96ec413ecf678c47f307181cd152f9cf6b",
        requested_change=(
            "Shorten only the bomber body by approximately 90 millimeters to a high-hip crop"
        ),
        preserve=(
            "roomy flight width and sleeve length",
            "external seam construction and orange bartacks",
            "washed-charcoal shell and blank white T-shirt",
            "camera, crop, background, and lighting",
        ),
        avoid=_COMMON_AVOID,
        prompt=(
            "Edit the supplied current garment image as the sole visual source of truth. Make "
            "exactly one visible design change: shorten only the bomber body length by "
            "approximately 90 millimeters so the rib hem finishes at the high hip; preserve "
            "sleeve length and keep the white T-shirt extending visibly below the jacket. KEEP "
            "unchanged: the exact bomber identity, roomy flight width, dropped shoulder, "
            "washed-charcoal color, distressed matte shell, externalized seam construction, "
            "safety-orange bartacks, rib collar cuffs and hem, two-way zip, pocket design and "
            "placement, blank optic-white heavyweight T-shirt, ghost-mannequin presentation, "
            "camera, crop, charcoal background, lighting, and every other proportion. Do not "
            "redesign or replace the garment. No person, skin, logos, text, watermark, extra "
            "styling, cartoon, drawing, CGI or collage."
        ),
    ),
)

PREPARED_PRESENTATION = PreparedPresentation(
    filename="devday-presentation-v3.png",
    sha256="a2da00bc1f3b551dc901e0a4273318edf7044f891967eb8d79e09a386ec2f4f6",
    preset_id="edgy-european-guy",
    controls=CastingControls(
        body_build="lean",
        stature="tall",
        skin_tone="light-medium",
        presentation="masculine",
        adult_age="25-39",
        pose_access="standing",
        continuity="new-fictional-casting",
    ),
    avoid=(
        "logos, brand marks, readable text, or watermark",
        "celebrity, recognizable real person, or borrowed campaign",
        "cartoon, drawing, CGI, collage, or excessive styling",
        "altered, hidden, or replaced canonical garments",
    ),
    prompt=(
        "Use the supplied garment image as the exact canonical wardrobe reference. Create a "
        "separate photorealistic editorial lookbook presentation with one entirely fictional, "
        "non-identifiable adult model, male-presenting, apparent age 28 to 34, tall lean build, "
        "short dark hair, understated contemporary European casting, calm neutral expression. "
        "Show the model full-body in a restrained raw-concrete Los Angeles studio, relaxed "
        "contrapposto, wearing the exact washed-charcoal cropped distressed bomber open over the "
        "exact blank heavyweight white T-shirt from the reference, with straight black trousers "
        "and unbranded black leather shoes. Preserve the jacket's high-hip body length, roomy "
        "width, dropped shoulder, external seam allowances, orange bartacks, rib, zips, pockets, "
        "abrasion, color, and the T-shirt neckline and hem. Soft overcast daylight with a warm "
        "edge, real camera, realistic skin and textiles, high-end independent fashion casting "
        "sheet, no borrowed campaign. Do not alter or hide the garment; no logos, brand marks, "
        "readable text, watermark, celebrity, recognizable real person, cartoon, drawing, CGI, "
        "collage, excessive styling, jewelry, hat, bag, or dramatic pose."
    ),
)

DEVDAY_PROJECT_SEED = ProjectSeedInput(
    object_name=DEVDAY_OBJECT_NAME,
    taste_signals=[
        TasteSignal(
            id="john-elliott",
            name="JOHN ELLIOTT",
            tags=["refined essentials", "fabric focus", "layered neutrals"],
        )
    ],
)


class DevDayDemoSeeder:
    """Import documented, real prepared API outputs into one reserved local demo project."""

    def __init__(
        self,
        *,
        store: SQLiteDesignStore,
        asset_root: Path,
        source_root: Path = DEFAULT_DEVDAY_SOURCE_ROOT,
    ) -> None:
        self.store = store
        self.asset_root = asset_root.resolve()
        self.source_root = source_root.resolve()
        self._lock = asyncio.Lock()

    async def ensure_seeded(self) -> ProjectSnapshot:
        async with self._lock:
            return await self._ensure_seeded_unlocked()

    async def _ensure_seeded_unlocked(self) -> ProjectSnapshot:
        try:
            project = await self.store.get_project(DEVDAY_PROJECT_ID)
        except ProjectNotFoundError:
            project = await self.store.upsert_project(
                DEVDAY_PROJECT_ID,
                DEVDAY_PROJECT_SEED,
            )

        progress = await self._design_seed_progress(project)
        if progress is None:
            return project

        if progress < len(PREPARED_DESIGN_VERSIONS):
            if project.presentations:
                return project
            versions = list(project.versions)
            for index in range(progress, len(PREPARED_DESIGN_VERSIONS)):
                prepared = PREPARED_DESIGN_VERSIONS[index]
                asset = await self._import_asset(prepared)
                parent = versions[-1] if versions else None
                job = await self.store.create_generation_job(
                    project_id=DEVDAY_PROJECT_ID,
                    base_version_id=parent.id if index > 0 and parent else None,
                    requested_change=prepared.requested_change,
                    model="gpt-image-2",
                )
                await self.store.update_generation_job(job.id, status="running")
                if index == 0 and parent and parent.status == "concept":
                    version = await self.store.materialize_concept_version(
                        project_id=DEVDAY_PROJECT_ID,
                        version_id=parent.id,
                        asset_id=asset.id,
                        generation_job_id=job.id,
                        requested_change=prepared.requested_change,
                        preserve=list(prepared.preserve),
                        avoid=list(prepared.avoid),
                        prompt=prepared.prompt,
                    )
                    versions[-1] = version
                else:
                    version = await self.store.add_design_version(
                        project_id=DEVDAY_PROJECT_ID,
                        parent_version_id=parent.id if parent else None,
                        asset_id=asset.id,
                        generation_job_id=job.id,
                        requested_change=prepared.requested_change,
                        preserve=list(prepared.preserve),
                        avoid=list(prepared.avoid),
                        prompt=prepared.prompt,
                    )
                    versions.append(version)
                await self.store.update_generation_job(
                    job.id,
                    status="succeeded",
                    output_asset_id=asset.id,
                )
            project = await self.store.get_project(DEVDAY_PROJECT_ID)

        project = await self._ensure_presentation(project)
        return await self._ensure_technical_view_records(project)

    async def _ensure_technical_view_records(
        self,
        project: ProjectSnapshot,
    ) -> ProjectSnapshot:
        """Expose honest retryable slots for prepared rasters without paid startup calls."""

        for version in project.versions:
            if version.status != "ready" or version.asset_id is None:
                continue
            for role in TECHNICAL_VIEW_ROLES:
                await self.store.ensure_technical_view(
                    project_id=project.id,
                    design_version_id=version.id,
                    role=role,
                    prompt=build_technical_view_prompt(
                        object_name=project.object_name,
                        role=role,
                    ),
                    model="gpt-image-2",
                )
        return await self.store.get_project(project.id)

    async def _design_seed_progress(self, project: ProjectSnapshot) -> int | None:
        if (
            project.object_name != DEVDAY_PROJECT_SEED.object_name
            or project.taste_signals != DEVDAY_PROJECT_SEED.taste_signals
        ):
            return None

        versions = project.versions
        if (
            len(versions) == 1
            and project.object_name == DEVDAY_OBJECT_NAME
            and versions[0].version_number == 1
            and versions[0].status == "concept"
            and versions[0].parent_version_id is None
            and versions[0].asset_id is None
            and versions[0].generation_job_id is None
        ):
            return 0

        expected_parent_id: str | None = None
        matched = 0
        for index, prepared in enumerate(PREPARED_DESIGN_VERSIONS):
            if index >= len(versions):
                break
            version = versions[index]
            if not await self._matches_design_version(
                version,
                prepared,
                version_number=index + 1,
                parent_version_id=expected_parent_id,
            ):
                return None
            expected_parent_id = version.id
            matched += 1

        if matched == len(PREPARED_DESIGN_VERSIONS):
            return matched
        if matched == len(versions):
            return matched
        return None

    async def _matches_design_version(
        self,
        version: DesignVersionRecord,
        prepared: PreparedDesignVersion,
        *,
        version_number: int,
        parent_version_id: str | None,
    ) -> bool:
        if (
            version.version_number != version_number
            or version.parent_version_id != parent_version_id
            or version.status != "ready"
            or version.asset_id is None
            or version.generation_job_id is None
            or version.requested_change != prepared.requested_change
            or version.preserve != list(prepared.preserve)
            or version.avoid != list(prepared.avoid)
            or version.prompt != prepared.prompt
        ):
            return False
        record, storage_path = await self.store.get_asset_location(version.asset_id)
        return await self._matches_asset(record, storage_path, prepared)

    async def _ensure_presentation(self, project: ProjectSnapshot) -> ProjectSnapshot:
        canonical_versions = project.versions[: len(PREPARED_DESIGN_VERSIONS)]
        if len(canonical_versions) != len(PREPARED_DESIGN_VERSIONS):
            return project
        version_three = canonical_versions[-1]

        for presentation in project.presentations:
            if await self._matches_presentation(presentation, version_three):
                return project

        if len(project.versions) != len(PREPARED_DESIGN_VERSIONS):
            return project

        partials = [
            presentation
            for presentation in project.presentations
            if self._is_partial_seed_presentation(presentation, version_three)
        ]
        if project.presentations and (len(project.presentations) != 1 or len(partials) != 1):
            return project
        partial = partials[0] if partials else None

        asset = await self._import_asset(PREPARED_PRESENTATION)
        if partial is None:
            partial = await self.store.create_presentation_render(
                project_id=DEVDAY_PROJECT_ID,
                design_version_id=version_three.id,
                preset_id=PREPARED_PRESENTATION.preset_id,
                controls=PREPARED_PRESENTATION.controls,
                prompt=PREPARED_PRESENTATION.prompt,
                avoid=list(PREPARED_PRESENTATION.avoid),
                model="gpt-image-2",
            )
        await self.store.update_presentation_render(partial.id, status="running")
        await self.store.update_presentation_render(
            partial.id,
            status="ready",
            output_asset_id=asset.id,
        )
        return await self.store.get_project(DEVDAY_PROJECT_ID)

    async def _matches_presentation(
        self,
        presentation: PresentationRenderRecord,
        version_three: DesignVersionRecord,
    ) -> bool:
        if (
            presentation.design_version_id != version_three.id
            or presentation.preset_id != PREPARED_PRESENTATION.preset_id
            or presentation.controls != PREPARED_PRESENTATION.controls
            or presentation.prompt != PREPARED_PRESENTATION.prompt
            or presentation.avoid != list(PREPARED_PRESENTATION.avoid)
            or presentation.model != "gpt-image-2"
            or presentation.status != "ready"
            or presentation.output_asset_id is None
        ):
            return False
        record, storage_path = await self.store.get_asset_location(presentation.output_asset_id)
        return await self._matches_asset(
            record,
            storage_path,
            PREPARED_PRESENTATION,
        )

    @staticmethod
    def _is_partial_seed_presentation(
        presentation: PresentationRenderRecord,
        version_three: DesignVersionRecord,
    ) -> bool:
        return (
            presentation.design_version_id == version_three.id
            and presentation.preset_id == PREPARED_PRESENTATION.preset_id
            and presentation.controls == PREPARED_PRESENTATION.controls
            and presentation.prompt == PREPARED_PRESENTATION.prompt
            and presentation.avoid == list(PREPARED_PRESENTATION.avoid)
            and presentation.model == "gpt-image-2"
            and presentation.status in {"queued", "running", "failed"}
            and presentation.output_asset_id is None
        )

    async def _import_asset(
        self,
        prepared: PreparedDesignVersion | PreparedPresentation,
    ) -> AssetRecord:
        existing = await self.store.find_asset_by_provenance(
            project_id=DEVDAY_PROJECT_ID,
            source_url=prepared.source_url,
            sha256=prepared.sha256,
        )
        if existing is not None:
            record, existing_path = existing
            await asyncio.to_thread(
                self._ensure_runtime_copy,
                prepared,
                Path(existing_path),
            )
            return record
        storage_path = Path("prepared-devday") / prepared.filename
        await asyncio.to_thread(self._ensure_runtime_copy, prepared, storage_path)
        return await self.store.add_asset(
            project_id=DEVDAY_PROJECT_ID,
            kind="generated",
            storage_path=storage_path.as_posix(),
            mime_type="image/png",
            width=1024,
            height=1536,
            sha256=prepared.sha256,
            original_name=prepared.filename,
            source_url=prepared.source_url,
        )

    async def _matches_asset(
        self,
        record: AssetRecord,
        storage_path: str,
        prepared: PreparedDesignVersion | PreparedPresentation,
    ) -> bool:
        if (
            record.project_id != DEVDAY_PROJECT_ID
            or record.kind != "generated"
            or record.mime_type != "image/png"
            or record.width != 1024
            or record.height != 1536
            or record.sha256 != prepared.sha256
            or record.source_url != prepared.source_url
            or record.original_name != prepared.filename
        ):
            return False
        await asyncio.to_thread(self._ensure_runtime_copy, prepared, Path(storage_path))
        return True

    def _ensure_runtime_copy(
        self,
        prepared: PreparedDesignVersion | PreparedPresentation,
        storage_path: Path,
    ) -> None:
        source = (self.source_root / prepared.filename).resolve()
        if not source.is_relative_to(self.source_root) or not source.is_file():
            raise DevDayDemoSeedError(f"Prepared DevDay source is missing: {prepared.filename}")
        self._validate_png(source, prepared.sha256)

        destination = (self.asset_root / storage_path).resolve()
        if not destination.is_relative_to(self.asset_root):
            raise DevDayDemoSeedError("Prepared DevDay destination escaped the asset root.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            self._validate_png(destination, prepared.sha256)
            return
        shutil.copyfile(source, destination)
        self._validate_png(destination, prepared.sha256)

    @staticmethod
    def _validate_png(path: Path, expected_sha256: str) -> None:
        try:
            with path.open("rb") as source:
                actual_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
            if actual_sha256 != expected_sha256:
                raise DevDayDemoSeedError(f"Prepared DevDay checksum mismatch: {path.name}")
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.format != "PNG" or image.size != (1024, 1536):
                    raise DevDayDemoSeedError(
                        f"Prepared DevDay image has unexpected dimensions: {path.name}"
                    )
        except (OSError, UnidentifiedImageError) as error:
            raise DevDayDemoSeedError(
                f"Prepared DevDay image is not a readable PNG: {path.name}"
            ) from error

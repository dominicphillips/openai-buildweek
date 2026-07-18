from __future__ import annotations

import io
from functools import partial
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from somethings_on.casting import CastingPresetCatalog
from somethings_on.config import Settings
from somethings_on.design_store import SQLiteDesignStore
from somethings_on.image_service import (
    CanonicalDesignAssetRequired,
    DesignImageService,
    GarmentPreservationAssessment,
    ImageGenerationUnavailable,
    ImageQuality,
)
from somethings_on.main import create_app
from somethings_on.models import (
    CastingControls,
    PresentationCreateInput,
    ProjectSeedInput,
)

CASTING_SEED = Path(__file__).parents[1] / "seeds" / "casting_presets.json"


def image_bytes(color: str = "white") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (96, 128), color).save(output, format="PNG")
    return output.getvalue()


class RecordingImageProvider:
    model = "fake-image"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Path | None, ImageQuality]] = []

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.calls.append((prompt, None, quality))
        return image_bytes("black")

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.calls.append((prompt, reference_path, quality))
        return image_bytes("black")


class RecordingPreservationAssessor:
    def __init__(self, *, preserves_garment: bool = True) -> None:
        self.preserves_garment = preserves_garment
        self.calls: list[tuple[Path, bytes]] = []

    async def assess_preservation(
        self,
        *,
        canonical_path: Path,
        presentation_content: bytes,
    ) -> GarmentPreservationAssessment:
        self.calls.append((canonical_path, presentation_content))
        return GarmentPreservationAssessment(
            preserves_garment=self.preserves_garment,
            changed_or_hidden_details=([] if self.preserves_garment else ["front closure"]),
            summary=(
                "The garment is preserved."
                if self.preserves_garment
                else "The front closure changed."
            ),
        )


@pytest.mark.asyncio
async def test_presentation_uses_canonical_asset_without_adding_design_version(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project("look_001", ProjectSeedInput(object_name="white T-shirt"))
    provider = RecordingImageProvider()
    assessor = RecordingPreservationAssessor()
    catalog = CastingPresetCatalog.load(CASTING_SEED)
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
        casting_catalog=catalog,
        preservation_assessor=assessor,
    )
    await service.initialize()

    with pytest.raises(CanonicalDesignAssetRequired):
        await service.create_presentation(
            project_id="look_001",
            request=PresentationCreateInput(preset_id="edgy-european-guy"),
        )
    assert provider.calls == []

    canonical = await service.create_revision(
        project_id="look_001",
        requested_change="Make the shoulder one centimeter wider",
    )
    before = await store.get_project("look_001")
    request = PresentationCreateInput(
        preset_id="edgy-european-guy",
        controls=CastingControls(
            body_build="broad",
            stature="short",
            skin_tone="deep",
            presentation="androgynous",
            adult_age="40-59",
            pose_access="seated",
        ),
    )
    presentation = await service.create_presentation(
        project_id="look_001",
        request=request,
    )
    after = await store.get_project("look_001")

    assert presentation.status == "ready"
    assert presentation.design_version_id == canonical.id
    assert presentation.output_asset_id is not None
    assert len(after.versions) == len(before.versions)
    assert after.current_version == before.current_version
    assert [record.id for record in after.presentations] == [presentation.id]
    assert provider.calls[-1][1] is not None
    assert provider.calls[-1][1].is_file()
    assert [call[2] for call in provider.calls] == ["medium"] * 5
    assert len(assessor.calls) == 1
    assert assessor.calls[0][0] == provider.calls[-1][1]
    assert assessor.calls[0][1]
    prompt = provider.calls[-1][0]
    preset = catalog.get("edgy-european-guy")
    assert preset.prompt_fragment in prompt
    assert preset.display_name not in prompt
    assert preset.one_line_mood not in prompt
    assert "Body build: broad." in prompt
    assert "Adult age: 40-59." in prompt
    assert "visibly age 25 or older" in prompt
    assert "Preserve the supplied garment" in prompt
    assert "recognizable campaigns" in prompt


@pytest.mark.asyncio
async def test_garment_drift_fails_presentation_without_saving_asset_or_version(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project("look_001", ProjectSeedInput(object_name="distressed bomber"))
    provider = RecordingImageProvider()
    assessor = RecordingPreservationAssessor(preserves_garment=False)
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
        casting_catalog=CastingPresetCatalog.load(CASTING_SEED),
        preservation_assessor=assessor,
    )
    await service.initialize()
    canonical = await service.create_revision(
        project_id="look_001",
        requested_change="Distress the shell while keeping the front closure",
    )
    before = await store.get_project("look_001")
    asset_files_before = sorted((tmp_path / "assets").rglob("*.png"))

    presentation = await service.create_presentation(
        project_id="look_001",
        request=PresentationCreateInput(preset_id="concrete-romantic"),
    )
    after = await store.get_project("look_001")
    asset_files_after = sorted((tmp_path / "assets").rglob("*.png"))

    assert presentation.status == "failed"
    assert presentation.error_code == "garment_drift"
    assert presentation.output_asset_id is None
    assert presentation.design_version_id == canonical.id
    assert after.versions == before.versions
    assert after.current_version == before.current_version
    assert after.presentations == [presentation]
    assert asset_files_after == asset_files_before
    assert len(assessor.calls) == 1
    assert [call[2] for call in provider.calls] == ["medium"] * 5


@pytest.mark.asyncio
async def test_provider_unavailable_keeps_design_and_presentation_history_clean(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project("look_001", ProjectSeedInput())
    catalog = CastingPresetCatalog.load(CASTING_SEED)
    setup_service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=RecordingImageProvider(),
        image_model="gpt-image-2",
        casting_catalog=catalog,
    )
    await setup_service.initialize()
    await setup_service.create_revision(
        project_id="look_001",
        requested_change="Add a slightly heavier collar rib",
    )
    offline_service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=None,
        image_model="gpt-image-2",
        casting_catalog=catalog,
    )

    with pytest.raises(ImageGenerationUnavailable, match="not available right now"):
        await offline_service.create_presentation(
            project_id="look_001",
            request=PresentationCreateInput(preset_id="nerdy-tech-girl"),
        )
    assert (await store.get_project("look_001")).presentations == []


def test_casting_controls_reject_unknown_values_and_fields() -> None:
    with pytest.raises(ValidationError):
        CastingControls(body_build="editorial")
    with pytest.raises(ValidationError):
        PresentationCreateInput.model_validate(
            {
                "preset_id": "edgy-european-guy",
                "controls": {"nationality": "European"},
            }
        )


def test_casting_endpoints_validate_and_keep_versions_immutable(tmp_path: Path) -> None:
    provider = RecordingImageProvider()
    assessor = RecordingPreservationAssessor()
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
        SOMETHINGS_ON_CASTING_PRESETS_PATH=CASTING_SEED,
    )
    app = create_app(
        settings,
        image_provider=provider,
        preservation_assessor=assessor,
    )

    with TestClient(app) as client:
        presets = client.get("/api/casting-presets")
        assert presets.status_code == 200
        assert len(presets.json()["presets"]) == 8

        client.put("/api/projects/look_001", json={"object_name": "white T-shirt"})
        missing_asset = client.post(
            "/api/projects/look_001/presentations",
            json={"preset_id": "nerdy-tech-girl"},
        )
        assert missing_asset.status_code == 409
        assert "Generate a design version" in missing_asset.json()["detail"]
        assert provider.calls == []

        assert client.portal is not None
        client.portal.call(
            partial(
                app.state.image_service.create_revision,
                project_id="look_001",
                requested_change="Shorten the sleeve by one centimeter",
            )
        )
        project_before = client.get("/api/projects/look_001").json()
        created = client.post(
            "/api/projects/look_001/presentations",
            json={
                "preset_id": "nerdy-tech-girl",
                "controls": {
                    "skin_tone": "medium-deep",
                    "adult_age": "60-plus",
                    "presentation": "mixed-cues",
                },
            },
        )
        assert created.status_code == 201
        assert created.json()["status"] == "ready"
        assert provider.calls[-1][1] is not None
        assert provider.calls[-1][2] == "medium"
        assert len(assessor.calls) == 1

        project_after = client.get("/api/projects/look_001").json()
        listed = client.get("/api/projects/look_001/presentations")
        assert len(project_after["versions"]) == len(project_before["versions"])
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [created.json()["id"]]

        invalid = client.post(
            "/api/projects/look_001/presentations",
            json={
                "preset_id": "nerdy-tech-girl",
                "controls": {"adult_age": "18-24"},
            },
        )
        assert invalid.status_code == 422
        unknown = client.post(
            "/api/projects/look_001/presentations",
            json={"preset_id": "not-a-preset"},
        )
        assert unknown.status_code == 404


def test_casting_endpoint_returns_failed_record_for_garment_drift(tmp_path: Path) -> None:
    provider = RecordingImageProvider()
    assessor = RecordingPreservationAssessor(preserves_garment=False)
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "test.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
        SOMETHINGS_ON_CASTING_PRESETS_PATH=CASTING_SEED,
    )
    app = create_app(
        settings,
        image_provider=provider,
        preservation_assessor=assessor,
    )

    with TestClient(app) as client:
        client.put("/api/projects/look_001", json={"object_name": "distressed bomber"})
        assert client.portal is not None
        client.portal.call(
            partial(
                app.state.image_service.create_revision,
                project_id="look_001",
                requested_change="Distress the shell and preserve every closure",
            )
        )
        before = client.get("/api/projects/look_001").json()

        created = client.post(
            "/api/projects/look_001/presentations",
            json={"preset_id": "after-hours-art-handler"},
        )
        after = client.get("/api/projects/look_001").json()

        assert created.status_code == 201
        assert created.json()["status"] == "failed"
        assert created.json()["error_code"] == "garment_drift"
        assert created.json()["output_asset_id"] is None
        assert created.json()["asset_url"] is None
        assert after["versions"] == before["versions"]
        assert after["current_version"] == before["current_version"]
        assert after["presentations"] == [created.json()]


def test_casting_endpoint_reports_provider_unavailable(tmp_path: Path) -> None:
    database_path = tmp_path / "test.sqlite3"
    asset_path = tmp_path / "assets"
    online_settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=database_path,
        SOMETHINGS_ON_ASSET_PATH=asset_path,
        SOMETHINGS_ON_CASTING_PRESETS_PATH=CASTING_SEED,
    )
    with TestClient(create_app(online_settings, image_provider=RecordingImageProvider())) as client:
        client.put("/api/projects/look_001", json={"object_name": "white T-shirt"})
        assert client.portal is not None
        client.portal.call(
            partial(
                client.app.state.image_service.create_revision,
                project_id="look_001",
                requested_change="Widen the hem by one centimeter",
            )
        )

    offline_settings = Settings(
        OPENAI_API_KEY="",
        SOMETHINGS_ON_DATABASE_PATH=database_path,
        SOMETHINGS_ON_ASSET_PATH=asset_path,
        SOMETHINGS_ON_CASTING_PRESETS_PATH=CASTING_SEED,
    )
    with TestClient(create_app(offline_settings)) as client:
        unavailable = client.post(
            "/api/projects/look_001/presentations",
            json={"preset_id": "sun-faded-minimalist"},
        )
        assert unavailable.status_code == 503
        assert unavailable.json()["detail"] == (
            "Editorial views are not available right now. The current version is unchanged."
        )

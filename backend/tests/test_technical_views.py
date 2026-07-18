from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from somethings_on.config import Settings
from somethings_on.design_store import SQLiteDesignStore
from somethings_on.image_service import DesignImageService, ImageQuality
from somethings_on.main import create_app
from somethings_on.models import ProjectSeedInput


def image_bytes(color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (96, 128), color).save(output, format="PNG")
    return output.getvalue()


class TechnicalViewProvider:
    model = "fake-image"

    def __init__(self, *, fail_roles: set[str] | None = None) -> None:
        self.fail_roles = fail_roles or set()
        self.generate_calls: list[tuple[str, ImageQuality]] = []
        self.edit_calls: list[tuple[str, Path, bytes, ImageQuality]] = []
        self.active_technical_calls = 0
        self.max_concurrent_technical_calls = 0

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.generate_calls.append((prompt, quality))
        return image_bytes("white")

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.edit_calls.append((prompt, reference_path, reference_path.read_bytes(), quality))
        if "derived technical inspection view" not in prompt:
            return image_bytes("gray")

        role = self._role_from_prompt(prompt)
        self.active_technical_calls += 1
        self.max_concurrent_technical_calls = max(
            self.max_concurrent_technical_calls,
            self.active_technical_calls,
        )
        try:
            await asyncio.sleep(0.01)
            if role in self.fail_roles:
                raise RuntimeError(f"{role} view unavailable")
            return image_bytes({"back": "black", "left": "red", "right": "blue"}[role])
        finally:
            self.active_technical_calls -= 1

    @staticmethod
    def _role_from_prompt(prompt: str) -> str:
        if "direct back view" in prompt:
            return "back"
        if "left-side profile" in prompt:
            return "left"
        if "right-side profile" in prompt:
            return "right"
        raise AssertionError("Technical prompt did not identify one supported view role")


@pytest.mark.asyncio
async def test_revision_creates_three_concurrent_views_from_exact_canonical_asset(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project(
        "look_001",
        ProjectSeedInput(object_name="Bomber jacket"),
    )
    provider = TechnicalViewProvider()
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()

    version = await service.create_revision(
        project_id="look_001",
        requested_change="Create the first washed charcoal bomber",
    )

    assert version.asset_id is not None
    canonical_path = await service.resolve_asset(version.asset_id)
    canonical_bytes = canonical_path.read_bytes()
    technical_calls = [
        call for call in provider.edit_calls if "derived technical inspection view" in call[0]
    ]
    assert len(technical_calls) == 3
    assert provider.max_concurrent_technical_calls == 3
    assert {provider._role_from_prompt(call[0]) for call in technical_calls} == {
        "back",
        "left",
        "right",
    }
    for prompt, reference_path, submitted_reference, quality in technical_calls:
        assert reference_path == canonical_path
        assert submitted_reference == canonical_bytes
        assert quality == "medium"
        assert "Change only the viewpoint" in prompt
        assert "Preserve the exact garment identity" in prompt
        assert "materials, construction, seam placement" in prompt
        assert "color, graphics, distressing, finish" in prompt
        assert "full object visible" in prompt
        assert "neutral studio background" in prompt
        assert "No person" in prompt

    snapshot = await store.get_project("look_001")
    assert snapshot.versions == [version]
    assert snapshot.current_version == version
    assert {view.role for view in snapshot.technical_views} == {"back", "left", "right"}
    assert {view.design_version_id for view in snapshot.technical_views} == {version.id}
    assert {view.status for view in snapshot.technical_views} == {"ready"}
    assert all(view.output_asset_id and view.asset_url for view in snapshot.technical_views)

    serialized = snapshot.model_dump(mode="json")
    assert len(serialized["technical_views"]) == 3
    assert all(
        item["asset_url"].startswith("/api/assets/") for item in serialized["technical_views"]
    )


@pytest.mark.asyncio
async def test_partial_view_failure_preserves_canonical_and_retries_only_failed_role(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project("look_001", ProjectSeedInput(object_name="T-shirt"))
    provider = TechnicalViewProvider(fail_roles={"left"})
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()

    version = await service.create_revision(
        project_id="look_001",
        requested_change="Create a heavyweight white jersey study",
    )
    assert version.asset_id is not None
    canonical_path = await service.resolve_asset(version.asset_id)
    canonical_before_retry = canonical_path.read_bytes()
    before = await store.get_project("look_001")
    views_before = {view.role: view for view in before.technical_views}

    assert version.status == "ready"
    assert before.current_version == version
    assert views_before["back"].status == "ready"
    assert views_before["right"].status == "ready"
    assert views_before["left"].status == "failed"
    assert views_before["left"].output_asset_id is None
    assert views_before["left"].error_code == "RuntimeError"

    calls_before_retry = len(provider.edit_calls)
    provider.fail_roles.clear()
    retried = await service.render_technical_view(
        project_id="look_001",
        design_version_id=version.id,
        role="left",
    )
    after = await store.get_project("look_001")

    assert retried.id == views_before["left"].id
    assert retried.status == "ready"
    assert retried.output_asset_id is not None
    assert len(provider.edit_calls) == calls_before_retry + 1
    retry_call = provider.edit_calls[-1]
    assert provider._role_from_prompt(retry_call[0]) == "left"
    assert retry_call[1] == canonical_path
    assert retry_call[2] == canonical_before_retry
    assert canonical_path.read_bytes() == canonical_before_retry
    assert after.versions == [version]
    assert after.current_version == version
    assert {view.status for view in after.technical_views} == {"ready"}


def test_technical_view_api_lists_snapshot_and_retries_failed_role(tmp_path: Path) -> None:
    provider = TechnicalViewProvider(fail_roles={"right"})
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "design.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
        SOMETHINGS_ON_REFERENCE_CATALOG_DATABASE_PATH=tmp_path / "reference.lancedb",
    )
    app = create_app(settings, image_provider=provider)

    with TestClient(app) as client:
        client.put("/api/projects/look_001", json={"object_name": "Bomber jacket"})
        created = client.post(
            "/api/projects/look_001/versions",
            json={"requested_change": "Create a clean flight jacket study"},
        )
        assert created.status_code == 201
        version = created.json()

        snapshot = client.get("/api/projects/look_001")
        assert snapshot.status_code == 200
        views = snapshot.json()["technical_views"]
        assert len(views) == 3
        assert {item["role"] for item in views} == {"back", "left", "right"}
        failed = next(item for item in views if item["role"] == "right")
        assert failed["status"] == "failed"
        assert failed["asset_url"] is None

        listed = client.get(f"/api/projects/look_001/versions/{version['id']}/technical-views")
        assert listed.status_code == 200
        assert listed.json() == views

        provider.fail_roles.clear()
        retry = client.post(
            f"/api/projects/look_001/versions/{version['id']}/technical-views/right"
        )
        assert retry.status_code == 200
        assert retry.json()["id"] == failed["id"]
        assert retry.json()["status"] == "ready"
        assert retry.json()["asset_url"].startswith("/api/assets/")

        invalid_role = client.post(
            f"/api/projects/look_001/versions/{version['id']}/technical-views/front"
        )
        assert invalid_role.status_code == 422

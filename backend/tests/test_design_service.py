from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from somethings_on.design_store import SQLiteDesignStore
from somethings_on.image_service import DesignImageService, ImageQuality
from somethings_on.models import ProjectSeedInput, TasteSignal


class RecordingImageProvider:
    model = "fake-image"

    def __init__(self) -> None:
        self.reference_paths: list[Path | None] = []
        self.qualities: list[ImageQuality] = []

    async def create(
        self,
        prompt: str,
        reference_path: Path | None = None,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        assert "no logo" in prompt
        self.reference_paths.append(reference_path)
        self.qualities.append(quality)
        output = io.BytesIO()
        Image.new("RGB", (96, 96), "white").save(output, format="PNG")
        return output.getvalue()


@pytest.mark.asyncio
async def test_revisions_are_immutable_and_reference_the_prior_asset(tmp_path: Path) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project(
        "look_001",
        ProjectSeedInput(
            object_name="white T-shirt",
            taste_signals=[
                TasteSignal(
                    id="signal",
                    name="Reference",
                    tags=["washed texture", "boxy proportion"],
                )
            ],
        ),
    )
    provider = RecordingImageProvider()
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()

    first = await service.create_revision(
        project_id="look_001",
        requested_change="Shorten the body by four centimeters",
        preserve=["sleeve volume"],
    )
    second = await service.create_revision(
        project_id="look_001",
        requested_change="Widen the neck rib slightly",
        preserve=["cropped body", "sleeve volume"],
    )

    assert first.version_number == 2
    assert second.version_number == 3
    assert second.parent_version_id == first.id
    assert provider.reference_paths[0] is None
    assert provider.reference_paths[1] is not None
    assert provider.reference_paths[1].is_file()
    assert provider.qualities == ["low", "low"]

    snapshot = await store.get_project("look_001")
    assert [version.version_number for version in snapshot.versions] == [1, 2, 3]
    assert snapshot.versions[1].requested_change == "Shorten the body by four centimeters"

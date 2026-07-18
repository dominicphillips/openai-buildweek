from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from somethings_on.design_agent import build_design_agent
from somethings_on.design_store import DesignVersionNotFoundError, SQLiteDesignStore
from somethings_on.image_service import (
    DesignImageService,
    ImageQuality,
    InvalidImageError,
    RevisionBaseAssetRequired,
)
from somethings_on.models import ProjectSeedInput, TasteSignal


class RecordingImageProvider:
    model = "fake-image"

    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, ImageQuality]] = []
        self.edit_calls: list[tuple[str, Path, bytes, ImageQuality]] = []

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        assert "No person" in prompt
        self.generate_calls.append((prompt, quality))
        return image_bytes("white")

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        assert "No person" in prompt
        self.edit_calls.append((prompt, reference_path, reference_path.read_bytes(), quality))
        return image_bytes("black")


class SvgEditProvider(RecordingImageProvider):
    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.edit_calls.append((prompt, reference_path, reference_path.read_bytes(), quality))
        return b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


class SvgGenerateProvider(RecordingImageProvider):
    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.generate_calls.append((prompt, quality))
        return b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5"/></svg>'


def image_bytes(color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (96, 96), color).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_initial_generation_then_edit_uses_current_raster_and_preserves_lineage(
    tmp_path: Path,
) -> None:
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
    base = (await store.get_project("look_001")).current_version
    assert base is not None
    assert base.status == "concept"
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
    assert first.asset_id is not None
    first_path = await service.resolve_asset(first.asset_id)
    first_bytes_before_edit = first_path.read_bytes()
    second = await service.create_revision(
        project_id="look_001",
        requested_change="Widen the neck rib slightly",
        preserve=["cropped body", "sleeve volume"],
    )

    assert first.id == base.id
    assert first.status == "ready"
    assert first.version_number == 1
    assert first.parent_version_id is None
    assert second.version_number == 2
    assert second.parent_version_id == first.id
    assert len(provider.generate_calls) == 1
    canonical_edit_calls = [
        call
        for call in provider.edit_calls
        if "Make exactly this one requested visible change" in call[0]
    ]
    assert len(canonical_edit_calls) == 1
    initial_prompt, initial_quality = provider.generate_calls[0]
    edit_prompt, reference_path, submitted_reference, edit_quality = canonical_edit_calls[0]
    assert initial_quality == "medium"
    assert edit_quality == "medium"
    assert "Create the first original design study from scratch" in initial_prompt
    assert "washed texture" in initial_prompt
    assert "Make exactly this one requested visible change" in edit_prompt
    assert "Widen the neck rib slightly" in edit_prompt
    assert "Everything outside the requested detail must remain visually unchanged" in edit_prompt
    assert "Do not reinterpret taste traits" in edit_prompt
    assert "washed texture" not in edit_prompt
    assert reference_path == first_path
    assert submitted_reference == first_bytes_before_edit
    assert first_path.read_bytes() == first_bytes_before_edit
    assert second.asset_id is not None
    second_path = await service.resolve_asset(second.asset_id)
    assert second_path != first_path
    assert second_path.read_bytes() != first_bytes_before_edit

    snapshot = await store.get_project("look_001")
    assert [version.version_number for version in snapshot.versions] == [1, 2]
    assert snapshot.versions[0].requested_change == "Shorten the body by four centimeters"
    assert snapshot.versions[0].asset_url == first.asset_url
    assert snapshot.versions[1].asset_url == second.asset_url
    assert snapshot.current_version == second


@pytest.mark.asyncio
async def test_selected_older_version_is_the_exact_branch_parent(tmp_path: Path) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    project = await store.upsert_project(
        "look_001",
        ProjectSeedInput(object_name="distressed bomber and white T-shirt"),
    )
    concept = project.current_version
    assert concept is not None
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
        requested_change="Build the first washed charcoal flight shell",
    )
    second = await service.create_revision(
        project_id="look_001",
        requested_change="Expose only the shoulder seam allowances",
    )
    assert first.asset_id is not None
    assert second.asset_id is not None
    first_path = await service.resolve_asset(first.asset_id)
    first_bytes = first_path.read_bytes()
    second_path = await service.resolve_asset(second.asset_id)
    second_bytes = second_path.read_bytes()

    branch = await service.create_revision(
        project_id="look_001",
        base_version_id=first.id,
        requested_change="Add only a restrained rib texture",
        preserve=["flight-shell silhouette", "washed charcoal color"],
    )

    assert first.id == concept.id
    assert first.version_number == 1
    assert second.version_number == 2
    assert branch.version_number == 3
    assert branch.parent_version_id == first.id
    branch_edit = next(
        call
        for call in reversed(provider.edit_calls)
        if "Add only a restrained rib texture" in call[0]
    )
    assert branch_edit[1] == first_path
    assert branch_edit[2] == first_bytes
    assert first_path.read_bytes() == first_bytes
    assert second_path.read_bytes() == second_bytes
    snapshot = await store.get_project("look_001")
    assert [version.id for version in snapshot.versions] == [
        first.id,
        second.id,
        branch.id,
    ]

    agent = build_design_agent(
        snapshot,
        model="gpt-5.6",
        selected_version=first,
    )
    assert isinstance(agent.instructions, str)
    assert f'"selected_version_id": "{first.id}"' in agent.instructions
    assert f'"latest_version_id": "{branch.id}"' in agent.instructions
    assert '"selected_version_is_latest": false' in agent.instructions
    assert "selected design version is authoritative" in agent.instructions
    assert "deliberately creates a branch" in agent.instructions


@pytest.mark.asyncio
async def test_selected_base_rejects_unknown_cross_project_and_assetless_ids(
    tmp_path: Path,
) -> None:
    store = SQLiteDesignStore(tmp_path / "design.sqlite3")
    await store.initialize()
    await store.upsert_project("look_a", ProjectSeedInput(object_name="white T-shirt"))
    project_b = await store.upsert_project(
        "look_b",
        ProjectSeedInput(object_name="distressed bomber"),
    )
    concept_b = project_b.current_version
    assert concept_b is not None
    provider = RecordingImageProvider()
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / "assets",
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()
    ready_a = await service.create_revision(
        project_id="look_a",
        requested_change="Create the first clean jersey study",
    )

    with pytest.raises(DesignVersionNotFoundError):
        await service.create_revision(
            project_id="look_b",
            base_version_id=ready_a.id,
            requested_change="Attempt a cross-project edit",
        )
    with pytest.raises(DesignVersionNotFoundError):
        await service.create_revision(
            project_id="look_a",
            base_version_id="ver_000000000000",
            requested_change="Attempt an unknown edit",
        )
    with pytest.raises(RevisionBaseAssetRequired, match="no raster to edit"):
        await service.create_revision(
            project_id="look_b",
            base_version_id=concept_b.id,
            requested_change="Attempt to edit a concept",
        )

    assert len(provider.generate_calls) == 1
    assert all(
        "derived technical inspection view" in prompt
        for prompt, _path, _content, _quality in provider.edit_calls
    )
    assert (await store.get_project("look_b")).versions == [concept_b]


@pytest.mark.asyncio
async def test_failed_branch_keeps_selected_parent_and_latest_version_intact(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "design.sqlite3"
    asset_root = tmp_path / "assets"
    store = SQLiteDesignStore(database_path)
    await store.initialize()
    await store.upsert_project("look_001", ProjectSeedInput(object_name="white T-shirt"))
    provider = RecordingImageProvider()
    service = DesignImageService(
        store=store,
        asset_root=asset_root,
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()
    first = await service.create_revision(
        project_id="look_001",
        requested_change="Start from a clean white jersey body",
    )
    assert first.asset_id is not None
    first_path = await service.resolve_asset(first.asset_id)
    first_bytes = first_path.read_bytes()
    second = await service.create_revision(
        project_id="look_001",
        requested_change="Widen only the neck rib",
    )
    assert second.asset_id is not None
    second_path = await service.resolve_asset(second.asset_id)
    second_bytes = second_path.read_bytes()
    failed_provider = SvgEditProvider()
    service.provider = failed_provider

    with pytest.raises(InvalidImageError, match="safe, readable image"):
        await service.create_revision(
            project_id="look_001",
            base_version_id=first.id,
            requested_change="Move only the shoulder seam outward",
        )

    snapshot = await store.get_project("look_001")
    assert snapshot.current_version == second
    assert [version.version_number for version in snapshot.versions] == [1, 2]
    assert first_path.read_bytes() == first_bytes
    assert second_path.read_bytes() == second_bytes
    assert len(list(asset_root.rglob("*.png"))) == 8
    assert len(provider.generate_calls) == 1
    canonical_edit_calls = [
        call
        for call in provider.edit_calls
        if "Make exactly this one requested visible change" in call[0]
    ]
    assert len(canonical_edit_calls) == 1
    assert canonical_edit_calls[0][2] == first_bytes
    assert failed_provider.generate_calls == []
    assert len(failed_provider.edit_calls) == 1
    assert failed_provider.edit_calls[0][1] == first_path
    assert failed_provider.edit_calls[0][2] == first_bytes
    with sqlite3.connect(database_path) as database:
        jobs = database.execute(
            "SELECT status, base_version_id, output_asset_id FROM generation_jobs ORDER BY rowid"
        ).fetchall()
    assert jobs == [
        ("succeeded", None, first.asset_id),
        ("succeeded", first.id, second.asset_id),
        ("failed", first.id, None),
    ]


@pytest.mark.asyncio
async def test_invalid_svg_initial_generation_cannot_report_success(tmp_path: Path) -> None:
    database_path = tmp_path / "design.sqlite3"
    asset_root = tmp_path / "assets"
    store = SQLiteDesignStore(database_path)
    await store.initialize()
    project = await store.upsert_project(
        "look_001",
        ProjectSeedInput(object_name="distressed bomber"),
    )
    base = project.current_version
    assert base is not None
    provider = SvgGenerateProvider()
    service = DesignImageService(
        store=store,
        asset_root=asset_root,
        provider=provider,
        image_model="gpt-image-2",
    )
    await service.initialize()

    with pytest.raises(InvalidImageError, match="safe, readable image"):
        await service.create_revision(
            project_id="look_001",
            requested_change="Create the first distressed flight shell",
        )

    snapshot = await store.get_project("look_001")
    assert snapshot.versions == [base]
    assert snapshot.current_version == base
    assert list(asset_root.rglob("*.png")) == []
    assert len(provider.generate_calls) == 1
    assert provider.edit_calls == []
    with sqlite3.connect(database_path) as database:
        jobs = database.execute(
            "SELECT status, base_version_id, output_asset_id FROM generation_jobs"
        ).fetchall()
    assert jobs == [("failed", None, None)]

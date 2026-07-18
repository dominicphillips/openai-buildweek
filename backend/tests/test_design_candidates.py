from __future__ import annotations

import asyncio
import io
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from somethings_on.config import Settings
from somethings_on.design_store import (
    CandidateSelectionConflictError,
    CandidateSetInProgressError,
    SQLiteDesignStore,
)
from somethings_on.image_service import (
    DesignImageService,
    ImageGenerationUnavailable,
    ImageQuality,
)
from somethings_on.main import create_app
from somethings_on.models import ProjectSeedInput


def image_bytes(color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (96, 128), color).save(output, format="PNG")
    return output.getvalue()


class CandidateImageProvider:
    model = "fake-image"

    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, int, ImageQuality]] = []
        self.edit_calls: list[tuple[str, Path, bytes, int, ImageQuality]] = []
        self.single_edit_calls: list[tuple[str, Path, bytes, ImageQuality]] = []

    async def generate(
        self,
        prompt: str,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        del prompt, quality
        return image_bytes("white")

    async def edit(
        self,
        prompt: str,
        reference_path: Path,
        *,
        quality: ImageQuality = "low",
    ) -> bytes:
        self.single_edit_calls.append(
            (prompt, reference_path, reference_path.read_bytes(), quality)
        )
        return image_bytes("gray")

    async def generate_candidates(
        self,
        prompt: str,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]:
        self.generate_calls.append((prompt, count, quality))
        return [image_bytes(color) for color in ("red", "green", "blue", "yellow")]

    async def edit_candidates(
        self,
        prompt: str,
        reference_path: Path,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]:
        self.edit_calls.append(
            (prompt, reference_path, reference_path.read_bytes(), count, quality)
        )
        return [image_bytes(color) for color in ("red", "green", "blue", "yellow")]


class IncompleteCandidateProvider(CandidateImageProvider):
    async def generate_candidates(
        self,
        prompt: str,
        *,
        count: int,
        quality: ImageQuality = "low",
    ) -> list[bytes]:
        self.generate_calls.append((prompt, count, quality))
        return [image_bytes(color) for color in ("red", "green", "blue")]


async def make_service(
    tmp_path: Path,
    *,
    project_id: str = "look_001",
    object_name: str = "T-shirt",
    provider: CandidateImageProvider | None = None,
) -> tuple[SQLiteDesignStore, DesignImageService, CandidateImageProvider]:
    store = SQLiteDesignStore(tmp_path / f"{project_id}.sqlite3")
    await store.initialize()
    await store.upsert_project(project_id, ProjectSeedInput(object_name=object_name))
    actual_provider = provider or CandidateImageProvider()
    service = DesignImageService(
        store=store,
        asset_root=tmp_path / f"{project_id}-assets",
        provider=actual_provider,
        image_model="gpt-image-2",
    )
    await service.initialize()
    return store, service, actual_provider


@pytest.mark.asyncio
async def test_first_candidate_set_keeps_exact_concept_and_creates_no_version(
    tmp_path: Path,
) -> None:
    store, service, provider = await make_service(tmp_path)
    before = await store.get_project("look_001")
    concept = before.current_version
    assert concept is not None

    candidates = await service.create_candidates(
        project_id="look_001",
        requested_change="Create a heavyweight white jersey study",
        preserve=["clean crew neck"],
        avoid=["logos"],
    )

    assert len(provider.generate_calls) == 1
    prompt, count, quality = provider.generate_calls[0]
    assert "Create the first original design study" in prompt
    assert count == 4
    assert quality == "medium"
    assert [candidate.candidate_index for candidate in candidates] == [1, 2, 3, 4]
    assert {candidate.base_version_id for candidate in candidates} == {concept.id}
    assert {candidate.status for candidate in candidates} == {"ready"}
    assert all(candidate.asset_url.startswith("/api/assets/") for candidate in candidates)

    snapshot = await store.get_project("look_001")
    assert snapshot.versions == [concept]
    assert snapshot.current_version == concept
    assert snapshot.technical_views == []
    assert snapshot.candidates == candidates
    assert len(snapshot.model_dump(mode="json")["candidates"]) == 4
    job = await store.get_generation_job("look_001", candidates[0].generation_job_id)
    assert job.status == "awaiting_selection"
    assert job.base_version_id == concept.id
    assert job.output_asset_id is None


@pytest.mark.asyncio
async def test_candidate_selection_is_atomic_idempotent_and_creates_pending_views(
    tmp_path: Path,
) -> None:
    store, service, provider = await make_service(tmp_path)
    concept = (await store.get_project("look_001")).current_version
    assert concept is not None
    candidates = await service.create_candidates(
        project_id="look_001",
        requested_change="Create a heavyweight white jersey study",
    )
    chosen = candidates[2]

    selected = await service.select_candidate(
        project_id="look_001",
        generation_job_id=chosen.generation_job_id,
        candidate_id=chosen.id,
    )
    repeated = await service.select_candidate(
        project_id="look_001",
        generation_job_id=chosen.generation_job_id,
        candidate_id=chosen.id,
    )

    assert selected == repeated
    assert selected.id == concept.id
    assert selected.version_number == 1
    assert selected.parent_version_id is None
    assert selected.asset_id == chosen.asset_id
    snapshot = await store.get_project("look_001")
    assert snapshot.versions == [selected]
    by_id = {candidate.id: candidate for candidate in snapshot.candidates}
    assert by_id[chosen.id].status == "selected"
    assert by_id[chosen.id].selected_version_id == selected.id
    assert {candidate.status for candidate in snapshot.candidates if candidate.id != chosen.id} == {
        "dismissed"
    }
    assert len(snapshot.technical_views) == 3
    assert {view.role for view in snapshot.technical_views} == {"back", "left", "right"}
    assert {view.status for view in snapshot.technical_views} == {"pending"}
    assert provider.single_edit_calls == []
    job = await store.get_generation_job("look_001", chosen.generation_job_id)
    assert job.status == "succeeded"
    assert job.output_asset_id == chosen.asset_id

    with pytest.raises(CandidateSelectionConflictError, match="already been selected"):
        await service.select_candidate(
            project_id="look_001",
            generation_job_id=chosen.generation_job_id,
            candidate_id=candidates[0].id,
        )


@pytest.mark.asyncio
async def test_edit_candidates_use_exact_selected_canonical_bytes(tmp_path: Path) -> None:
    store, service, provider = await make_service(tmp_path)
    first = await service.create_revision(
        project_id="look_001",
        requested_change="Create the first heavyweight jersey study",
    )
    assert first.asset_id is not None
    canonical_path = await service.resolve_asset(first.asset_id)
    canonical_bytes = canonical_path.read_bytes()
    provider.single_edit_calls.clear()

    candidates = await service.create_candidates(
        project_id="look_001",
        base_version_id=first.id,
        requested_change="Widen only the neck rib",
        preserve=["body length", "sleeve volume"],
    )

    assert len(provider.edit_calls) == 1
    prompt, reference_path, submitted, count, quality = provider.edit_calls[0]
    assert "Widen only the neck rib" in prompt
    assert reference_path == canonical_path
    assert submitted == canonical_bytes
    assert canonical_path.read_bytes() == canonical_bytes
    assert count == 4
    assert quality == "medium"
    assert {candidate.base_version_id for candidate in candidates} == {first.id}
    assert (await store.get_project("look_001")).versions == [first]

    selected = await service.select_candidate(
        project_id="look_001",
        generation_job_id=candidates[0].generation_job_id,
        candidate_id=candidates[0].id,
    )
    assert selected.version_number == 2
    assert selected.parent_version_id == first.id
    assert selected.asset_id == candidates[0].asset_id


@pytest.mark.asyncio
async def test_dismiss_and_concurrent_selection_preserve_one_canonical_lineage(
    tmp_path: Path,
) -> None:
    store, service, _provider = await make_service(tmp_path)
    concept = (await store.get_project("look_001")).current_version
    assert concept is not None
    candidates = await service.create_candidates(
        project_id="look_001",
        requested_change="Create a clean first study",
    )

    outcomes = await asyncio.gather(
        service.select_candidate(
            project_id="look_001",
            generation_job_id=candidates[0].generation_job_id,
            candidate_id=candidates[0].id,
        ),
        service.select_candidate(
            project_id="look_001",
            generation_job_id=candidates[1].generation_job_id,
            candidate_id=candidates[1].id,
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(outcome, Exception) for outcome in outcomes) == 1
    assert sum(isinstance(outcome, CandidateSelectionConflictError) for outcome in outcomes) == 1
    snapshot = await store.get_project("look_001")
    assert len(snapshot.versions) == 1
    assert snapshot.versions[0].id == concept.id
    assert sum(candidate.status == "selected" for candidate in snapshot.candidates) == 1

    store_2, service_2, _provider_2 = await make_service(
        tmp_path,
        project_id="look_002",
    )
    before = await store_2.get_project("look_002")
    discardable = await service_2.create_candidates(
        project_id="look_002",
        requested_change="Create another clean first study",
    )
    dismissed = await service_2.dismiss_candidate_set(
        project_id="look_002",
        generation_job_id=discardable[0].generation_job_id,
    )
    repeated = await service_2.dismiss_candidate_set(
        project_id="look_002",
        generation_job_id=discardable[0].generation_job_id,
    )
    assert dismissed == repeated
    assert {candidate.status for candidate in dismissed} == {"dismissed"}
    assert (await store_2.get_project("look_002")).versions == before.versions
    assert (
        await store_2.get_generation_job("look_002", discardable[0].generation_job_id)
    ).status == "discarded"


@pytest.mark.asyncio
async def test_candidate_failures_and_unresolved_set_keep_current_version(
    tmp_path: Path,
) -> None:
    provider = IncompleteCandidateProvider()
    store, service, _provider = await make_service(tmp_path, provider=provider)
    concept = (await store.get_project("look_001")).current_version
    assert concept is not None

    with pytest.raises(ImageGenerationUnavailable, match="full set"):
        await service.create_candidates(
            project_id="look_001",
            requested_change="Create a first jersey study",
        )
    snapshot = await store.get_project("look_001")
    assert snapshot.versions == [concept]
    assert snapshot.candidates == []
    assert list((tmp_path / "look_001-assets").rglob("*.png")) == []

    service.provider = CandidateImageProvider()
    candidates = await service.create_candidates(
        project_id="look_001",
        requested_change="Create a valid first jersey study",
    )
    with sqlite3.connect(store.database_path) as database:
        database.execute(
            "UPDATE generation_jobs SET updated_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", candidates[0].generation_job_id),
        )
        database.commit()
    with pytest.raises(CandidateSetInProgressError, match="Choose or dismiss"):
        await service.create_candidates(
            project_id="look_001",
            requested_change="Create an overlapping set",
        )
    assert (await store.get_project("look_001")).candidates == candidates
    assert (await store.get_project("look_001")).versions == [concept]
    unresolved = await store.get_generation_job("look_001", candidates[0].generation_job_id)
    assert unresolved.status == "awaiting_selection"


@pytest.mark.asyncio
async def test_project_change_is_blocked_while_candidate_set_awaits_selection(
    tmp_path: Path,
) -> None:
    store, service, _provider = await make_service(tmp_path)
    candidates = await service.create_candidates(
        project_id="look_001",
        requested_change="Create a jersey study",
    )

    with pytest.raises(CandidateSetInProgressError, match="before changing the project"):
        await store.upsert_project(
            "look_001",
            ProjectSeedInput(object_name="Bomber jacket"),
        )
    unchanged = await store.get_project("look_001")
    assert unchanged.object_name == "T-shirt"
    selected = await service.select_candidate(
        project_id="look_001",
        generation_job_id=candidates[0].generation_job_id,
        candidate_id=candidates[0].id,
    )
    assert selected.id == unchanged.current_version.id  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_stale_running_job_is_failed_before_new_candidate_set_job(
    tmp_path: Path,
) -> None:
    store, _service, _provider = await make_service(tmp_path)
    project = await store.get_project("look_001")
    base = project.current_version
    assert base is not None
    stale = await store.create_candidate_generation_job(
        project_id="look_001",
        expected_project_updated_at=project.updated_at.isoformat(),
        base_version_id=base.id,
        expected_base_asset_id=None,
        expected_base_status="concept",
        requested_change="Interrupted render",
        model="gpt-image-2",
    )
    with pytest.raises(CandidateSetInProgressError, match="before changing the project"):
        await store.upsert_project(
            "look_001",
            ProjectSeedInput(object_name="Bomber jacket"),
        )
    await store.update_generation_job(stale.id, status="running")
    with pytest.raises(CandidateSetInProgressError, match="before changing the project"):
        await store.upsert_project(
            "look_001",
            ProjectSeedInput(object_name="Bomber jacket"),
        )
    with sqlite3.connect(store.database_path) as database:
        database.execute(
            "UPDATE generation_jobs SET updated_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", stale.id),
        )
        database.commit()

    replacement = await store.create_candidate_generation_job(
        project_id="look_001",
        expected_project_updated_at=project.updated_at.isoformat(),
        base_version_id=base.id,
        expected_base_asset_id=None,
        expected_base_status="concept",
        requested_change="Recovered render",
        model="gpt-image-2",
    )

    stale_after = await store.get_generation_job("look_001", stale.id)
    assert stale_after.status == "failed"
    assert stale_after.error_code == "stale_generation_job"
    assert replacement.status == "queued"


@pytest.mark.asyncio
async def test_candidate_job_rejects_a_project_snapshot_changed_before_insert(
    tmp_path: Path,
) -> None:
    store, _service, _provider = await make_service(tmp_path)
    stale_snapshot = await store.get_project("look_001")
    stale_version = stale_snapshot.current_version
    assert stale_version is not None
    await store.upsert_project("look_001", ProjectSeedInput(object_name="Bomber jacket"))

    with pytest.raises(CandidateSetInProgressError, match="project changed"):
        await store.create_candidate_generation_job(
            project_id="look_001",
            expected_project_updated_at=stale_snapshot.updated_at.isoformat(),
            base_version_id=stale_version.id,
            expected_base_asset_id=None,
            expected_base_status="concept",
            requested_change="Render from stale T-shirt state",
            model="gpt-image-2",
        )
    with sqlite3.connect(store.database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM generation_jobs").fetchone() == (0,)


@pytest.mark.asyncio
async def test_candidate_job_rejects_a_base_materialized_after_prompt_snapshot(
    tmp_path: Path,
) -> None:
    store, service, _provider = await make_service(tmp_path)
    stale_snapshot = await store.get_project("look_001")
    stale_version = stale_snapshot.current_version
    assert stale_version is not None
    await service.create_revision(
        project_id="look_001",
        requested_change="Create a direct compatibility version",
    )

    with pytest.raises(CandidateSetInProgressError, match="source design changed"):
        await store.create_candidate_generation_job(
            project_id="look_001",
            expected_project_updated_at=stale_snapshot.updated_at.isoformat(),
            base_version_id=stale_version.id,
            expected_base_asset_id=None,
            expected_base_status="concept",
            requested_change="Render from stale concept state",
            model="gpt-image-2",
        )


def test_candidate_set_api_create_select_dismiss_and_cross_project_ids(tmp_path: Path) -> None:
    provider = CandidateImageProvider()
    settings = Settings(
        OPENAI_API_KEY="test-key",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "api.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "api-assets",
        SOMETHINGS_ON_REFERENCE_CATALOG_DATABASE_PATH=tmp_path / "reference.lancedb",
    )
    app = create_app(settings, image_provider=provider)

    with TestClient(app) as client:
        client.put("/api/projects/look_a", json={"object_name": "T-shirt"})
        client.put("/api/projects/look_b", json={"object_name": "Bomber jacket"})
        created = client.post(
            "/api/projects/look_a/candidate-sets",
            json={"requested_change": "Create a heavyweight white jersey study"},
        )
        assert created.status_code == 201
        candidates = created.json()
        assert len(candidates) == 4
        job_id = candidates[0]["generation_job_id"]
        before = client.get("/api/projects/look_a").json()
        assert len(before["versions"]) == 1
        assert before["versions"][0]["status"] == "concept"
        assert len(before["candidates"]) == 4
        blocked_change = client.put(
            "/api/projects/look_a",
            json={"object_name": "Bomber jacket"},
        )
        assert blocked_change.status_code == 409

        cross_project = client.post(
            f"/api/projects/look_b/candidate-sets/{job_id}/select/{candidates[0]['id']}"
        )
        assert cross_project.status_code == 404
        missing_candidate = client.post(
            f"/api/projects/look_a/candidate-sets/{job_id}/select/cand_000000000000"
        )
        assert missing_candidate.status_code == 404

        selected = client.post(
            f"/api/projects/look_a/candidate-sets/{job_id}/select/{candidates[1]['id']}"
        )
        assert selected.status_code == 200
        version = selected.json()
        assert version["version_number"] == 1
        assert version["asset_id"] == candidates[1]["asset_id"]
        snapshot = client.get("/api/projects/look_a").json()
        assert snapshot["current_version"]["id"] == version["id"]
        assert {view["status"] for view in snapshot["technical_views"]} == {"ready"}

        sibling = client.post(
            f"/api/projects/look_a/candidate-sets/{job_id}/select/{candidates[0]['id']}"
        )
        assert sibling.status_code == 409
        dismiss_selected = client.post(f"/api/projects/look_a/candidate-sets/{job_id}/dismiss")
        assert dismiss_selected.status_code == 409

        discardable = client.post(
            "/api/projects/look_b/candidate-sets",
            json={"requested_change": "Create a washed flight jacket study"},
        ).json()
        dismissed = client.post(
            f"/api/projects/look_b/candidate-sets/{discardable[0]['generation_job_id']}/dismiss"
        )
        assert dismissed.status_code == 200
        assert {candidate["status"] for candidate in dismissed.json()} == {"dismissed"}

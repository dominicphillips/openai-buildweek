from __future__ import annotations

import hashlib
import io
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from somethings_on.config import Settings
from somethings_on.demo_seed import (
    DEVDAY_PROJECT_ID,
    DEVDAY_PROJECT_SEED,
    PREPARED_DESIGN_VERSIONS,
    PREPARED_PRESENTATION,
    DevDayDemoSeeder,
)
from somethings_on.design_store import SQLiteDesignStore
from somethings_on.main import create_app


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        OPENAI_API_KEY="",
        SOMETHINGS_ON_DATABASE_PATH=tmp_path / "design.sqlite3",
        SOMETHINGS_ON_ASSET_PATH=tmp_path / "assets",
        SOMETHINGS_ON_REFERENCE_CATALOG_DATABASE_PATH=tmp_path / "reference.lancedb",
    )


def _png_bytes(width: int = 64, height: int = 96) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), "black").save(output, format="PNG")
    return output.getvalue()


def test_devday_seed_is_ready_idempotent_and_independent_of_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.chdir(tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get(f"/api/projects/{DEVDAY_PROJECT_ID}")
        assert response.status_code == 200
        project = response.json()
        assert project["object_name"] == DEVDAY_PROJECT_SEED.object_name
        assert project["taste_signals"] == [
            signal.model_dump(mode="json") for signal in DEVDAY_PROJECT_SEED.taste_signals
        ]

        versions = project["versions"]
        assert [version["version_number"] for version in versions] == [1, 2, 3]
        assert [version["status"] for version in versions] == ["ready", "ready", "ready"]
        assert [version["parent_version_id"] for version in versions] == [
            None,
            versions[0]["id"],
            versions[1]["id"],
        ]
        assert project["current_version"]["id"] == versions[2]["id"]

        for version, prepared in zip(versions, PREPARED_DESIGN_VERSIONS, strict=True):
            assert version["asset_id"] is not None
            assert version["asset_url"] == f"/api/assets/{version['asset_id']}"
            asset = client.get(version["asset_url"])
            assert asset.status_code == 200
            assert asset.headers["content-type"] == "image/png"
            assert hashlib.sha256(asset.content).hexdigest() == prepared.sha256

        assert len(project["presentations"]) == 1
        presentation = project["presentations"][0]
        assert presentation["status"] == "ready"
        assert presentation["design_version_id"] == versions[2]["id"]
        assert presentation["preset_id"] == "edgy-european-guy"
        assert presentation["controls"] == PREPARED_PRESENTATION.controls.model_dump(mode="json")
        assert presentation["asset_url"] is not None
        presentation_asset = client.get(presentation["asset_url"])
        assert presentation_asset.status_code == 200
        assert (
            hashlib.sha256(presentation_asset.content).hexdigest() == PREPARED_PRESENTATION.sha256
        )

        original_ids = {
            "versions": [version["id"] for version in versions],
            "assets": [version["asset_id"] for version in versions]
            + [presentation["output_asset_id"]],
            "presentations": [presentation["id"]],
        }
        put_response = client.put(
            f"/api/projects/{DEVDAY_PROJECT_ID}",
            json=DEVDAY_PROJECT_SEED.model_dump(mode="json"),
        )
        assert put_response.status_code == 200
        assert [version["id"] for version in put_response.json()["versions"]] == original_ids[
            "versions"
        ]

    restored_path = settings.asset_path / "prepared-devday" / "devday-look-v2.png"
    restored_path.unlink()
    assert not restored_path.exists()

    with TestClient(create_app(settings)) as client:
        restarted = client.get(f"/api/projects/{DEVDAY_PROJECT_ID}").json()
        assert [version["id"] for version in restarted["versions"]] == original_ids["versions"]
        assert [version["asset_id"] for version in restarted["versions"]] + [
            restarted["presentations"][0]["output_asset_id"]
        ] == original_ids["assets"]
        assert [render["id"] for render in restarted["presentations"]] == original_ids[
            "presentations"
        ]
        assert restored_path.is_file()
        assert (
            hashlib.sha256(restored_path.read_bytes()).hexdigest()
            == PREPARED_DESIGN_VERSIONS[1].sha256
        )

    with sqlite3.connect(settings.database_path) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM design_versions WHERE project_id = ?",
            (DEVDAY_PROJECT_ID,),
        ).fetchone() == (3,)
        assert database.execute(
            "SELECT COUNT(*) FROM generation_jobs WHERE project_id = ?",
            (DEVDAY_PROJECT_ID,),
        ).fetchone() == (3,)
        assert database.execute(
            "SELECT COUNT(*) FROM design_assets WHERE project_id = ?",
            (DEVDAY_PROJECT_ID,),
        ).fetchone() == (4,)
        assert database.execute(
            "SELECT COUNT(*) FROM presentation_renders WHERE project_id = ?",
            (DEVDAY_PROJECT_ID,),
        ).fetchone() == (1,)
        for index, (version_id, asset_id, prepared) in enumerate(
            zip(
                original_ids["versions"],
                original_ids["assets"][:3],
                PREPARED_DESIGN_VERSIONS,
                strict=True,
            )
        ):
            generation_job_id = database.execute(
                "SELECT generation_job_id FROM design_versions WHERE id = ?",
                (version_id,),
            ).fetchone()[0]
            assert database.execute(
                """
                SELECT base_version_id, requested_change, model, status, output_asset_id
                FROM generation_jobs WHERE id = ?
                """,
                (generation_job_id,),
            ).fetchone() == (
                None if index == 0 else original_ids["versions"][index - 1],
                prepared.requested_change,
                "gpt-image-2",
                "succeeded",
                asset_id,
            )
    assert len(list((settings.asset_path / "prepared-devday").glob("*.png"))) == 4


@pytest.mark.asyncio
async def test_devday_seed_never_replaces_a_user_created_version(tmp_path: Path) -> None:
    database_path = tmp_path / "design.sqlite3"
    asset_root = tmp_path / "assets"
    store = SQLiteDesignStore(database_path)
    await store.initialize()
    project = await store.upsert_project(DEVDAY_PROJECT_ID, DEVDAY_PROJECT_SEED)
    concept = project.current_version
    assert concept is not None

    content = _png_bytes()
    relative_path = Path("user") / "authored-v1.png"
    destination = asset_root / relative_path
    destination.parent.mkdir(parents=True)
    destination.write_bytes(content)
    asset = await store.add_asset(
        project_id=DEVDAY_PROJECT_ID,
        kind="generated",
        storage_path=relative_path.as_posix(),
        mime_type="image/png",
        width=64,
        height=96,
        sha256=hashlib.sha256(content).hexdigest(),
        original_name="authored-v1.png",
    )
    job = await store.create_generation_job(
        project_id=DEVDAY_PROJECT_ID,
        base_version_id=None,
        requested_change="Create my own first distressed bomber study",
        model="gpt-image-2",
    )
    authored = await store.materialize_concept_version(
        project_id=DEVDAY_PROJECT_ID,
        version_id=concept.id,
        asset_id=asset.id,
        generation_job_id=job.id,
        requested_change="Create my own first distressed bomber study",
        preserve=["my selected proportion"],
        avoid=["unrequested changes"],
        prompt="User-authored canonical design prompt.",
    )
    await store.update_generation_job(job.id, status="succeeded", output_asset_id=asset.id)

    before = await store.get_project(DEVDAY_PROJECT_ID)
    seeded = await DevDayDemoSeeder(store=store, asset_root=asset_root).ensure_seeded()

    assert seeded == before
    assert seeded.versions == [authored]
    assert seeded.presentations == []
    assert not (asset_root / "prepared-devday").exists()
    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM design_versions").fetchone() == (1,)
        assert database.execute("SELECT COUNT(*) FROM generation_jobs").fetchone() == (1,)
        assert database.execute("SELECT COUNT(*) FROM design_assets").fetchone() == (1,)
        assert database.execute("SELECT COUNT(*) FROM presentation_renders").fetchone() == (0,)

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from .models import (
    AssetRecord,
    CastingControls,
    DesignVersionRecord,
    GenerationJobRecord,
    LinkReferenceRecord,
    PresentationRenderRecord,
    ProjectSeedInput,
    ProjectSnapshot,
    TasteSignal,
    utc_now,
)


class ProjectNotFoundError(LookupError):
    pass


class AssetNotFoundError(LookupError):
    pass


class DesignVersionNotFoundError(LookupError):
    pass


class SQLiteDesignStore:
    """Canonical application state separate from ChatKit conversation history."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    async def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("PRAGMA journal_mode=WAL")
            await database.execute("PRAGMA foreign_keys=ON")
            await database.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    object_name TEXT NOT NULL,
                    taste_signals TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS design_assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('reference', 'generated')),
                    storage_path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    sha256 TEXT,
                    source_url TEXT,
                    original_name TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS link_references (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS generation_jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    base_version_id TEXT,
                    requested_change TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_asset_id TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS design_versions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    parent_version_id TEXT,
                    asset_id TEXT,
                    generation_job_id TEXT,
                    requested_change TEXT NOT NULL,
                    preserve_items TEXT NOT NULL,
                    avoid_items TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('concept', 'ready')),
                    created_at TEXT NOT NULL,
                    UNIQUE(project_id, version_number),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(asset_id) REFERENCES design_assets(id),
                    FOREIGN KEY(generation_job_id) REFERENCES generation_jobs(id)
                );

                CREATE TABLE IF NOT EXISTS presentation_renders (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    design_version_id TEXT NOT NULL,
                    preset_id TEXT NOT NULL,
                    controls_snapshot TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    avoid_items TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('queued', 'running', 'ready', 'failed', 'rejected')),
                    output_asset_id TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(design_version_id) REFERENCES design_versions(id),
                    FOREIGN KEY(output_asset_id) REFERENCES design_assets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_assets_project_created
                    ON design_assets(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_versions_project_number
                    ON design_versions(project_id, version_number);
                CREATE INDEX IF NOT EXISTS idx_presentations_project_created
                    ON presentation_renders(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_presentations_version_created
                    ON presentation_renders(design_version_id, created_at);
                """
            )
            await database.commit()

    async def upsert_project(self, project_id: str, seed: ProjectSeedInput) -> ProjectSnapshot:
        now = utc_now()
        taste_json = json.dumps(
            [signal.model_dump(mode="json") for signal in seed.taste_signals],
            separators=(",", ":"),
        )
        async with self._connect() as database:
            existing = await self._fetchone(
                database,
                "SELECT object_name FROM projects WHERE id = ?",
                (project_id,),
            )
            object_changed = existing is not None and existing["object_name"] != seed.object_name
            if existing is None:
                await database.execute(
                    """
                    INSERT INTO projects (id, object_name, taste_signals, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (project_id, seed.object_name, taste_json, now.isoformat(), now.isoformat()),
                )
            else:
                await database.execute(
                    """
                    UPDATE projects
                    SET object_name = ?, taste_signals = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (seed.object_name, taste_json, now.isoformat(), project_id),
                )

            current = await self._fetchone(
                database,
                """
                SELECT id, version_number
                FROM design_versions
                WHERE project_id = ?
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (project_id,),
            )
            if current is None or object_changed:
                version_number = 1 if current is None else int(current["version_number"]) + 1
                await database.execute(
                    """
                    INSERT INTO design_versions (
                        id, project_id, version_number, parent_version_id, asset_id,
                        generation_job_id, requested_change, preserve_items, avoid_items,
                        prompt, status, created_at
                    ) VALUES (?, ?, ?, ?, NULL, NULL, ?, '[]', '[]', ?, 'concept', ?)
                    """,
                    (
                        f"ver_{uuid.uuid4().hex[:12]}",
                        project_id,
                        version_number,
                        current["id"] if current else None,
                        f"Base study for {seed.object_name}",
                        "Local vector base study; no generated asset yet.",
                        now.isoformat(),
                    ),
                )
            await database.commit()
        return await self.get_project(project_id)

    async def ensure_project(self, project_id: str) -> ProjectSnapshot:
        try:
            return await self.get_project(project_id)
        except ProjectNotFoundError:
            return await self.upsert_project(project_id, ProjectSeedInput())

    async def get_project(self, project_id: str) -> ProjectSnapshot:
        async with self._connect() as database:
            project = await self._fetchone(
                database,
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            )
            if project is None:
                raise ProjectNotFoundError(project_id)
            asset_rows = await self._fetchall(
                database,
                """
                SELECT * FROM design_assets
                WHERE project_id = ? AND kind = 'reference'
                ORDER BY created_at ASC
                """,
                (project_id,),
            )
            link_rows = await self._fetchall(
                database,
                """
                SELECT * FROM link_references
                WHERE project_id = ?
                ORDER BY created_at ASC
                """,
                (project_id,),
            )
            version_rows = await self._fetchall(
                database,
                """
                SELECT * FROM design_versions
                WHERE project_id = ?
                ORDER BY version_number ASC
                """,
                (project_id,),
            )
            presentation_rows = await self._fetchall(
                database,
                """
                SELECT * FROM presentation_renders
                WHERE project_id = ?
                ORDER BY created_at ASC
                """,
                (project_id,),
            )

        return ProjectSnapshot(
            id=project["id"],
            object_name=project["object_name"],
            taste_signals=[
                TasteSignal.model_validate(signal)
                for signal in json.loads(project["taste_signals"])
            ],
            references=[self._asset_from_row(row) for row in asset_rows],
            link_references=[self._link_from_row(row) for row in link_rows],
            versions=[self._version_from_row(row) for row in version_rows],
            presentations=[self._presentation_from_row(row) for row in presentation_rows],
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )

    async def add_link_reference(
        self,
        project_id: str,
        url: str,
        label: str,
    ) -> LinkReferenceRecord:
        await self.ensure_project(project_id)
        record = LinkReferenceRecord(
            id=f"lnk_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            url=url,
            label=label,
            created_at=utc_now(),
        )
        await self._execute(
            """
            INSERT INTO link_references (id, project_id, url, label, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                record.url,
                record.label,
                record.created_at.isoformat(),
            ),
        )
        return record

    async def add_asset(
        self,
        *,
        project_id: str,
        kind: Literal["reference", "generated"],
        storage_path: str,
        mime_type: str,
        width: int,
        height: int,
        sha256: str,
        original_name: str | None = None,
        source_url: str | None = None,
    ) -> AssetRecord:
        await self.ensure_project(project_id)
        record = AssetRecord(
            id=f"ast_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            kind=kind,
            mime_type=mime_type,
            width=width,
            height=height,
            sha256=sha256,
            source_url=source_url,
            original_name=original_name,
            created_at=utc_now(),
        )
        await self._execute(
            """
            INSERT INTO design_assets (
                id, project_id, kind, storage_path, mime_type, width, height,
                sha256, source_url, original_name, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                record.kind,
                storage_path,
                record.mime_type,
                record.width,
                record.height,
                record.sha256,
                record.source_url,
                record.original_name,
                record.created_at.isoformat(),
            ),
        )
        return record

    async def get_asset_location(self, asset_id: str) -> tuple[AssetRecord, str]:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                "SELECT * FROM design_assets WHERE id = ?",
                (asset_id,),
            )
        if row is None:
            raise AssetNotFoundError(asset_id)
        return self._asset_from_row(row), row["storage_path"]

    async def create_generation_job(
        self,
        *,
        project_id: str,
        base_version_id: str | None,
        requested_change: str,
        model: str,
    ) -> GenerationJobRecord:
        now = utc_now()
        record = GenerationJobRecord(
            id=f"job_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            base_version_id=base_version_id,
            requested_change=requested_change,
            model=model,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        await self._execute(
            """
            INSERT INTO generation_jobs (
                id, project_id, base_version_id, requested_change, model, status,
                output_asset_id, error_code, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                record.base_version_id,
                record.requested_change,
                record.model,
                record.status,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
            ),
        )
        return record

    async def update_generation_job(
        self,
        job_id: str,
        *,
        status: Literal["running", "succeeded", "failed"],
        output_asset_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        await self._execute(
            """
            UPDATE generation_jobs
            SET status = ?, output_asset_id = ?, error_code = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, output_asset_id, error_code, utc_now().isoformat(), job_id),
        )

    async def add_design_version(
        self,
        *,
        project_id: str,
        parent_version_id: str | None,
        asset_id: str,
        generation_job_id: str,
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
        prompt: str,
    ) -> DesignVersionRecord:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                """
                SELECT COALESCE(MAX(version_number), 0) AS current_number
                FROM design_versions WHERE project_id = ?
                """,
                (project_id,),
            )
            version_number = int(row["current_number"]) + 1
            record = DesignVersionRecord(
                id=f"ver_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                version_number=version_number,
                parent_version_id=parent_version_id,
                asset_id=asset_id,
                generation_job_id=generation_job_id,
                requested_change=requested_change,
                preserve=preserve,
                avoid=avoid,
                prompt=prompt,
                status="ready",
                created_at=utc_now(),
            )
            await database.execute(
                """
                INSERT INTO design_versions (
                    id, project_id, version_number, parent_version_id, asset_id,
                    generation_job_id, requested_change, preserve_items, avoid_items,
                    prompt, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.version_number,
                    record.parent_version_id,
                    record.asset_id,
                    record.generation_job_id,
                    record.requested_change,
                    json.dumps(record.preserve),
                    json.dumps(record.avoid),
                    record.prompt,
                    record.status,
                    record.created_at.isoformat(),
                ),
            )
            await database.commit()
        return record

    async def latest_version(self, project_id: str) -> DesignVersionRecord | None:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                """
                SELECT * FROM design_versions
                WHERE project_id = ?
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (project_id,),
            )
        return self._version_from_row(row) if row else None

    async def get_design_version(
        self,
        project_id: str,
        version_id: str,
    ) -> DesignVersionRecord:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                """
                SELECT * FROM design_versions
                WHERE project_id = ? AND id = ?
                """,
                (project_id, version_id),
            )
        if row is None:
            raise DesignVersionNotFoundError(version_id)
        return self._version_from_row(row)

    async def create_presentation_render(
        self,
        *,
        project_id: str,
        design_version_id: str,
        preset_id: str,
        controls: CastingControls,
        prompt: str,
        avoid: list[str],
        model: str,
    ) -> PresentationRenderRecord:
        now = utc_now()
        record = PresentationRenderRecord(
            id=f"pre_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            design_version_id=design_version_id,
            preset_id=preset_id,
            controls=controls,
            prompt=prompt,
            avoid=avoid,
            model=model,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        await self._execute(
            """
            INSERT INTO presentation_renders (
                id, project_id, design_version_id, preset_id, controls_snapshot,
                prompt, avoid_items, model, status, output_asset_id, error_code,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                record.design_version_id,
                record.preset_id,
                json.dumps(record.controls.model_dump(mode="json"), separators=(",", ":")),
                record.prompt,
                json.dumps(record.avoid, separators=(",", ":")),
                record.model,
                record.status,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
            ),
        )
        return record

    async def update_presentation_render(
        self,
        render_id: str,
        *,
        status: Literal["running", "ready", "failed", "rejected"],
        output_asset_id: str | None = None,
        error_code: str | None = None,
    ) -> PresentationRenderRecord:
        await self._execute(
            """
            UPDATE presentation_renders
            SET status = ?, output_asset_id = ?, error_code = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                output_asset_id,
                error_code,
                utc_now().isoformat(),
                render_id,
            ),
        )
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                "SELECT * FROM presentation_renders WHERE id = ?",
                (render_id,),
            )
        if row is None:
            raise LookupError(render_id)
        return self._presentation_from_row(row)

    async def list_presentations(self, project_id: str) -> list[PresentationRenderRecord]:
        async with self._connect() as database:
            rows = await self._fetchall(
                database,
                """
                SELECT * FROM presentation_renders
                WHERE project_id = ?
                ORDER BY created_at ASC
                """,
                (project_id,),
            )
        return [self._presentation_from_row(row) for row in rows]

    async def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        async with self._connect() as database:
            await database.execute(query, params)
            await database.commit()

    def _connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.database_path)

    @staticmethod
    async def _fetchone(
        database: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...],
    ) -> aiosqlite.Row | None:
        database.row_factory = aiosqlite.Row
        cursor = await database.execute(query, params)
        return await cursor.fetchone()

    @staticmethod
    async def _fetchall(
        database: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...],
    ) -> list[aiosqlite.Row]:
        database.row_factory = aiosqlite.Row
        cursor = await database.execute(query, params)
        return list(await cursor.fetchall())

    @staticmethod
    def _asset_from_row(row: aiosqlite.Row) -> AssetRecord:
        return AssetRecord(
            id=row["id"],
            project_id=row["project_id"],
            kind=row["kind"],
            mime_type=row["mime_type"],
            width=row["width"],
            height=row["height"],
            sha256=row["sha256"],
            source_url=row["source_url"],
            original_name=row["original_name"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _link_from_row(row: aiosqlite.Row) -> LinkReferenceRecord:
        return LinkReferenceRecord(
            id=row["id"],
            project_id=row["project_id"],
            url=row["url"],
            label=row["label"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _version_from_row(row: aiosqlite.Row) -> DesignVersionRecord:
        return DesignVersionRecord(
            id=row["id"],
            project_id=row["project_id"],
            version_number=row["version_number"],
            parent_version_id=row["parent_version_id"],
            asset_id=row["asset_id"],
            generation_job_id=row["generation_job_id"],
            requested_change=row["requested_change"],
            preserve=json.loads(row["preserve_items"]),
            avoid=json.loads(row["avoid_items"]),
            prompt=row["prompt"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _presentation_from_row(row: aiosqlite.Row) -> PresentationRenderRecord:
        return PresentationRenderRecord(
            id=row["id"],
            project_id=row["project_id"],
            design_version_id=row["design_version_id"],
            preset_id=row["preset_id"],
            controls=CastingControls.model_validate(json.loads(row["controls_snapshot"])),
            prompt=row["prompt"],
            avoid=json.loads(row["avoid_items"]),
            model=row["model"],
            status=row["status"],
            output_asset_id=row["output_asset_id"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

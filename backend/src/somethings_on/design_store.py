from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from .models import (
    AssetRecord,
    CastingControls,
    DesignCandidateRecord,
    DesignVersionRecord,
    GenerationJobRecord,
    GenerationJobStatus,
    LinkReferenceRecord,
    PresentationRenderRecord,
    ProjectSeedInput,
    ProjectSnapshot,
    TasteSignal,
    TechnicalViewRecord,
    TechnicalViewRole,
    utc_now,
)


class ProjectNotFoundError(LookupError):
    pass


class AssetNotFoundError(LookupError):
    pass


class DesignVersionNotFoundError(LookupError):
    pass


class TechnicalViewNotFoundError(LookupError):
    pass


class CandidateSetNotFoundError(LookupError):
    pass


class DesignCandidateNotFoundError(LookupError):
    pass


class CandidateSelectionConflictError(RuntimeError):
    pass


class CandidateSetInProgressError(RuntimeError):
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

                CREATE TABLE IF NOT EXISTS design_candidates (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    generation_job_id TEXT NOT NULL,
                    base_version_id TEXT,
                    candidate_index INTEGER NOT NULL CHECK(candidate_index BETWEEN 1 AND 4),
                    requested_change TEXT NOT NULL,
                    preserve_items TEXT NOT NULL,
                    avoid_items TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('ready', 'selected', 'dismissed')),
                    asset_id TEXT NOT NULL,
                    selected_version_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(generation_job_id, candidate_index),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(generation_job_id) REFERENCES generation_jobs(id) ON DELETE CASCADE,
                    FOREIGN KEY(base_version_id) REFERENCES design_versions(id),
                    FOREIGN KEY(asset_id) REFERENCES design_assets(id),
                    FOREIGN KEY(selected_version_id) REFERENCES design_versions(id)
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

                CREATE TABLE IF NOT EXISTS technical_views (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    design_version_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('back', 'left', 'right')),
                    prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('pending', 'running', 'ready', 'failed')),
                    output_asset_id TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(design_version_id, role),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(design_version_id) REFERENCES design_versions(id) ON DELETE CASCADE,
                    FOREIGN KEY(output_asset_id) REFERENCES design_assets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_assets_project_created
                    ON design_assets(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_versions_project_number
                    ON design_versions(project_id, version_number);
                CREATE INDEX IF NOT EXISTS idx_candidates_project_created
                    ON design_candidates(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_candidates_job_index
                    ON design_candidates(generation_job_id, candidate_index);
                CREATE INDEX IF NOT EXISTS idx_presentations_project_created
                    ON presentation_renders(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_presentations_version_created
                    ON presentation_renders(design_version_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_technical_views_project_version
                    ON technical_views(project_id, design_version_id);
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
            await database.execute("BEGIN IMMEDIATE")
            try:
                existing = await self._fetchone(
                    database,
                    "SELECT object_name, taste_signals FROM projects WHERE id = ?",
                    (project_id,),
                )
                if existing is not None and (
                    existing["object_name"] != seed.object_name
                    or existing["taste_signals"] != taste_json
                ):
                    unresolved = await self._fetchone(
                        database,
                        """
                        SELECT id FROM generation_jobs
                        WHERE project_id = ?
                            AND status IN ('queued', 'running', 'awaiting_selection')
                        LIMIT 1
                        """,
                        (project_id,),
                    )
                    if unresolved is not None:
                        raise CandidateSetInProgressError(
                            "Choose or dismiss the current options before changing the project."
                        )
                object_changed = (
                    existing is not None and existing["object_name"] != seed.object_name
                )
                if existing is None:
                    await database.execute(
                        """
                        INSERT INTO projects (
                            id, object_name, taste_signals, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            seed.object_name,
                            taste_json,
                            now.isoformat(),
                            now.isoformat(),
                        ),
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
            except Exception:
                await database.rollback()
                raise
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
            candidate_rows = await self._fetchall(
                database,
                """
                SELECT * FROM design_candidates
                WHERE project_id = ?
                ORDER BY created_at ASC, candidate_index ASC
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
            technical_view_rows = await self._fetchall(
                database,
                """
                SELECT * FROM technical_views
                WHERE project_id = ?
                ORDER BY created_at ASC, role ASC
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
            candidates=[self._candidate_from_row(row) for row in candidate_rows],
            technical_views=[self._technical_view_from_row(row) for row in technical_view_rows],
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

    async def find_asset_by_provenance(
        self,
        *,
        project_id: str,
        source_url: str,
        sha256: str,
    ) -> tuple[AssetRecord, str] | None:
        """Find an already imported local artifact without duplicating its database row."""

        async with self._connect() as database:
            row = await self._fetchone(
                database,
                """
                SELECT * FROM design_assets
                WHERE project_id = ? AND source_url = ? AND sha256 = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (project_id, source_url, sha256),
            )
        if row is None:
            return None
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

    async def create_candidate_generation_job(
        self,
        *,
        project_id: str,
        expected_project_updated_at: str,
        base_version_id: str | None,
        expected_base_asset_id: str | None,
        expected_base_status: Literal["concept", "ready"] | None,
        requested_change: str,
        model: str,
    ) -> GenerationJobRecord:
        """Create one candidate-set job while preventing unresolved-set races."""

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
        async with self._connect() as database:
            await database.execute("BEGIN IMMEDIATE")
            try:
                stale_before = now - timedelta(minutes=30)
                await database.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'failed', error_code = 'stale_generation_job', updated_at = ?
                    WHERE project_id = ? AND status IN ('queued', 'running')
                        AND updated_at < ?
                    """,
                    (now.isoformat(), project_id, stale_before.isoformat()),
                )
                existing = await self._fetchone(
                    database,
                    """
                    SELECT id FROM generation_jobs
                    WHERE project_id = ?
                        AND status IN ('queued', 'running', 'awaiting_selection')
                    LIMIT 1
                    """,
                    (project_id,),
                )
                if existing is not None:
                    raise CandidateSetInProgressError(
                        "Choose or dismiss the current options before making another set."
                    )
                project = await self._fetchone(
                    database,
                    "SELECT updated_at FROM projects WHERE id = ?",
                    (project_id,),
                )
                if project is None:
                    raise ProjectNotFoundError(project_id)
                if project["updated_at"] != expected_project_updated_at:
                    raise CandidateSetInProgressError(
                        "The project changed before rendering began. Review it and try again."
                    )
                if base_version_id is not None:
                    base = await self._fetchone(
                        database,
                        """
                        SELECT asset_id, status FROM design_versions
                        WHERE project_id = ? AND id = ?
                        """,
                        (project_id, base_version_id),
                    )
                    if (
                        base is None
                        or base["asset_id"] != expected_base_asset_id
                        or base["status"] != expected_base_status
                    ):
                        raise CandidateSetInProgressError(
                            "The source design changed before rendering began. "
                            "Review it and try again."
                        )
                await database.execute(
                    """
                    INSERT INTO generation_jobs (
                        id, project_id, base_version_id, requested_change, model, status,
                        output_asset_id, error_code, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'queued', NULL, NULL, ?, ?)
                    """,
                    (
                        record.id,
                        record.project_id,
                        record.base_version_id,
                        record.requested_change,
                        record.model,
                        record.created_at.isoformat(),
                        record.updated_at.isoformat(),
                    ),
                )
                await database.commit()
            except Exception:
                await database.rollback()
                raise
        return record

    async def update_generation_job(
        self,
        job_id: str,
        *,
        status: GenerationJobStatus,
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

    async def get_generation_job(
        self,
        project_id: str,
        job_id: str,
    ) -> GenerationJobRecord:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                "SELECT * FROM generation_jobs WHERE project_id = ? AND id = ?",
                (project_id, job_id),
            )
        if row is None:
            raise CandidateSetNotFoundError(job_id)
        return self._generation_job_from_row(row)

    async def materialize_concept_version(
        self,
        *,
        project_id: str,
        version_id: str,
        asset_id: str,
        generation_job_id: str,
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
        prompt: str,
    ) -> DesignVersionRecord:
        """Turn one provisional assetless concept into its first immutable raster version."""

        async with self._connect() as database:
            cursor = await database.execute(
                """
                UPDATE design_versions
                SET asset_id = ?, generation_job_id = ?, requested_change = ?,
                    preserve_items = ?, avoid_items = ?, prompt = ?, status = 'ready',
                    created_at = ?
                WHERE project_id = ? AND id = ?
                    AND status = 'concept' AND asset_id IS NULL
                """,
                (
                    asset_id,
                    generation_job_id,
                    requested_change,
                    json.dumps(preserve),
                    json.dumps(avoid),
                    prompt,
                    utc_now().isoformat(),
                    project_id,
                    version_id,
                ),
            )
            if cursor.rowcount != 1:
                existing = await self._fetchone(
                    database,
                    "SELECT id FROM design_versions WHERE project_id = ? AND id = ?",
                    (project_id, version_id),
                )
                if existing is None:
                    raise DesignVersionNotFoundError(version_id)
                raise ValueError("Only an assetless concept can become the first raster version.")
            row = await self._fetchone(
                database,
                "SELECT * FROM design_versions WHERE project_id = ? AND id = ?",
                (project_id, version_id),
            )
            await database.commit()

        if row is None:  # pragma: no cover - guarded by the successful update above
            raise DesignVersionNotFoundError(version_id)
        return self._version_from_row(row)

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

    async def create_design_candidates(
        self,
        *,
        project_id: str,
        generation_job_id: str,
        base_version_id: str | None,
        requested_change: str,
        preserve: list[str],
        avoid: list[str],
        prompt: str,
        model: str,
        asset_ids: list[str],
    ) -> list[DesignCandidateRecord]:
        """Persist one complete four-option set after every raster is validated."""

        if len(asset_ids) != 4:
            raise ValueError("A candidate set must contain exactly four images.")
        now = utc_now()
        records = [
            DesignCandidateRecord(
                id=f"cand_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                generation_job_id=generation_job_id,
                base_version_id=base_version_id,
                candidate_index=index,
                requested_change=requested_change,
                preserve=preserve,
                avoid=avoid,
                prompt=prompt,
                model=model,
                status="ready",
                asset_id=asset_id,
                created_at=now,
                updated_at=now,
            )
            for index, asset_id in enumerate(asset_ids, start=1)
        ]
        async with self._connect() as database:
            await database.execute("BEGIN IMMEDIATE")
            try:
                job = await self._fetchone(
                    database,
                    "SELECT * FROM generation_jobs WHERE project_id = ? AND id = ?",
                    (project_id, generation_job_id),
                )
                if job is None:
                    raise CandidateSetNotFoundError(generation_job_id)
                if job["status"] != "running":
                    raise CandidateSelectionConflictError(
                        "This candidate set is not accepting generated images."
                    )
                if job["base_version_id"] != base_version_id:
                    raise CandidateSelectionConflictError(
                        "The candidate set source does not match its generation job."
                    )
                await database.executemany(
                    """
                    INSERT INTO design_candidates (
                        id, project_id, generation_job_id, base_version_id, candidate_index,
                        requested_change, preserve_items, avoid_items, prompt, model, status,
                        asset_id, selected_version_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, NULL, ?, ?)
                    """,
                    [
                        (
                            record.id,
                            record.project_id,
                            record.generation_job_id,
                            record.base_version_id,
                            record.candidate_index,
                            record.requested_change,
                            json.dumps(record.preserve),
                            json.dumps(record.avoid),
                            record.prompt,
                            record.model,
                            record.asset_id,
                            record.created_at.isoformat(),
                            record.updated_at.isoformat(),
                        )
                        for record in records
                    ],
                )
                cursor = await database.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'awaiting_selection', output_asset_id = NULL,
                        error_code = NULL, updated_at = ?
                    WHERE id = ? AND status = 'running'
                    """,
                    (now.isoformat(), generation_job_id),
                )
                if cursor.rowcount != 1:  # pragma: no cover - locked status check above
                    raise CandidateSelectionConflictError(
                        "This candidate set is not accepting generated images."
                    )
                await database.commit()
            except Exception:
                await database.rollback()
                raise
        return records

    async def list_design_candidates(
        self,
        project_id: str,
        *,
        generation_job_id: str | None = None,
    ) -> list[DesignCandidateRecord]:
        query = "SELECT * FROM design_candidates WHERE project_id = ?"
        params: tuple[Any, ...] = (project_id,)
        if generation_job_id is not None:
            query += " AND generation_job_id = ?"
            params = (project_id, generation_job_id)
        query += " ORDER BY created_at ASC, candidate_index ASC"
        async with self._connect() as database:
            rows = await self._fetchall(database, query, params)
        return [self._candidate_from_row(row) for row in rows]

    async def delete_unlinked_assets(self, asset_ids: list[str]) -> None:
        """Remove candidate assets only while no domain record references them."""

        if not asset_ids:
            return
        placeholders = ",".join("?" for _ in asset_ids)
        async with self._connect() as database:
            referenced = await self._fetchone(
                database,
                f"""
                SELECT 1
                FROM design_candidates
                WHERE asset_id IN ({placeholders})
                UNION ALL
                SELECT 1
                FROM design_versions
                WHERE asset_id IN ({placeholders})
                LIMIT 1
                """,
                tuple(asset_ids + asset_ids),
            )
            if referenced is not None:
                raise CandidateSelectionConflictError("A linked design asset cannot be discarded.")
            await database.execute(
                f"DELETE FROM design_assets WHERE id IN ({placeholders})",
                tuple(asset_ids),
            )
            await database.commit()

    async def select_design_candidate(
        self,
        *,
        project_id: str,
        generation_job_id: str,
        candidate_id: str,
        technical_views: list[tuple[TechnicalViewRole, str, str]],
    ) -> tuple[DesignVersionRecord, bool]:
        """Atomically turn one option into garment truth and dismiss its siblings."""

        async with self._connect() as database:
            await database.execute("BEGIN IMMEDIATE")
            try:
                job = await self._fetchone(
                    database,
                    "SELECT * FROM generation_jobs WHERE project_id = ? AND id = ?",
                    (project_id, generation_job_id),
                )
                if job is None:
                    raise CandidateSetNotFoundError(generation_job_id)
                candidate = await self._fetchone(
                    database,
                    """
                    SELECT * FROM design_candidates
                    WHERE project_id = ? AND generation_job_id = ? AND id = ?
                    """,
                    (project_id, generation_job_id, candidate_id),
                )
                if candidate is None:
                    raise DesignCandidateNotFoundError(candidate_id)

                if candidate["status"] == "selected" and candidate["selected_version_id"]:
                    existing = await self._fetchone(
                        database,
                        "SELECT * FROM design_versions WHERE project_id = ? AND id = ?",
                        (project_id, candidate["selected_version_id"]),
                    )
                    if existing is None:  # pragma: no cover - protected by the transaction
                        raise CandidateSelectionConflictError(
                            "The selected version is no longer available."
                        )
                    await database.commit()
                    return self._version_from_row(existing), False

                selected_sibling = await self._fetchone(
                    database,
                    """
                    SELECT id FROM design_candidates
                    WHERE generation_job_id = ? AND status = 'selected'
                    LIMIT 1
                    """,
                    (generation_job_id,),
                )
                if selected_sibling is not None:
                    raise CandidateSelectionConflictError(
                        "Another option from this set has already been selected."
                    )
                if job["status"] != "awaiting_selection" or candidate["status"] != "ready":
                    raise CandidateSelectionConflictError(
                        "This candidate set is no longer available for selection."
                    )

                now = utc_now()
                base = None
                if candidate["base_version_id"] is not None:
                    base = await self._fetchone(
                        database,
                        """
                        SELECT * FROM design_versions
                        WHERE project_id = ? AND id = ?
                        """,
                        (project_id, candidate["base_version_id"]),
                    )
                    if base is None:
                        raise CandidateSelectionConflictError(
                            "The source design version is no longer available."
                        )

                if base is not None and base["status"] == "concept" and base["asset_id"] is None:
                    latest = await self._fetchone(
                        database,
                        """
                        SELECT id FROM design_versions
                        WHERE project_id = ?
                        ORDER BY version_number DESC
                        LIMIT 1
                        """,
                        (project_id,),
                    )
                    if latest is None or latest["id"] != base["id"]:
                        raise CandidateSelectionConflictError(
                            "The starting design changed before this option was selected."
                        )
                    cursor = await database.execute(
                        """
                        UPDATE design_versions
                        SET asset_id = ?, generation_job_id = ?, requested_change = ?,
                            preserve_items = ?, avoid_items = ?, prompt = ?, status = 'ready',
                            created_at = ?
                        WHERE project_id = ? AND id = ?
                            AND status = 'concept' AND asset_id IS NULL
                        """,
                        (
                            candidate["asset_id"],
                            generation_job_id,
                            candidate["requested_change"],
                            candidate["preserve_items"],
                            candidate["avoid_items"],
                            candidate["prompt"],
                            now.isoformat(),
                            project_id,
                            base["id"],
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise CandidateSelectionConflictError(
                            "The starting design changed before this option was selected."
                        )
                    version_id = base["id"]
                else:
                    if base is None or base["status"] != "ready" or base["asset_id"] is None:
                        raise CandidateSelectionConflictError(
                            "The source design version is no longer available."
                        )
                    sequence = await self._fetchone(
                        database,
                        """
                        SELECT COALESCE(MAX(version_number), 0) AS current_number
                        FROM design_versions WHERE project_id = ?
                        """,
                        (project_id,),
                    )
                    version_id = f"ver_{uuid.uuid4().hex[:12]}"
                    await database.execute(
                        """
                        INSERT INTO design_versions (
                            id, project_id, version_number, parent_version_id, asset_id,
                            generation_job_id, requested_change, preserve_items, avoid_items,
                            prompt, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?)
                        """,
                        (
                            version_id,
                            project_id,
                            int(sequence["current_number"]) + 1,
                            candidate["base_version_id"],
                            candidate["asset_id"],
                            generation_job_id,
                            candidate["requested_change"],
                            candidate["preserve_items"],
                            candidate["avoid_items"],
                            candidate["prompt"],
                            now.isoformat(),
                        ),
                    )

                for role, view_prompt, view_model in technical_views:
                    await database.execute(
                        """
                        INSERT OR IGNORE INTO technical_views (
                            id, project_id, design_version_id, role, prompt, model, status,
                            output_asset_id, error_code, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?, ?)
                        """,
                        (
                            f"view_{uuid.uuid4().hex[:12]}",
                            project_id,
                            version_id,
                            role,
                            view_prompt,
                            view_model,
                            now.isoformat(),
                            now.isoformat(),
                        ),
                    )

                await database.execute(
                    """
                    UPDATE design_candidates
                    SET status = 'selected', selected_version_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (version_id, now.isoformat(), candidate_id),
                )
                await database.execute(
                    """
                    UPDATE design_candidates
                    SET status = 'dismissed', updated_at = ?
                    WHERE generation_job_id = ? AND id != ? AND status = 'ready'
                    """,
                    (now.isoformat(), generation_job_id, candidate_id),
                )
                await database.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'succeeded', output_asset_id = ?, error_code = NULL,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (candidate["asset_id"], now.isoformat(), generation_job_id),
                )
                version = await self._fetchone(
                    database,
                    "SELECT * FROM design_versions WHERE project_id = ? AND id = ?",
                    (project_id, version_id),
                )
                await database.commit()
            except Exception:
                await database.rollback()
                raise
        if version is None:  # pragma: no cover - guarded by insert/update above
            raise DesignVersionNotFoundError(version_id)
        return self._version_from_row(version), True

    async def dismiss_design_candidates(
        self,
        *,
        project_id: str,
        generation_job_id: str,
    ) -> list[DesignCandidateRecord]:
        """Dismiss an unselected set without changing the current design version."""

        async with self._connect() as database:
            await database.execute("BEGIN IMMEDIATE")
            try:
                job = await self._fetchone(
                    database,
                    "SELECT * FROM generation_jobs WHERE project_id = ? AND id = ?",
                    (project_id, generation_job_id),
                )
                if job is None:
                    raise CandidateSetNotFoundError(generation_job_id)
                if job["status"] == "succeeded":
                    raise CandidateSelectionConflictError(
                        "A selected candidate set cannot be dismissed."
                    )
                if job["status"] not in {"awaiting_selection", "discarded"}:
                    raise CandidateSelectionConflictError(
                        "This candidate set is not available for dismissal."
                    )
                if job["status"] == "awaiting_selection":
                    now = utc_now().isoformat()
                    await database.execute(
                        """
                        UPDATE design_candidates
                        SET status = 'dismissed', updated_at = ?
                        WHERE generation_job_id = ? AND status = 'ready'
                        """,
                        (now, generation_job_id),
                    )
                    await database.execute(
                        """
                        UPDATE generation_jobs
                        SET status = 'discarded', output_asset_id = NULL, error_code = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, generation_job_id),
                    )
                rows = await self._fetchall(
                    database,
                    """
                    SELECT * FROM design_candidates
                    WHERE project_id = ? AND generation_job_id = ?
                    ORDER BY candidate_index ASC
                    """,
                    (project_id, generation_job_id),
                )
                await database.commit()
            except Exception:
                await database.rollback()
                raise
        return [self._candidate_from_row(row) for row in rows]

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

    async def ensure_technical_view(
        self,
        *,
        project_id: str,
        design_version_id: str,
        role: TechnicalViewRole,
        prompt: str,
        model: str,
    ) -> TechnicalViewRecord:
        """Create one pending derived-view slot, or return its existing durable record."""

        now = utc_now()
        async with self._connect() as database:
            version = await self._fetchone(
                database,
                "SELECT id FROM design_versions WHERE project_id = ? AND id = ?",
                (project_id, design_version_id),
            )
            if version is None:
                raise DesignVersionNotFoundError(design_version_id)
            await database.execute(
                """
                INSERT OR IGNORE INTO technical_views (
                    id, project_id, design_version_id, role, prompt, model, status,
                    output_asset_id, error_code, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?, ?)
                """,
                (
                    f"view_{uuid.uuid4().hex[:12]}",
                    project_id,
                    design_version_id,
                    role,
                    prompt,
                    model,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            row = await self._fetchone(
                database,
                """
                SELECT * FROM technical_views
                WHERE project_id = ? AND design_version_id = ? AND role = ?
                """,
                (project_id, design_version_id, role),
            )
            await database.commit()
        if row is None:  # pragma: no cover - guarded by insert/select above
            raise TechnicalViewNotFoundError(f"{design_version_id}:{role}")
        return self._technical_view_from_row(row)

    async def claim_technical_view(self, view_id: str) -> tuple[TechnicalViewRecord, bool]:
        """Atomically claim a pending/failed view so duplicate requests cannot double-render."""

        async with self._connect() as database:
            cursor = await database.execute(
                """
                UPDATE technical_views
                SET status = 'running', output_asset_id = NULL, error_code = NULL, updated_at = ?
                WHERE id = ? AND status IN ('pending', 'failed')
                """,
                (utc_now().isoformat(), view_id),
            )
            row = await self._fetchone(
                database,
                "SELECT * FROM technical_views WHERE id = ?",
                (view_id,),
            )
            await database.commit()
        if row is None:
            raise TechnicalViewNotFoundError(view_id)
        return self._technical_view_from_row(row), cursor.rowcount == 1

    async def update_technical_view(
        self,
        view_id: str,
        *,
        status: Literal["ready", "failed"],
        output_asset_id: str | None = None,
        error_code: str | None = None,
    ) -> TechnicalViewRecord:
        async with self._connect() as database:
            await database.execute(
                """
                UPDATE technical_views
                SET status = ?, output_asset_id = ?, error_code = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, output_asset_id, error_code, utc_now().isoformat(), view_id),
            )
            row = await self._fetchone(
                database,
                "SELECT * FROM technical_views WHERE id = ?",
                (view_id,),
            )
            await database.commit()
        if row is None:
            raise TechnicalViewNotFoundError(view_id)
        return self._technical_view_from_row(row)

    async def get_technical_view(
        self,
        *,
        project_id: str,
        design_version_id: str,
        role: TechnicalViewRole,
    ) -> TechnicalViewRecord:
        async with self._connect() as database:
            row = await self._fetchone(
                database,
                """
                SELECT * FROM technical_views
                WHERE project_id = ? AND design_version_id = ? AND role = ?
                """,
                (project_id, design_version_id, role),
            )
        if row is None:
            raise TechnicalViewNotFoundError(f"{design_version_id}:{role}")
        return self._technical_view_from_row(row)

    async def list_technical_views(
        self,
        project_id: str,
        *,
        design_version_id: str | None = None,
    ) -> list[TechnicalViewRecord]:
        query = "SELECT * FROM technical_views WHERE project_id = ?"
        params: tuple[Any, ...] = (project_id,)
        if design_version_id is not None:
            query += " AND design_version_id = ?"
            params = (project_id, design_version_id)
        query += " ORDER BY created_at ASC, role ASC"
        async with self._connect() as database:
            rows = await self._fetchall(database, query, params)
        return [self._technical_view_from_row(row) for row in rows]

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
    def _candidate_from_row(row: aiosqlite.Row) -> DesignCandidateRecord:
        return DesignCandidateRecord(
            id=row["id"],
            project_id=row["project_id"],
            generation_job_id=row["generation_job_id"],
            base_version_id=row["base_version_id"],
            candidate_index=row["candidate_index"],
            requested_change=row["requested_change"],
            preserve=json.loads(row["preserve_items"]),
            avoid=json.loads(row["avoid_items"]),
            prompt=row["prompt"],
            model=row["model"],
            status=row["status"],
            asset_id=row["asset_id"],
            selected_version_id=row["selected_version_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _generation_job_from_row(row: aiosqlite.Row) -> GenerationJobRecord:
        return GenerationJobRecord(
            id=row["id"],
            project_id=row["project_id"],
            base_version_id=row["base_version_id"],
            requested_change=row["requested_change"],
            model=row["model"],
            status=row["status"],
            output_asset_id=row["output_asset_id"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
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

    @staticmethod
    def _technical_view_from_row(row: aiosqlite.Row) -> TechnicalViewRecord:
        return TechnicalViewRecord(
            id=row["id"],
            project_id=row["project_id"],
            design_version_id=row["design_version_id"],
            role=row["role"],
            prompt=row["prompt"],
            model=row["model"],
            status=row["status"],
            output_asset_id=row["output_asset_id"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

import aiosqlite
from chatkit.store import NotFoundError, Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from pydantic import TypeAdapter

Context = dict[str, Any]
RowT = TypeVar("RowT", ThreadMetadata, ThreadItem)

_THREAD_ADAPTER = TypeAdapter(ThreadMetadata)
_ITEM_ADAPTER = TypeAdapter(ThreadItem)
_ATTACHMENT_ADAPTER = TypeAdapter(Attachment)


class SQLiteChatStore(Store[Context]):
    """Persistent ChatKit thread store using JSON payloads in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    async def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("PRAGMA journal_mode=WAL")
            await database.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_items (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chat_items_thread_created
                    ON chat_items(thread_id, created_at, id);

                CREATE TABLE IF NOT EXISTS chat_attachments (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                """
            )
            await database.commit()

    async def load_thread(self, thread_id: str, context: Context) -> ThreadMetadata:
        del context
        row = await self._fetch_one(
            "SELECT data FROM chat_threads WHERE id = ?",
            (thread_id,),
        )
        if row is None:
            raise NotFoundError(f"Thread {thread_id} not found")
        return _THREAD_ADAPTER.validate_json(row["data"])

    async def save_thread(self, thread: ThreadMetadata, context: Context) -> None:
        del context
        await self._execute(
            """
            INSERT INTO chat_threads (id, created_at, data)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                created_at = excluded.created_at,
                data = excluded.data
            """,
            (thread.id, thread.created_at.isoformat(), self._serialize(thread)),
        )

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: Context,
    ) -> Page[ThreadMetadata]:
        del context
        rows = await self._fetch_all("SELECT data FROM chat_threads")
        threads = [_THREAD_ADAPTER.validate_json(row["data"]) for row in rows]
        return self._paginate(
            threads,
            after,
            limit,
            order,
            sort_key=lambda thread: (thread.created_at, thread.id),
        )

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: Context,
    ) -> Page[ThreadItem]:
        del context
        rows = await self._fetch_all(
            "SELECT data FROM chat_items WHERE thread_id = ?",
            (thread_id,),
        )
        items = [_ITEM_ADAPTER.validate_json(row["data"]) for row in rows]
        return self._paginate(
            items,
            after,
            limit,
            order,
            sort_key=lambda item: (item.created_at, item.id),
        )

    async def add_thread_item(
        self,
        thread_id: str,
        item: ThreadItem,
        context: Context,
    ) -> None:
        await self.save_item(thread_id, item, context)

    async def save_item(
        self,
        thread_id: str,
        item: ThreadItem,
        context: Context,
    ) -> None:
        del context
        await self._execute(
            """
            INSERT INTO chat_items (id, thread_id, created_at, data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                thread_id = excluded.thread_id,
                created_at = excluded.created_at,
                data = excluded.data
            """,
            (item.id, thread_id, item.created_at.isoformat(), self._serialize(item)),
        )

    async def load_item(
        self,
        thread_id: str,
        item_id: str,
        context: Context,
    ) -> ThreadItem:
        del context
        row = await self._fetch_one(
            "SELECT data FROM chat_items WHERE thread_id = ? AND id = ?",
            (thread_id, item_id),
        )
        if row is None:
            raise NotFoundError(f"Item {item_id} not found in thread {thread_id}")
        return _ITEM_ADAPTER.validate_json(row["data"])

    async def delete_thread(self, thread_id: str, context: Context) -> None:
        del context
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("DELETE FROM chat_items WHERE thread_id = ?", (thread_id,))
            await database.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
            await database.commit()

    async def delete_thread_item(
        self,
        thread_id: str,
        item_id: str,
        context: Context,
    ) -> None:
        del context
        await self._execute(
            "DELETE FROM chat_items WHERE thread_id = ? AND id = ?",
            (thread_id, item_id),
        )

    async def save_attachment(self, attachment: Attachment, context: Context) -> None:
        del context
        await self._execute(
            """
            INSERT INTO chat_attachments (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data = excluded.data
            """,
            (attachment.id, self._serialize(attachment)),
        )

    async def load_attachment(self, attachment_id: str, context: Context) -> Attachment:
        del context
        row = await self._fetch_one(
            "SELECT data FROM chat_attachments WHERE id = ?",
            (attachment_id,),
        )
        if row is None:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        return _ATTACHMENT_ADAPTER.validate_json(row["data"])

    async def delete_attachment(self, attachment_id: str, context: Context) -> None:
        del context
        await self._execute(
            "DELETE FROM chat_attachments WHERE id = ?",
            (attachment_id,),
        )

    @staticmethod
    def _serialize(value: Any) -> str:
        return value.model_dump_json(by_alias=True, exclude_none=False)

    @staticmethod
    def _paginate(
        rows: Sequence[RowT],
        after: str | None,
        limit: int,
        order: str,
        sort_key: Callable[[RowT], object],
    ) -> Page[RowT]:
        safe_limit = max(1, min(limit, 100))
        sorted_rows = sorted(rows, key=sort_key, reverse=order == "desc")
        start = 0
        if after:
            start = next(
                (index + 1 for index, row in enumerate(sorted_rows) if row.id == after),
                0,
            )
        data = list(sorted_rows[start : start + safe_limit])
        has_more = start + safe_limit < len(sorted_rows)
        next_after = data[-1].id if has_more and data else None
        return Page(data=data, has_more=has_more, after=next_after)

    async def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(query, params)
            await database.commit()

    async def _fetch_one(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> aiosqlite.Row | None:
        async with aiosqlite.connect(self.database_path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(query, params)
            return await cursor.fetchone()

    async def _fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.database_path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(query, params)
            return list(await cursor.fetchall())

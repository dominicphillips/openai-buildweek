from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from chatkit.types import (
    ActiveStatus,
    InferenceOptions,
    ThreadMetadata,
    UserMessageItem,
    UserMessageTextContent,
)

from somethings_on.chat_store import SQLiteChatStore


@pytest.mark.asyncio
async def test_chat_store_persists_and_paginates(tmp_path: Path) -> None:
    store = SQLiteChatStore(tmp_path / "chat.sqlite3")
    await store.initialize()
    context: dict = {}
    created_at = datetime.now(UTC)
    thread = ThreadMetadata(
        id="thr_test",
        title="A white T-shirt",
        created_at=created_at,
        status=ActiveStatus(),
    )
    await store.save_thread(thread, context)

    for index in range(3):
        item = UserMessageItem(
            id=f"msg_{index}",
            thread_id=thread.id,
            created_at=created_at + timedelta(seconds=index),
            content=[UserMessageTextContent(text=f"Message {index}")],
            attachments=[],
            inference_options=InferenceOptions(),
        )
        await store.add_thread_item(thread.id, item, context)

    loaded = await store.load_thread(thread.id, context)
    assert loaded.title == "A white T-shirt"

    first_page = await store.load_thread_items(
        thread.id,
        after=None,
        limit=2,
        order="asc",
        context=context,
    )
    assert [item.id for item in first_page.data] == ["msg_0", "msg_1"]
    assert first_page.has_more is True
    assert first_page.after == "msg_1"

    second_page = await store.load_thread_items(
        thread.id,
        after=first_page.after,
        limit=2,
        order="asc",
        context=context,
    )
    assert [item.id for item in second_page.data] == ["msg_2"]
    assert second_page.has_more is False

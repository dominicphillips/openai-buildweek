from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
from agents import Runner
from chatkit.types import (
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemRemovedEvent,
    ThreadMetadata,
)

from somethings_on.chat_server import DesignChatServer, _product_safe_agent_failure
from somethings_on.chat_store import SQLiteChatStore
from somethings_on.design_store import SQLiteDesignStore
from somethings_on.image_service import DesignImageService
from somethings_on.models import ProjectSeedInput


def make_status_error(
    error_type: type[openai.APIStatusError],
    *,
    status_code: int,
    code: str,
    secret: str = "raw-upstream-secret",
) -> openai.APIStatusError:
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
        headers={"authorization": f"Bearer {secret}"},
    )
    response = httpx.Response(
        status_code,
        request=request,
        headers={"x-request-id": "req_provider_123"},
    )
    return error_type(
        f"Upstream body contained {secret}",
        response=response,
        body={"code": code, "message": secret},
    )


@pytest.mark.parametrize(
    ("error", "expected_category", "expected_copy"),
    [
        (
            make_status_error(
                openai.AuthenticationError,
                status_code=401,
                code="invalid_api_key",
            ),
            "authentication",
            "connection is restored",
        ),
        (
            make_status_error(
                openai.PermissionDeniedError,
                status_code=403,
                code="model_not_found",
            ),
            "model_access",
            "connection is restored",
        ),
        (
            make_status_error(
                openai.RateLimitError,
                status_code=429,
                code="insufficient_quota",
            ),
            "quota",
            "Try again in a moment",
        ),
        (
            make_status_error(
                openai.RateLimitError,
                status_code=429,
                code="rate_limit_exceeded",
            ),
            "rate_limit",
            "Try again in a moment",
        ),
        (
            openai.APITimeoutError(httpx.Request("POST", "https://api.openai.com/v1/responses")),
            "provider_connection",
            "Try again in a moment",
        ),
        (
            make_status_error(
                openai.InternalServerError,
                status_code=503,
                code="server_error",
            ),
            "provider_unavailable",
            "Try again in a moment",
        ),
        (
            make_status_error(
                openai.BadRequestError,
                status_code=400,
                code="invalid_request_error",
            ),
            "request_configuration",
            "Try again in a moment",
        ),
    ],
)
def test_product_safe_failure_copy_never_exposes_upstream_details(
    error: openai.OpenAIError,
    expected_category: str,
    expected_copy: str,
) -> None:
    category, message = _product_safe_agent_failure(error)

    assert category == expected_category
    assert expected_copy in message
    assert "current version has not changed" in message
    assert "raw-upstream-secret" not in message
    assert str(error) not in message


class FailingRunResult:
    def __init__(self, error: openai.OpenAIError) -> None:
        self.error = error

    async def stream_events(self) -> AsyncIterator[object]:
        yield SimpleNamespace(
            type="raw_response_event",
            data=SimpleNamespace(
                type="response.output_item.added",
                item=SimpleNamespace(
                    type="message",
                    id="msg_partial",
                    content=[],
                ),
            ),
        )
        raise self.error


@pytest.mark.asyncio
async def test_stream_failure_replaces_partial_item_with_persisted_safe_assistant_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "studio.sqlite3"
    chat_store = SQLiteChatStore(database_path)
    design_store = SQLiteDesignStore(database_path)
    await chat_store.initialize()
    await design_store.initialize()
    await design_store.upsert_project(
        "look_001",
        ProjectSeedInput(object_name="distressed bomber"),
    )
    image_service = DesignImageService(
        store=design_store,
        asset_root=tmp_path / "assets",
        provider=None,
        image_model="gpt-image-2",
    )
    await image_service.initialize()
    server = DesignChatServer(
        chat_store=chat_store,
        design_store=design_store,
        image_service=image_service,
        agent_model="gpt-5.6",
        agent_ready=True,
    )
    thread = ThreadMetadata(id="thread_001", created_at=datetime.now(UTC))
    context = {
        "project_id": "look_001",
        "request_id": "request_001",
        "base_version_id": None,
    }
    await chat_store.save_thread(thread, context)
    error = make_status_error(
        openai.RateLimitError,
        status_code=429,
        code="insufficient_quota",
    )
    monkeypatch.setattr(
        Runner,
        "run_streamed",
        lambda *args, **kwargs: FailingRunResult(error),
    )

    async def response_stream():
        async for event in server.respond(thread, None, context):
            yield event

    events = [
        event
        async for event in server._process_events(
            thread,
            context,
            response_stream,
        )
    ]

    assert any(
        isinstance(event, ThreadItemAddedEvent) and event.item.id == "msg_partial"
        for event in events
    )
    assert any(
        isinstance(event, ThreadItemRemovedEvent) and event.item_id == "msg_partial"
        for event in events
    )
    completed = [event for event in events if isinstance(event, ThreadItemDoneEvent)]
    assert len(completed) == 1
    assert isinstance(completed[0].item, AssistantMessageItem)
    assistant_text = completed[0].item.content[0].text
    assert "studio is paused" in assistant_text
    assert "current version has not changed" in assistant_text
    assert "raw-upstream-secret" not in assistant_text
    assert all(event.type != "error" for event in events)

    stored = await chat_store.load_thread_items(
        thread.id,
        after=None,
        limit=20,
        order="asc",
        context=context,
    )
    assert [item.id for item in stored.data] == [completed[0].item.id]
    assert isinstance(stored.data[0], AssistantMessageItem)
    assert stored.data[0].content[0].text == assistant_text

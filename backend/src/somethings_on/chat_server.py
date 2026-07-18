from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import openai
from agents import Runner
from agents.models.interface import Model
from agents.result import RunResultStreaming
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemRemovedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)

from .chat_store import SQLiteChatStore
from .design_agent import build_design_agent
from .design_store import SQLiteDesignStore
from .image_service import DesignImageService

MAX_RECENT_ITEMS = 40
RequestContext = dict[str, Any]
logger = logging.getLogger(__name__)

_QUOTA_ERROR_CODES = frozenset(
    {
        "billing_hard_limit_reached",
        "billing_not_active",
        "credits_exhausted",
        "insufficient_quota",
        "quota_exceeded",
        "usage_limit_reached",
    }
)

_AUTH_FAILURE_MESSAGE = (
    "The studio is not connected right now. Your current version has not changed. Try again "
    "after the connection is restored."
)
_ACCESS_FAILURE_MESSAGE = (
    "The studio is not connected right now. Your current version has not changed. Try again "
    "after the connection is restored."
)
_QUOTA_FAILURE_MESSAGE = (
    "The studio is paused right now. Your current version has not changed. Try again in a moment."
)
_RATE_LIMIT_FAILURE_MESSAGE = (
    "The studio is busy right now. Your current version has not changed. Try again in a moment."
)
_PROVIDER_FAILURE_MESSAGE = (
    "That change did not finish. Your current version has not changed. Try again in a moment."
)
_REQUEST_FAILURE_MESSAGE = (
    "That change did not finish. Your current version has not changed. Try again in a moment."
)


class _ProductSafeAgentStream:
    """Let ChatKit finish its stream normally while retaining a provider exception server-side."""

    def __init__(self, result: RunResultStreaming) -> None:
        self.result = result
        self.failure: openai.OpenAIError | None = None

    async def stream_events(self) -> AsyncIterator[Any]:
        try:
            async for event in self.result.stream_events():
                yield event
        except openai.OpenAIError as error:
            self.failure = error


def _product_safe_agent_failure(error: openai.OpenAIError) -> tuple[str, str]:
    """Classify from typed metadata only; never place the upstream message/body in UI copy."""

    markers = {
        marker.lower()
        for marker in (getattr(error, "code", None), getattr(error, "type", None))
        if isinstance(marker, str)
    }
    status_code = getattr(error, "status_code", None)

    if isinstance(error, openai.AuthenticationError) or status_code == 401:
        return "authentication", _AUTH_FAILURE_MESSAGE
    if isinstance(error, openai.PermissionDeniedError | openai.NotFoundError) or status_code in {
        403,
        404,
    }:
        return "model_access", _ACCESS_FAILURE_MESSAGE
    if isinstance(error, openai.RateLimitError) or status_code == 429:
        if markers & _QUOTA_ERROR_CODES:
            return "quota", _QUOTA_FAILURE_MESSAGE
        return "rate_limit", _RATE_LIMIT_FAILURE_MESSAGE
    if isinstance(error, openai.APITimeoutError | openai.APIConnectionError):
        return "provider_connection", _PROVIDER_FAILURE_MESSAGE
    if isinstance(error, openai.APIStatusError):
        if error.status_code >= 500:
            return "provider_unavailable", _PROVIDER_FAILURE_MESSAGE
        return "request_configuration", _REQUEST_FAILURE_MESSAGE
    return "provider_error", _PROVIDER_FAILURE_MESSAGE


class DesignChatServer(ChatKitServer[RequestContext]):
    def __init__(
        self,
        *,
        chat_store: SQLiteChatStore,
        design_store: SQLiteDesignStore,
        image_service: DesignImageService,
        agent_model: str | Model,
        agent_ready: bool,
    ) -> None:
        super().__init__(chat_store)
        self.design_store = design_store
        self.image_service = image_service
        self.agent_model = agent_model
        self.agent_ready = agent_ready

    def _assistant_message_event(
        self,
        *,
        thread: ThreadMetadata,
        context: RequestContext,
        text: str,
    ) -> ThreadItemDoneEvent:
        return ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=thread.id,
                id=self.store.generate_item_id("message", thread, context),
                created_at=datetime.now(UTC),
                content=[AssistantMessageContent(text=text)],
            )
        )

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        del input_user_message
        if not self.agent_ready:
            yield self._assistant_message_event(
                thread=thread,
                context=context,
                text=(
                    "The studio is not connected yet. Your canvas and current version are still "
                    "here."
                ),
            )
            return

        project_id = str(context["project_id"])
        project = await self.design_store.ensure_project(project_id)
        base_version_id = context.get("base_version_id")
        selected_version = project.current_version
        if isinstance(base_version_id, str):
            selected_version = await self.design_store.get_design_version(
                project_id,
                base_version_id,
            )
        items_page = await self.store.load_thread_items(
            thread.id,
            after=None,
            limit=MAX_RECENT_ITEMS,
            order="desc",
            context=context,
        )
        agent_input = await simple_to_agent_input(list(reversed(items_page.data)))
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context={
                **context,
                "image_service": self.image_service,
            },
        )
        agent = build_design_agent(
            project,
            model=self.agent_model,
            selected_version=selected_version,
        )
        pending_item_ids: dict[str, None] = {}
        stream_failure: openai.OpenAIError | None = None
        try:
            result = Runner.run_streamed(agent, agent_input, context=agent_context)
            safe_result = _ProductSafeAgentStream(result)
            async for event in stream_agent_response(agent_context, safe_result):
                if isinstance(event, ThreadItemAddedEvent):
                    pending_item_ids[event.item.id] = None
                elif isinstance(event, ThreadItemDoneEvent):
                    pending_item_ids.pop(event.item.id, None)
                elif isinstance(event, ThreadItemRemovedEvent):
                    pending_item_ids.pop(event.item_id, None)
                yield event
            stream_failure = safe_result.failure
        except openai.OpenAIError as error:
            # The normal Agents SDK path is captured by _ProductSafeAgentStream so ChatKit can
            # drain its queues. This boundary also covers a synchronous provider failure.
            stream_failure = error

        if stream_failure is None:
            return

        category, message = _product_safe_agent_failure(stream_failure)
        logger.error(
            "OpenAI agent stream failed category=%s exception=%s status=%s request_id=%s",
            category,
            type(stream_failure).__name__,
            getattr(stream_failure, "status_code", None),
            getattr(stream_failure, "request_id", None),
        )
        for item_id in pending_item_ids:
            yield ThreadItemRemovedEvent(item_id=item_id)
        yield self._assistant_message_event(
            thread=thread,
            context=context,
            text=message,
        )

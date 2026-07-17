from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from agents import Runner
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadItemDoneEvent,
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


class DesignChatServer(ChatKitServer[RequestContext]):
    def __init__(
        self,
        *,
        chat_store: SQLiteChatStore,
        design_store: SQLiteDesignStore,
        image_service: DesignImageService,
        agent_model: str,
        agent_ready: bool,
    ) -> None:
        super().__init__(chat_store)
        self.design_store = design_store
        self.image_service = image_service
        self.agent_model = agent_model
        self.agent_ready = agent_ready

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        del input_user_message
        if not self.agent_ready:
            yield ThreadItemDoneEvent(
                item=AssistantMessageItem(
                    thread_id=thread.id,
                    id=self.store.generate_item_id("message", thread, context),
                    created_at=datetime.now(UTC),
                    content=[
                        AssistantMessageContent(
                            text=(
                                "The studio guide is offline until OPENAI_API_KEY is configured. "
                                "Your canvas and project state are still available locally."
                            )
                        )
                    ],
                )
            )
            return

        project_id = str(context["project_id"])
        project = await self.design_store.ensure_project(project_id)
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
        agent = build_design_agent(project, model=self.agent_model)
        result = Runner.run_streamed(agent, agent_input, context=agent_context)
        async for event in stream_agent_response(agent_context, result):
            yield event

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from agents.tool_context import ToolContext

from somethings_on.design_agent import create_design_revision


class RecordingRevisionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create_revision(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="ver_222222222222",
            version_number=4,
            asset_url="/api/assets/ast_222222222222",
            requested_change=kwargs["requested_change"],
            preserve=kwargs["preserve"] or [],
        )


class RecordingAgentContext:
    def __init__(self, service: RecordingRevisionService) -> None:
        self.request_context = {
            "image_service": service,
            "project_id": "look_001",
            "base_version_id": "ver_111111111111",
        }
        self.events: list[object] = []

    async def stream(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_revision_tool_uses_authoritative_base_from_request_context() -> None:
    service = RecordingRevisionService()
    agent_context = RecordingAgentContext(service)
    tool_context = ToolContext(
        context=agent_context,
        tool_name="create_design_revision",
        tool_call_id="call_001",
        tool_arguments="{}",
    )

    result = await create_design_revision.on_invoke_tool(
        tool_context,
        json.dumps(
            {
                "requested_change": "Add only a restrained rib texture",
                "preserve": ["washed charcoal color"],
                "avoid": None,
            }
        ),
    )

    assert service.calls == [
        {
            "project_id": "look_001",
            "requested_change": "Add only a restrained rib texture",
            "preserve": ["washed charcoal color"],
            "avoid": None,
            "base_version_id": "ver_111111111111",
        }
    ]
    assert json.loads(result)["version_id"] == "ver_222222222222"
    assert len(agent_context.events) == 2

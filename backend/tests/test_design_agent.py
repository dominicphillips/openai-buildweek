from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from agents.tool_context import ToolContext
from chatkit.types import ClientEffectEvent, ProgressUpdateEvent

from somethings_on.design_agent import create_design_revision


class RecordingCandidateService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create_candidates(self, **kwargs: object) -> list[SimpleNamespace]:
        self.calls.append(kwargs)
        return [
            SimpleNamespace(
                id=f"cand_{index:012x}",
                generation_job_id="job_222222222222",
            )
            for index in range(1, 5)
        ]


class RecordingAgentContext:
    def __init__(self, service: RecordingCandidateService) -> None:
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
    service = RecordingCandidateService()
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
            "count": 4,
        }
    ]
    assert json.loads(result) == {
        "status": "awaiting_selection",
        "candidate_set_id": "job_222222222222",
        "candidate_count": 4,
        "requested_change": "Add only a restrained rib texture",
        "message": (
            "Four options are ready. The designer must choose one to create the next version."
        ),
    }
    assert len(agent_context.events) == 2
    progress = agent_context.events[0]
    assert isinstance(progress, ProgressUpdateEvent)
    assert progress.text == "Working on four options…"
    assert progress.icon is None
    effect = agent_context.events[1]
    assert isinstance(effect, ClientEffectEvent)
    assert effect.name == "design.candidates.created"
    assert effect.data == {
        "project_id": "look_001",
        "job_id": "job_222222222222",
        "count": 4,
    }

from __future__ import annotations

import json
from typing import Any, cast

from agents import Agent, RunContextWrapper, function_tool
from chatkit.agents import AgentContext
from chatkit.types import ClientEffectEvent, ProgressUpdateEvent

from .image_service import DesignImageService, ImageGenerationUnavailable, InvalidImageError
from .models import ProjectSnapshot

AgentRequestContext = dict[str, Any]


@function_tool
async def create_design_revision(
    run_context: RunContextWrapper[AgentContext[AgentRequestContext]],
    requested_change: str,
    preserve: list[str] | None = None,
    avoid: list[str] | None = None,
) -> str:
    """Create one new immutable visual version after the designer confirms a concrete change.

    Args:
        requested_change: One specific, visible change to make to the current object.
        preserve: Existing qualities that must remain unchanged.
        avoid: Explicitly unwanted details or directions.
    """

    agent_context = run_context.context
    request_context = agent_context.request_context
    service = cast(DesignImageService, request_context["image_service"])
    project_id = cast(str, request_context["project_id"])

    await agent_context.stream(
        ProgressUpdateEvent(icon="sparkle", text="Rendering one authored change…")
    )
    try:
        version = await service.create_revision(
            project_id=project_id,
            requested_change=requested_change,
            preserve=preserve,
            avoid=avoid,
        )
    except (ImageGenerationUnavailable, InvalidImageError, ValueError) as error:
        return f"The visual revision was not created: {error}"

    await agent_context.stream(
        ClientEffectEvent(
            name="design.version.created",
            data={
                "project_id": project_id,
                "version_id": version.id,
                "version_number": version.version_number,
                "asset_url": version.asset_url,
            },
        )
    )
    return json.dumps(
        {
            "status": "created",
            "version_id": version.id,
            "version_number": version.version_number,
            "asset_url": version.asset_url,
            "requested_change": version.requested_change,
            "preserved": version.preserve,
        }
    )


def build_design_agent(
    project: ProjectSnapshot,
    *,
    model: str,
) -> Agent[AgentContext[AgentRequestContext]]:
    taste_traits = sorted({tag for signal in project.taste_signals for tag in signal.tags})
    current = project.current_version
    project_state = {
        "object": project.object_name,
        "taste_traits": taste_traits,
        "reference_count": len(project.references) + len(project.link_references),
        "current_version": current.version_number if current else 1,
        "last_change": current.requested_change if current else "Base study",
    }

    return Agent[AgentContext[AgentRequestContext]](
        name="SOMETHINGS-ON Design Guide",
        model=model,
        instructions=(
            "You are the calm, exacting design guide inside SOMETHINGS-ON, a studio for emerging "
            "fashion designers. Treat the designer as the creative director. Ask at most one "
            "useful "
            "question at a time, keep most replies under 90 words, and use concrete language about "
            "proportion, material, construction, finish, wear, and context.\n\n"
            "References are evidence, not templates. Translate them into abstract traits and never "
            "imitate a named brand or designer, reproduce a logo, signature graphic, trade dress, "
            "or an identifiable existing garment. Do not claim endorsement. The 'small change' "
            "idea is a "
            "creative constraint, not a copyright rule. Keep changes visible, intentional, and "
            "attributable to this designer.\n\n"
            "Before calling create_design_revision, identify what must stay and obtain clear "
            "confirmation of one visible change. Never call it merely because the user is "
            "exploring. After a successful tool call, summarize what changed and what was "
            "preserved. If the tool "
            "cannot run, say so plainly and continue the design conversation without pretending an "
            "image exists.\n\n"
            f"Current project state:\n{json.dumps(project_state, indent=2)}"
        ),
        tools=[create_design_revision],
    )

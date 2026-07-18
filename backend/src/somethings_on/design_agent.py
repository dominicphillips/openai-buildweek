from __future__ import annotations

import json
from typing import Any, cast

from agents import Agent, RunContextWrapper, function_tool
from agents.models.interface import Model
from chatkit.agents import AgentContext
from chatkit.types import ClientEffectEvent, ProgressUpdateEvent

from .design_store import CandidateSetInProgressError, DesignVersionNotFoundError
from .image_service import (
    DesignImageService,
    ImageGenerationUnavailable,
    InvalidImageError,
    RevisionBaseAssetRequired,
)
from .models import DesignVersionRecord, ProjectSnapshot

AgentRequestContext = dict[str, Any]


@function_tool
async def create_design_revision(
    run_context: RunContextWrapper[AgentContext[AgentRequestContext]],
    requested_change: str,
    preserve: list[str] | None = None,
    avoid: list[str] | None = None,
) -> str:
    """Create four visual options after the designer confirms one concrete change.

    Args:
        requested_change: One specific, visible change to make to the current object.
        preserve: Existing qualities that must remain unchanged.
        avoid: Explicitly unwanted details or directions.
    """

    agent_context = run_context.context
    request_context = agent_context.request_context
    service = cast(DesignImageService, request_context["image_service"])
    project_id = cast(str, request_context["project_id"])
    base_version_id = cast(str | None, request_context.get("base_version_id"))

    await agent_context.stream(ProgressUpdateEvent(text="Working on four options…"))
    try:
        candidates = await service.create_candidates(
            project_id=project_id,
            requested_change=requested_change,
            preserve=preserve,
            avoid=avoid,
            base_version_id=base_version_id,
            count=4,
        )
    except DesignVersionNotFoundError:
        return (
            "The visual revision was not created: the selected design version is no longer "
            "available. Choose another version and try again."
        )
    except RevisionBaseAssetRequired as error:
        return f"The visual revision was not created: {error}"
    except CandidateSetInProgressError as error:
        return f"The visual options were not created: {error}"
    except (ImageGenerationUnavailable, InvalidImageError, ValueError) as error:
        return f"The visual options were not created: {error}"

    candidate_set_id = candidates[0].generation_job_id

    await agent_context.stream(
        ClientEffectEvent(
            name="design.candidates.created",
            data={
                "project_id": project_id,
                "job_id": candidate_set_id,
                "count": len(candidates),
            },
        )
    )
    return json.dumps(
        {
            "status": "awaiting_selection",
            "candidate_set_id": candidate_set_id,
            "candidate_count": len(candidates),
            "requested_change": requested_change,
            "message": (
                "Four options are ready. The designer must choose one to create the next version."
            ),
        }
    )


def build_design_agent(
    project: ProjectSnapshot,
    *,
    model: str | Model,
    selected_version: DesignVersionRecord | None = None,
) -> Agent[AgentContext[AgentRequestContext]]:
    taste_traits = sorted({tag for signal in project.taste_signals for tag in signal.tags})
    latest = project.current_version
    selected = selected_version or latest
    project_state = {
        "object": project.object_name,
        "taste_traits": taste_traits,
        "reference_count": len(project.references) + len(project.link_references),
        "latest_version_id": latest.id if latest else None,
        "latest_version_number": latest.version_number if latest else None,
        "selected_version_id": selected.id if selected else None,
        "selected_version_number": selected.version_number if selected else None,
        "selected_version_is_latest": bool(selected and latest and selected.id == latest.id),
        "selected_version_has_raster": bool(selected and selected.asset_id),
        "selected_last_change": selected.requested_change if selected else "Base study",
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
            "exploring. The tool creates four candidates, not a new version. After a successful "
            "tool call, tell the designer to compare and choose one option in the studio. Do not "
            "claim that a version exists before that selection. If the tool "
            "cannot run, say so plainly and continue the design conversation without pretending an "
            "image exists.\n\n"
            "The browser's selected design version is authoritative for this turn. The revision "
            "tool is bound to that immutable version in local request context; never substitute "
            "the latest version or ask the tool to choose a different parent. If the selected "
            "version is older than the latest version, a successful revision deliberately creates "
            "a branch while preserving every existing version.\n\n"
            f"Current project state:\n{json.dumps(project_state, indent=2)}"
        ),
        tools=[create_design_revision],
    )

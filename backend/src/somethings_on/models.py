from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class TasteSignal(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return [tag.strip()[:80] for tag in tags if tag.strip()]


class ProjectSeedInput(BaseModel):
    object_name: str = Field(default="T-shirt", min_length=1, max_length=160)
    taste_signals: list[TasteSignal] = Field(default_factory=list, max_length=5)


RevisionInstruction = Annotated[str, Field(min_length=1, max_length=120)]


class DesignRevisionCreateInput(BaseModel):
    """One explicit raster generation or exact-image edit request."""

    model_config = ConfigDict(extra="forbid")

    requested_change: str = Field(min_length=1, max_length=800)
    preserve: list[RevisionInstruction] = Field(default_factory=list, max_length=8)
    avoid: list[RevisionInstruction] = Field(default_factory=list, max_length=8)
    base_version_id: str | None = Field(
        default=None,
        pattern=r"^ver_[a-f0-9]{12}$",
    )

    @field_validator("requested_change")
    @classmethod
    def normalize_requested_change(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Describe one concrete design change.")
        return value

    @field_validator("preserve", "avoid")
    @classmethod
    def normalize_instructions(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Revision instructions cannot be blank.")
        return normalized


class LinkReferenceInput(BaseModel):
    url: HttpUrl
    label: str | None = Field(default=None, max_length=160)


class AssetRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    kind: Literal["reference", "generated"]
    mime_type: str
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    source_url: str | None = None
    original_name: str | None = None
    created_at: datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"/api/assets/{self.id}"


class LinkReferenceRecord(BaseModel):
    id: str
    project_id: str
    url: str
    label: str
    created_at: datetime


class CastingControls(BaseModel):
    """Independent, closed-vocabulary controls for one fictional adult casting."""

    model_config = ConfigDict(extra="forbid")

    body_build: Literal["varied", "lean", "straight", "soft", "muscular", "broad", "full"] = (
        "varied"
    )
    stature: Literal["varied", "short", "medium", "tall"] = "varied"
    skin_tone: Literal[
        "varied",
        "deep",
        "medium-deep",
        "medium",
        "light-medium",
        "light",
        "very-light",
    ] = "varied"
    presentation: Literal["varied", "feminine", "masculine", "androgynous", "mixed-cues"] = "varied"
    adult_age: Literal["varied-adult", "25-39", "40-59", "60-plus"] = "varied-adult"
    pose_access: Literal["varied", "standing", "seated", "mobility-aid-aware"] = "varied"
    continuity: Literal["new-fictional-casting", "keep-generated-character"] = (
        "new-fictional-casting"
    )


class PresentationCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    design_version_id: str | None = Field(
        default=None,
        pattern=r"^ver_[a-f0-9]{12}$",
    )
    controls: CastingControls = Field(default_factory=CastingControls)


class CastingVariationGuidance(BaseModel):
    body: str
    skin: str
    presentation: str
    age: str
    pose_access: str


class CastingPresetRecord(BaseModel):
    id: str
    display_name: str
    one_line_mood: str
    wardrobe_context: str
    pose: str
    setting: str
    lighting: str
    casting_variation_guidance: CastingVariationGuidance
    prompt_fragment: str
    avoid_list: list[str]


class CastingSubjectPolicy(BaseModel):
    adults_only: bool
    minimum_apparent_age: int = Field(ge=25)
    fictional_people_only: bool
    real_person_references_allowed: bool
    preserve_garment_design: bool
    presentation_is_separate_asset: bool
    global_prompt_rules: list[str]


class CastingPresetCollection(BaseModel):
    schema_version: int
    collection_id: str
    collection_name: str
    subject_policy: CastingSubjectPolicy
    variation_controls: dict[str, str | list[str]]
    ux_copy: dict[str, str]
    presets: list[CastingPresetRecord]


class DesignVersionRecord(BaseModel):
    id: str
    project_id: str
    version_number: int
    parent_version_id: str | None = None
    asset_id: str | None = None
    generation_job_id: str | None = None
    requested_change: str
    preserve: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    prompt: str
    status: Literal["concept", "ready"]
    created_at: datetime

    @computed_field
    @property
    def asset_url(self) -> str | None:
        return f"/api/assets/{self.asset_id}" if self.asset_id else None


class PresentationRenderRecord(BaseModel):
    id: str
    project_id: str
    design_version_id: str
    preset_id: str
    controls: CastingControls
    prompt: str
    avoid: list[str]
    model: str
    status: Literal["queued", "running", "ready", "failed", "rejected"]
    output_asset_id: str | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def asset_url(self) -> str | None:
        return f"/api/assets/{self.output_asset_id}" if self.output_asset_id else None


class ProjectSnapshot(BaseModel):
    id: str
    object_name: str
    taste_signals: list[TasteSignal]
    references: list[AssetRecord]
    link_references: list[LinkReferenceRecord]
    versions: list[DesignVersionRecord]
    presentations: list[PresentationRenderRecord] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def current_version(self) -> DesignVersionRecord | None:
        return self.versions[-1] if self.versions else None


class GenerationJobRecord(BaseModel):
    id: str
    project_id: str
    base_version_id: str | None = None
    requested_change: str
    model: str
    status: Literal["queued", "running", "succeeded", "failed"]
    output_asset_id: str | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "SOMETHINGS-ON"
    chatkit_ready: bool
    chatkit_domain_key: str | None = None
    agent_model: str
    image_model: str

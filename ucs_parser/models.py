"""
Data models for Universal Cognitive Schema v0.1.0.
These mirror the JSON Schema definition in schema/ucs.schema.json.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExtractionMethod(str, Enum):
    api        = "api"
    export     = "export"
    manual     = "manual"
    synthesised = "synthesised"


class ExpertiseDepth(str, Enum):
    aware      = "aware"
    functional = "functional"
    proficient = "proficient"
    expert     = "expert"


class OutputFormat(str, Enum):
    prose      = "prose"
    bullets    = "bullets"
    structured = "structured"
    mixed      = "mixed"


class ResponseLength(str, Enum):
    concise  = "concise"
    moderate = "moderate"
    thorough = "thorough"


class CitationStyle(str, Enum):
    inline   = "inline"
    footnote = "footnote"
    none     = "none"


class AutonomyTolerance(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


class ConfirmationFrequency(str, Enum):
    always    = "always"
    sometimes = "sometimes"
    rarely    = "rarely"


class ProjectStatus(str, Enum):
    active    = "active"
    paused    = "paused"
    completed = "completed"
    abandoned = "abandoned"


class PromptStructure(str, Enum):
    single_line     = "single-line"
    multi_paragraph = "multi-paragraph"
    bulleted        = "bulleted"
    mixed           = "mixed"


class PromptLength(str, Enum):
    short  = "short"
    medium = "medium"
    long   = "long"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class CommunicationStyle(BaseModel):
    """Weighted blend of communication modes. Values 0.0–1.0."""
    direct:        float = Field(default=0.0, ge=0.0, le=1.0)
    collaborative: float = Field(default=0.0, ge=0.0, le=1.0)
    socratic:      float = Field(default=0.0, ge=0.0, le=1.0)
    narrative:     float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def at_least_one_nonzero(self) -> CommunicationStyle:
        total = self.direct + self.collaborative + self.socratic + self.narrative
        if total == 0.0:
            raise ValueError("At least one communication_style dimension must be non-zero.")
        return self


class LanguagePreferences(BaseModel):
    primary: str = Field(..., pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    others:  list[str] = Field(default_factory=list)


class Persona(BaseModel):
    updated_at:            Optional[datetime]          = None
    communication_style:   CommunicationStyle          = Field(default_factory=lambda: CommunicationStyle(direct=1.0))
    formality:             Optional[float]             = Field(default=None, ge=0.0, le=1.0)
    verbosity:             Optional[float]             = Field(default=None, ge=0.0, le=1.0)
    tone_markers:          list[str]                   = Field(default_factory=list)
    language_preferences:  Optional[LanguagePreferences] = None


class ExpertiseDomain(BaseModel):
    name:        str
    depth:       ExpertiseDepth
    last_active: Optional[datetime] = None
    notes:       Optional[str]      = None


class ExpertiseMap(BaseModel):
    updated_at: Optional[datetime]       = None
    domains:    list[ExpertiseDomain]    = Field(default_factory=list)


class Project(BaseModel):
    id:              uuid.UUID
    name:            str
    description:     Optional[str]      = None
    context_summary: Optional[str]      = None
    status:          Optional[ProjectStatus] = None
    created_at:      datetime
    updated_at:      Optional[datetime] = None
    archived_at:     Optional[datetime] = None
    tags:            list[str]          = Field(default_factory=list)


class ProjectGraph(BaseModel):
    updated_at: Optional[datetime] = None
    active:     list[Project]      = Field(default_factory=list)
    archived:   list[Project]      = Field(default_factory=list)


class PreferenceCorpus(BaseModel):
    updated_at:                 Optional[datetime]      = None
    output_format:              Optional[OutputFormat]  = None
    response_length:            Optional[ResponseLength] = None
    code_language_preferences:  list[str]               = Field(default_factory=list)
    citation_style:             Optional[CitationStyle] = None
    custom:                     dict[str, Any]          = Field(default_factory=dict)


class TypicalPromptStyle(BaseModel):
    opener:     Optional[str]            = None
    structure:  Optional[PromptStructure] = None
    avg_length: Optional[PromptLength]   = None


class InteractionPatterns(BaseModel):
    updated_at:             Optional[datetime]          = None
    typical_prompt_style:   Optional[TypicalPromptStyle] = None
    common_corrections:     list[str]                   = Field(default_factory=list)
    reinforced_behaviours:  list[str]                   = Field(default_factory=list)
    rejected_behaviours:    list[str]                   = Field(default_factory=list)


class TrustBoundaries(BaseModel):
    updated_at:                         Optional[datetime]              = None
    autonomous_action_tolerance:        Optional[AutonomyTolerance]    = None
    preferred_confirmation_frequency:   Optional[ConfirmationFrequency] = None
    sensitive_domains:                  list[str]                       = Field(default_factory=list)


class LifeChapter(BaseModel):
    label:  str
    from_:  datetime = Field(..., alias="from")
    to:     Optional[datetime] = None
    active: bool
    notes:  Optional[str] = None

    model_config = {"populate_by_name": True}


class TemporalContext(BaseModel):
    updated_at:     Optional[datetime]  = None
    recency_weight: Optional[float]     = Field(default=None, ge=0.0, le=1.0)
    life_chapters:  list[LifeChapter]   = Field(default_factory=list)


class Provenance(BaseModel):
    source_platforms:       list[str]
    extraction_method:      ExtractionMethod
    sanitised:              bool
    sanitised_at:           Optional[datetime] = None
    attestation_signature:  Optional[str]      = None

    @field_validator("source_platforms")
    @classmethod
    def at_least_one_platform(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("source_platforms must contain at least one entry.")
        return v


class FidelityScore(BaseModel):
    score:             float = Field(..., ge=0.0, le=1.0)
    note:              Optional[str] = None
    interaction_count: Optional[int] = Field(default=None, ge=0)


class FidelityReport(BaseModel):
    generated_at:        Optional[datetime]     = None
    overall:             Optional[FidelityScore] = None
    persona:             Optional[FidelityScore] = None
    expertise_map:       Optional[FidelityScore] = None
    project_graph:       Optional[FidelityScore] = None
    preference_corpus:   Optional[FidelityScore] = None
    interaction_patterns:Optional[FidelityScore] = None
    trust_boundaries:    Optional[FidelityScore] = None
    temporal_context:    Optional[FidelityScore] = None


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------

class UCSProfile(BaseModel):
    ucs_version:         str            = "0.1.0"
    profile_id:          uuid.UUID      = Field(default_factory=uuid.uuid4)
    created_at:          datetime       = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:          datetime       = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_url:          str            = "https://ucs-standard.org/schema/v0.1.0/ucs.schema.json"
    persona:             Persona        = Field(default_factory=Persona)
    expertise_map:       Optional[ExpertiseMap]        = None
    project_graph:       Optional[ProjectGraph]        = None
    preference_corpus:   Optional[PreferenceCorpus]    = None
    interaction_patterns:Optional[InteractionPatterns] = None
    trust_boundaries:    Optional[TrustBoundaries]     = None
    temporal_context:    Optional[TemporalContext]     = None
    extensions:          dict[str, Any]                = Field(default_factory=dict)
    provenance:          Optional[Provenance]          = None
    fidelity:            Optional[FidelityReport]      = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True, by_alias=True)

    def to_json(self, path: str, indent: int = 2) -> None:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=indent, default=str)

    @classmethod
    def from_json(cls, path: str) -> "UCSProfile":
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

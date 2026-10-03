from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from pch_core.schema.metadata import UniversalMetadata
from pch_core.timeutil import validate_interval


class MemoryKind(StrEnum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    SUMMARY = "summary"


class SensitivityFlag(StrEnum):
    FINANCIAL = "financial"
    HEALTH = "health"
    LEGAL = "legal"
    RELATIONSHIP = "relationship"


class Memory(UniversalMetadata):
    kind: MemoryKind = MemoryKind.SEMANTIC
    statement: str
    subject_ref: str | None = None
    project_id: str | None = None
    sensitivity_flags: list[SensitivityFlag] = Field(default_factory=list)
    tombstone: bool = False
    valid_from: str | None = None
    valid_until: str | None = None
    never_true: bool = False

    @model_validator(mode="after")
    def _interval_order(self) -> Memory:
        validate_interval(self.valid_from, self.valid_until)
        return self

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class TransitionKind(StrEnum):
    UPDATE = "update"
    SUPERSESSION = "supersession"
    CONFIDENCE_CHANGE = "confidence_change"
    CONDITIONAL_EXCEPTION = "conditional_exception"


class StateTransition(UniversalMetadata):
    subject_id: str
    subject_type: str
    kind: TransitionKind
    previous_value: Any = None
    new_value: Any = None
    valid_from: str | None = None
    valid_until: str | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None
    experience_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str
    recorded_at: str

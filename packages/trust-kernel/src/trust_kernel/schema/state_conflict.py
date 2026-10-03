from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class ConflictResolution(StrEnum):
    AUTOMATED = "automated"
    POLICY_BASED = "policy_based"
    USER_CONFIRMED = "user_confirmed"
    UNRESOLVED = "unresolved"


class StateConflictStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class StateConflict(UniversalMetadata):
    subject: str
    claim_ids: list[str] = Field(min_length=2)
    evidence_ids: list[str] = Field(default_factory=list)
    temporal_scope: dict[str, str | None] = Field(default_factory=dict)
    resolution: ConflictResolution
    status: StateConflictStatus
    detail: str

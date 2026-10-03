from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EntityType(StrEnum):
    PERSON = "person"
    SPACE = "space"
    PROFILE = "profile"
    PREFERENCE = "preference"
    PROJECT = "project"
    GOAL = "goal"
    COMMITMENT = "commitment"
    DECISION = "decision"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    SHARED_STATE = "shared_state"
    CONNECTION = "connection"
    GRANT = "grant"
    MANIFEST = "manifest"
    PROPOSAL = "proposal"
    CONFLICT = "conflict"
    ACTION_INTENT = "action_intent"
    APPROVAL = "approval"
    AUDIT_EVENT = "audit_event"
    EXPORT = "export"
    IMPORT_STAGING = "import_staging"
    VENDOR_IMPORT_BATCH = "vendor_import_batch"
    EVENT = "event"
    OPERATIONAL_PROPOSAL = "operational_proposal"
    RELATION = "relation"
    RELATION_PROPOSAL = "relation_proposal"
    EXPERIENCE = "experience"
    EVIDENCE = "evidence"
    STATE_TRANSITION = "state_transition"
    STATE_CONFLICT = "state_conflict"


class Classification(StrEnum):
    PUBLIC = "public"
    PERSONAL = "personal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"


class Authority(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    SOURCE_IMPORTED = "source_imported"
    AGENT_INFERRED = "agent_inferred"
    PROPOSED = "proposed"


class RetentionMode(StrEnum):
    UNTIL_REVOKED = "until_revoked"
    REVIEW_AFTER = "review_after"
    EXPIRES = "expires"


class Retention(BaseModel):
    mode: RetentionMode = RetentionMode.UNTIL_REVOKED
    at: str | None = None


class UniversalMetadata(BaseModel):
    id: str
    space_id: str = "personal"
    type: EntityType
    labels: list[str] = Field(default_factory=list)
    classification: Classification = Classification.PERSONAL
    owner: str
    created_at: str
    updated_at: str
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    authority: Authority = Authority.USER_CONFIRMED
    retention: Retention = Field(default_factory=Retention)
    policy_tags: list[str] = Field(default_factory=list)
    version: int = 1

    @model_validator(mode="after")
    def _inferred_needs_confidence(self) -> UniversalMetadata:
        if self.authority == Authority.AGENT_INFERRED and self.confidence is None:
            raise ValueError("confidence required when authority is agent_inferred")
        return self


def metadata_dict(meta: UniversalMetadata) -> dict[str, Any]:
    return meta.model_dump(mode="json")

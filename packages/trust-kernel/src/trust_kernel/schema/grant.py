from enum import StrEnum

from pydantic import BaseModel, Field


class Capability(StrEnum):
    PROJECT_READ = "project.read"
    COMMITMENT_READ = "commitment.read"
    MEMORY_RETRIEVE = "memory.retrieve"
    MEMORY_PROPOSE = "memory.propose"
    STATE_WRITE = "state.write"
    STATE_SHARE = "state.share"
    ACTION_PROPOSE = "action.propose"
    PROFILE_READ = "profile.read"


class GrantStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Grant(BaseModel):
    id: str
    space_id: str = "personal"
    connection_id: str
    capabilities: list[Capability] = Field(default_factory=list)
    selectors: dict[str, str] = Field(default_factory=dict)
    classification_ceiling: str = "private"
    purpose_constraint: str | None = None
    expires_at: str | None = None
    status: GrantStatus = GrantStatus.ACTIVE
    preset: str | None = None
    summary_human: str = ""


PRESETS: dict[str, dict] = {
    "read_active_projects": {
        "capabilities": [
            Capability.PROJECT_READ,
            Capability.COMMITMENT_READ,
            Capability.MEMORY_RETRIEVE,
        ],
        "summary_human": "Can read my active projects",
    },
    "always_ask_before_sending": {
        "capabilities": [Capability.ACTION_PROPOSE],
        "summary_human": "Always ask before sending anything",
    },
    "read_project": {
        "capabilities": [
            Capability.PROJECT_READ,
            Capability.COMMITMENT_READ,
            Capability.MEMORY_RETRIEVE,
        ],
        "summary_human": "Can read a specific project",
    },
}

from enum import StrEnum

from pydantic import BaseModel, Field


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class AgentConnection(BaseModel):
    id: str
    space_id: str = "personal"
    name: str
    runtime_info: dict = Field(default_factory=dict)
    status: ConnectionStatus = ConnectionStatus.PENDING
    credential_hash: str = ""
    paired_at: str | None = None
    revoked_at: str | None = None

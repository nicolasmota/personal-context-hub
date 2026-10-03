from enum import StrEnum

from pydantic import BaseModel, Field


class ManifestStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class DisclosedRef(BaseModel):
    id: str
    type: str
    version: int


class ContextManifest(BaseModel):
    id: str
    space_id: str = "personal"
    connection_id: str
    purpose: str
    requested_capabilities: list[str] = Field(default_factory=list)
    selectors: dict[str, str] = Field(default_factory=dict)
    disclosed_refs: list[DisclosedRef] = Field(default_factory=list)
    redaction_notices: list[str] = Field(default_factory=list)
    expires_at: str
    status: ManifestStatus = ManifestStatus.ACTIVE
    entities: list[dict] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)

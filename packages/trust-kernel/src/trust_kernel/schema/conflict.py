from enum import StrEnum

from pydantic import BaseModel


class ConflictKind(StrEnum):
    DUPLICATE = "duplicate"
    CONTRADICTION = "contradiction"


class ConflictStatus(StrEnum):
    OPEN = "open"
    RESOLVED_KEEP_EXISTING = "resolved_keep_existing"
    RESOLVED_ACCEPT_NEW = "resolved_accept_new"
    RESOLVED_MERGED = "resolved_merged"


class Conflict(BaseModel):
    id: str
    space_id: str = "personal"
    memory_id: str | None = None
    proposal_id: str
    kind: ConflictKind
    status: ConflictStatus = ConflictStatus.OPEN
    detail: str = ""

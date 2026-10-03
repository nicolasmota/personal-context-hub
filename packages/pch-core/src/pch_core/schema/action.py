from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class ActionIntent(BaseModel):
    id: str
    space_id: str = "personal"
    connection_id: str
    kind: str
    summary_human: str
    payload: dict[str, Any] = Field(default_factory=dict)
    basis_refs: list[str] = Field(default_factory=list)
    idempotency_key: str
    contract_id: str
    decision: str | None = None
    risk: str = "unspecified"
    reversible: bool = False
    valid_until: str | None = None
    limits: dict[str, Any] = Field(default_factory=dict)
    status: IntentStatus = IntentStatus.PENDING
    declined_parent_id: str | None = None
    created_at: str
    decided_at: str | None = None

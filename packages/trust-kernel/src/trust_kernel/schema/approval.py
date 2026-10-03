from enum import StrEnum

from pydantic import BaseModel, Field


class DecisionKind(StrEnum):
    APPROVED = "approved"
    DECLINED = "declined"


class Approval(BaseModel):
    id: str
    space_id: str = "personal"
    intent_ref: str
    intent_kind: str = "action"
    decision: DecisionKind
    decided_at: str
    context_shown: dict = Field(default_factory=dict)

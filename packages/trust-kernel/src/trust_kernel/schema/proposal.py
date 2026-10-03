from enum import StrEnum

from pydantic import BaseModel, Field

from trust_kernel.schema.memory import Memory


class ProposalStatus(StrEnum):
    PENDING = "pending"
    AUTO_ACCEPTED = "auto_accepted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class MemoryProposal(BaseModel):
    id: str
    space_id: str = "personal"
    proposed_memory: Memory
    evidence_refs: list[str] = Field(default_factory=list)
    submitted_by: str
    status: ProposalStatus = ProposalStatus.PENDING
    policy_verdict: str = "needs_review"
    conflict_ids: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str | None = None


class OperationalProposal(BaseModel):
    id: str
    space_id: str = "personal"
    target_id: str
    operational_phase: str | None = None
    current_step: str | None = Field(default=None, max_length=200)
    situation_intent: str | None = Field(default=None, max_length=200)
    submitted_by: str
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str

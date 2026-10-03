from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class EvidenceKind(StrEnum):
    OBSERVATION = "observation"
    USER_CONFIRMED = "user_confirmed"
    SOURCE_FACT = "source_fact"
    AGENT_INFERENCE = "agent_inference"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Evidence(UniversalMetadata):
    kind: EvidenceKind
    source: str
    authority_label: str
    observed_at: str
    statement: str
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    provenance_chain: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

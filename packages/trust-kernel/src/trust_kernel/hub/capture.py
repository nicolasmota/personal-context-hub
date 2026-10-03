from __future__ import annotations

from typing import Any

from trust_kernel.errors import ValidationFailed
from trust_kernel.hub.const import OWNER
from trust_kernel.schema.evidence import EvidenceKind, VerificationStatus


def _required(value: str | None, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationFailed(f"{label} is required")
    return text


class CaptureMixin:
    def capture_experience(
        self,
        *,
        action: str,
        operating_context: str,
        outcome: str,
        occurred_at: str,
        provenance: str,
        feedback: str | None = None,
        lesson: str | None = None,
        confidence: float = 1.0,
        authority: str = "user_confirmed",
        actor: str = OWNER,
    ) -> dict[str, Any]:
        body = {
            "action": _required(action, "action"),
            "operating_context": _required(operating_context, "operating_context"),
            "outcome": _required(outcome, "outcome"),
            "occurred_at": _required(occurred_at, "occurred_at"),
            "provenance": _required(provenance, "provenance"),
            "feedback": feedback,
            "lesson": lesson,
            "confidence": confidence,
            "authority": authority,
        }
        with self.engine.tx():
            return self.create("experience", body, actor)

    def record_evidence(
        self,
        *,
        kind: str,
        source: str,
        authority_label: str,
        observed_at: str,
        statement: str,
        confidence: float = 1.0,
        verification_status: str = "unverified",
        provenance_chain: list[str] | None = None,
        derived_from: list[str] | None = None,
        supports: str | None = None,
        actor: str = OWNER,
    ) -> dict[str, Any]:
        try:
            parsed_kind = EvidenceKind(kind)
        except ValueError as exc:
            raise ValidationFailed("unknown evidence kind") from exc
        try:
            parsed_verification = VerificationStatus(verification_status)
        except ValueError as exc:
            raise ValidationFailed("unknown verification status") from exc
        chain = list(provenance_chain or [])
        for target in derived_from or []:
            if target not in chain:
                chain.append(target)
        body = {
            "kind": parsed_kind.value,
            "source": _required(source, "source"),
            "authority_label": _required(authority_label, "authority_label"),
            "observed_at": _required(observed_at, "observed_at"),
            "statement": _required(statement, "statement"),
            "confidence": confidence,
            "verification_status": parsed_verification.value,
            "provenance_chain": chain,
            "authority": "agent_inferred"
            if parsed_kind is EvidenceKind.AGENT_INFERENCE
            else "user_confirmed",
        }
        with self.engine.tx():
            for target in derived_from or []:
                self.get(target)
            if supports:
                self.get(supports)
            stored = self.create("evidence", body, actor)
            for target in derived_from or []:
                self.create_relation(stored["id"], target, "derived_from", actor)
            if supports:
                self.create_relation(supports, stored["id"], "supported_by", actor)
            return stored

    def admit_observation(
        self,
        *,
        source: str,
        captured_at: str,
        classification: str,
        statement: str,
        actor: str = OWNER,
    ) -> dict[str, Any]:
        stored_class = classification if classification in {"public", "personal", "private", "sensitive"} else "personal"
        return self.create(
            "evidence",
            {
                "kind": "import",
                "source": _required(source, "source"),
                "authority_label": _required(source, "source"),
                "observed_at": _required(captured_at, "captured_at"),
                "statement": _required(statement, "statement"),
                "classification": stored_class,
                "verification_status": "unverified",
                "authority": "source_imported",
                "untrusted": True,
            },
            actor,
        )

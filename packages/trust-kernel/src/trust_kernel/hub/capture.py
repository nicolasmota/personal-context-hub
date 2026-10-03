from __future__ import annotations

from typing import Any

from trust_kernel.errors import ValidationFailed
from trust_kernel.hub.const import OWNER
from trust_kernel.schema.evidence import EvidenceKind, VerificationStatus

_CLASSES = {"public", "personal", "private", "sensitive"}


def _required(value: str | None, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationFailed(f"{label} is required")
    return text


def _lesson(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _same_episode(row: dict[str, Any], identity: tuple) -> bool:
    stored = (
        row.get("project_id"),
        row.get("action"),
        row.get("operating_context"),
        row.get("outcome"),
        _lesson(row.get("lesson")),
        row.get("occurred_at"),
    )
    return stored == identity


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
        project_id: str | None = None,
        classification: str | None = None,
        actor: str = OWNER,
    ) -> dict[str, Any]:
        tied = str(project_id or "").strip() or None
        lesson_text = _lesson(lesson)
        identity = (
            tied,
            _required(action, "action"),
            _required(operating_context, "operating_context"),
            _required(outcome, "outcome"),
            lesson_text,
            _required(occurred_at, "occurred_at"),
        )
        if classification is not None and classification not in _CLASSES:
            raise ValidationFailed("unknown classification")
        body = {
            "action": identity[1],
            "operating_context": identity[2],
            "outcome": identity[3],
            "occurred_at": identity[5],
            "provenance": _required(provenance, "provenance"),
            "feedback": feedback,
            "lesson": lesson_text,
            "confidence": confidence,
            "authority": authority,
        }
        if tied:
            body["project_id"] = tied
        if classification:
            body["classification"] = classification
        with self.engine.tx():
            for row in self.list("experience"):
                if _same_episode(row, identity):
                    return row
            stored = self.create("experience", body, actor)
            if tied:
                self.reconcile_lesson_offer(tied)
            return stored

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

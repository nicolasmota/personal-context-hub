from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pch_core.context.conflicts import detect_state_conflicts
from pch_core.errors import ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.schema.audit import EventKind
from pch_core.timeutil import now_iso, row_is_current


class EvolutionMixin:
    def _preference_condition(self, row: dict[str, Any]) -> str | None:
        text = str(row.get("condition") or "").strip()
        return text or None

    def _current_preferences(self, key: str) -> list[dict[str, Any]]:
        moment = datetime.now(UTC)
        return [
            row
            for row in self.store.list("preference")
            if row.get("key") == key and row_is_current(row, moment) and not row.get("never_true")
        ]

    def _assert_evidence_may_change_state(self, evidence_ids: list[str]) -> None:
        if not evidence_ids:
            return
        kinds = []
        for evidence_id in evidence_ids:
            row = self.get(evidence_id)
            if row.get("type") != "evidence":
                raise ValidationFailed("evolve evidence must be an evidence record")
            kinds.append(row.get("kind"))
        if kinds and all(kind == "agent_inference" for kind in kinds):
            raise ValidationFailed("agent inference cannot become canonical personal state")

    def _write_transition(
        self,
        *,
        subject_id: str,
        subject_type: str,
        kind: str,
        previous_value: Any,
        new_value: Any,
        reason: str,
        experience_ids: list[str],
        evidence_ids: list[str],
        actor: str,
        valid_from: str | None = None,
        valid_until: str | None = None,
    ) -> dict:
        now = now_iso()
        body = {
            "id": new_id("state_transition"),
            "space_id": "personal",
            "type": "state_transition",
            "owner": self.person_id(),
            "created_at": now,
            "classification": "personal",
            "authority": "user_confirmed",
            "version": 1,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "kind": kind,
            "previous_value": previous_value,
            "new_value": new_value,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "experience_ids": experience_ids,
            "evidence_ids": evidence_ids,
            "reason": reason,
            "recorded_at": now,
            "labels": [],
            "source_refs": evidence_ids,
            "confidence": 1.0,
            "retention": {"mode": "until_revoked"},
            "policy_tags": [],
        }
        stored = self.store.put(body, new=True)
        self.ledger.append(
            EventKind.OBJECT_WRITE,
            actor,
            f"Recorded {kind}",
            [stored["id"], subject_id],
        )
        return stored

    def evolve(
        self,
        *,
        subject: str,
        value: Any,
        reason: str,
        experience_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        condition: str | None = None,
        actor: str = OWNER,
    ) -> dict:
        cause_reason = str(reason or "").strip()
        if not cause_reason:
            raise ValidationFailed("reason is required")
        experiences = list(experience_ids or [])
        evidence = list(evidence_ids or [])
        self._assert_evidence_may_change_state(evidence)
        key = subject.strip()
        if not key:
            raise ValidationFailed("subject is required")
        condition_text = str(condition or "").strip() or None
        with self.engine.tx():
            current = self._current_preferences(key)
            unconditional = next(
                (row for row in current if self._preference_condition(row) is None), None
            )
            if condition_text:
                if any(self._preference_condition(row) == condition_text for row in current):
                    raise ValidationFailed("that condition is already live")
                created = self.create(
                    "preference",
                    {
                        "key": key,
                        "value": value,
                        "condition": condition_text,
                        "rationale": cause_reason,
                    },
                    actor,
                )
                transition = self._write_transition(
                    subject_id=created["id"],
                    subject_type="preference",
                    kind="conditional_exception",
                    previous_value=None if unconditional is None else unconditional.get("value"),
                    new_value=value,
                    reason=cause_reason,
                    experience_ids=experiences,
                    evidence_ids=evidence,
                    actor=actor,
                    valid_from=created.get("valid_from"),
                    valid_until=None,
                )
                self.sync_state_conflicts()
                return {
                    "preference": created,
                    "transition": transition,
                    "predecessor": unconditional,
                }
            if unconditional is None:
                created = self.create(
                    "preference",
                    {"key": key, "value": value, "rationale": cause_reason},
                    actor,
                )
                transition = self._write_transition(
                    subject_id=created["id"],
                    subject_type="preference",
                    kind="update",
                    previous_value=None,
                    new_value=value,
                    reason=cause_reason,
                    experience_ids=experiences,
                    evidence_ids=evidence,
                    actor=actor,
                    valid_from=created.get("valid_from"),
                )
                self.sync_state_conflicts()
                return {"preference": created, "transition": transition}
            superseded = self.supersede(
                unconditional["id"],
                {"value": value, "rationale": cause_reason},
                actor,
                experience_ids=experiences,
                evidence_ids=evidence,
                reason=cause_reason,
            )
            self.sync_state_conflicts()
            return {
                "preference": superseded["successor"],
                "transition": superseded["transition"],
                "superseded": superseded,
            }

    def sync_state_conflicts(self) -> list[dict]:
        detected = detect_state_conflicts(self.store.list("preference"), self.store.list("memory"))
        existing = {row.get("subject"): row for row in self.store.list("state_conflict")}
        written: list[dict] = []
        now = now_iso()
        for item in detected:
            prior = existing.get(item["subject"])
            body = {
                "id": prior["id"] if prior else new_id("state_conflict"),
                "space_id": "personal",
                "type": "state_conflict",
                "owner": self.person_id(),
                "created_at": prior.get("created_at") if prior else now,
                "classification": "personal",
                "authority": "user_confirmed",
                "version": int(prior.get("version", 0)) + 1 if prior else 1,
                "labels": [],
                "source_refs": item["evidence_ids"],
                "confidence": 1.0,
                "retention": {"mode": "until_revoked"},
                "policy_tags": [],
                **item,
            }
            written.append(self.store.put(body, new=prior is None))
        return written

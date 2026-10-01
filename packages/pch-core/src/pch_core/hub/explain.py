from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pch_core.errors import NotFound, ValidationFailed
from pch_core.timeutil import now_iso, row_is_current


def _condition(row: dict[str, Any]) -> str | None:
    text = str(row.get("condition") or "").strip()
    return text or None


class ExplainMixin:
    def explain_subject(self, subject: str) -> dict[str, Any]:
        key = str(subject or "").strip()
        if not key:
            raise ValidationFailed("subject is required")
        rows = [row for row in self.store.list("preference") if row.get("key") == key]
        if self._open_conflict(key) or self._split_current(rows):
            return self._explanation(key, "disputed", value=None, conflict_status="unresolved")
        current = [row for row in self._current_preferences(key) if not row.get("declined")]
        if current:
            chosen = next((row for row in current if _condition(row) is None), current[0])
            return self._explanation(key, "live", preference=chosen)
        if any(row.get("declined") for row in rows):
            return self._explanation(key, "declined", value=None)
        if any(row.get("never_true") for row in rows):
            return self._explanation(key, "revoked", value=None)
        moment = datetime.now(UTC)
        if any(row.get("valid_until") and not row_is_current(row, moment) for row in rows):
            return self._explanation(key, "expired", value=None)
        return self._explanation(key, "unknown", value=None)

    def source_impact(self, evidence_id: str) -> dict[str, Any]:
        self._require_evidence(evidence_id)
        moment = datetime.now(UTC)
        live_facts = []
        for row in self.store.list("preference"):
            if row.get("declined") or row.get("never_true") or not row_is_current(row, moment):
                continue
            if evidence_id not in self._citations(row):
                continue
            live_facts.append({"id": row["id"], "key": row.get("key"), "value": row.get("value")})
        pending = []
        for row in self.store.list("proposal"):
            if row.get("status") != "pending":
                continue
            if evidence_id not in list(row.get("evidence_refs") or []):
                continue
            memory = row.get("proposed_memory") or {}
            pending.append(
                {
                    "id": row["id"],
                    "statement": row.get("statement") or memory.get("statement") or "",
                }
            )
        return {
            "evidence_id": evidence_id,
            "live_facts": live_facts,
            "pending_proposals": pending,
        }

    def withdraw_source(self, evidence_id: str) -> dict[str, Any]:
        impact = self.source_impact(evidence_id)
        with self.engine.tx():
            row = self._require_evidence(evidence_id)
            row["verification_status"] = "rejected"
            row["updated_at"] = now_iso()
            self.store.put(row)
        return impact

    def _require_evidence(self, evidence_id: str) -> dict[str, Any]:
        row = self.get(evidence_id)
        if row.get("type") != "evidence":
            raise ValidationFailed("source must be evidence")
        return row

    def _open_conflict(self, key: str) -> bool:
        return any(
            row.get("subject") == key and row.get("status") == "open"
            for row in self.store.list("state_conflict")
        )

    def _split_current(self, rows: list[dict[str, Any]]) -> bool:
        moment = datetime.now(UTC)
        unconditional = [
            row
            for row in rows
            if row_is_current(row, moment) and not row.get("declined") and _condition(row) is None
        ]
        return len({repr(row.get("value")) for row in unconditional}) > 1

    def _citations(self, preference: dict[str, Any]) -> set[str]:
        cited = {str(item) for item in (preference.get("source_refs") or [])}
        transition = self._latest_transition(preference["id"])
        if transition:
            cited.update(str(item) for item in (transition.get("evidence_ids") or []))
        return cited

    def _latest_transition(self, subject_id: str) -> dict[str, Any] | None:
        matches = [
            row
            for row in self.store.list("state_transition")
            if row.get("subject_id") == subject_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda row: str(row.get("recorded_at") or ""))

    def _evidence_views(self, ids: list[str]) -> list[dict[str, Any]]:
        views = []
        for evidence_id in ids:
            try:
                row = self.get(evidence_id)
            except NotFound:
                continue
            if row.get("type") != "evidence":
                continue
            views.append(
                {
                    "id": row["id"],
                    "kind": row.get("kind"),
                    "statement": row.get("statement"),
                    "authority_label": row.get("authority_label"),
                }
            )
        return views

    def _explanation(
        self,
        key: str,
        status: str,
        *,
        preference: dict[str, Any] | None = None,
        value: Any = None,
        conflict_status: str | None = None,
    ) -> dict[str, Any]:
        chosen = preference
        transition = self._latest_transition(chosen["id"]) if chosen else None
        evidence_ids: list[str] = []
        if transition:
            evidence_ids.extend(str(item) for item in (transition.get("evidence_ids") or []))
        elif chosen:
            evidence_ids.extend(str(item) for item in (chosen.get("source_refs") or []))
        shown_value = chosen.get("value") if chosen is not None and status == "live" else value
        return {
            "subject": key,
            "status": status,
            "value": shown_value,
            "authority": None if chosen is None else chosen.get("authority"),
            "effective_from": None if chosen is None else chosen.get("valid_from"),
            "effective_until": None if chosen is None else chosen.get("valid_until"),
            "evidence": self._evidence_views(evidence_ids),
            "previous_value": None if transition is None else transition.get("previous_value"),
            "preference_id": None if chosen is None else chosen["id"],
            "conflict_status": conflict_status,
        }

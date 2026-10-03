from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trust_kernel.errors import NotFound, ValidationFailed
from trust_kernel.timeutil import now_iso, row_is_current

_KINDS = {"preference", "memory", "goal", "project", "experience"}
_IMPACT_TYPES = ("preference", "memory", "goal", "project", "experience")


def _condition(row: dict[str, Any]) -> str | None:
    text = str(row.get("condition") or "").strip()
    return text or None


def _shown_value(row: dict[str, Any]) -> Any:
    kind = row.get("type")
    if kind == "preference":
        return row.get("value")
    if kind == "experience":
        return row.get("outcome")
    if kind == "memory":
        return row.get("statement")
    return row.get("title") or row.get("value") or row.get("statement")


class ExplainMixin:
    def explain_subject(self, subject: str, projection_id: str | None = None) -> dict[str, Any]:
        key = str(subject or "").strip()
        if not key:
            raise ValidationFailed("subject is required")
        row = self._row_by_id(key)
        if row is not None:
            return self._explain_row(row, projection_id)
        return self._explain_preference_key(key, projection_id)

    def source_impact(self, evidence_id: str) -> dict[str, Any]:
        self._require_evidence(evidence_id)
        moment = datetime.now(UTC)
        live_facts = []
        for type_ in _IMPACT_TYPES:
            for row in self.store.list(type_):
                if type_ == "preference":
                    if row.get("declined") or row.get("never_true") or not row_is_current(row, moment):
                        continue
                elif row.get("valid_until") and not row_is_current(row, moment):
                    continue
                if evidence_id not in self._citations(row):
                    continue
                live_facts.append(
                    {
                        "id": row["id"],
                        "type": type_,
                        "key": row.get("key"),
                        "value": _shown_value(row),
                    }
                )
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
        issued = []
        for row in self.store.list("disclosure_receipt"):
            if evidence_id not in list(row.get("evidence_ids") or []):
                continue
            issued.append(
                {
                    "id": row["id"],
                    "contract_id": row.get("contract_id"),
                    "connection_id": row.get("connection_id"),
                }
            )
        return {
            "evidence_id": evidence_id,
            "live_facts": live_facts,
            "pending_proposals": pending,
            "issued_projections": issued,
        }

    def withdraw_source(self, evidence_id: str) -> dict[str, Any]:
        impact = self.source_impact(evidence_id)
        with self.engine.tx():
            row = self._require_evidence(evidence_id)
            row["verification_status"] = "rejected"
            row["updated_at"] = now_iso()
            self.store.put(row)
        return impact

    def _row_by_id(self, key: str) -> dict[str, Any] | None:
        try:
            row = self.get(key)
        except NotFound:
            return None
        if row.get("type") not in _KINDS:
            return None
        return row

    def _explain_preference_key(self, key: str, projection_id: str | None) -> dict[str, Any]:
        rows = [row for row in self.store.list("preference") if row.get("key") == key]
        if self._open_conflict(key) or self._split_current(rows):
            chosen = next((row for row in rows if row_is_current(row, datetime.now(UTC))), None)
            return self._explanation(key, "disputed", preference=chosen, value=None, conflict_status="unresolved")
        current = [row for row in self._current_preferences(key) if not row.get("declined")]
        if current:
            chosen = next((row for row in current if _condition(row) is None), current[0])
            status = "omitted" if self._was_omitted(projection_id, chosen) else "live"
            return self._explanation(key, status, preference=chosen, value=None if status == "omitted" else chosen.get("value"))
        if any(row.get("declined") for row in rows):
            return self._explanation(key, "declined", value=None)
        if any(row.get("never_true") for row in rows):
            return self._explanation(key, "revoked", value=None)
        moment = datetime.now(UTC)
        if any(row.get("valid_until") and not row_is_current(row, moment) for row in rows):
            return self._explanation(key, "expired", value=None)
        return self._explanation(key, "unknown", value=None)

    def _explain_row(self, row: dict[str, Any], projection_id: str | None) -> dict[str, Any]:
        status = self._row_status(row)
        if status == "live" and self._was_omitted(projection_id, row):
            status = "omitted"
        value = None if status != "live" else _shown_value(row)
        return self._explanation(str(row.get("key") or row["id"]), status, preference=row, value=value)

    def _row_status(self, row: dict[str, Any]) -> str:
        if row.get("declined"):
            return "declined"
        if row.get("never_true"):
            return "revoked"
        subject = str(row.get("key") or row["id"])
        if self._open_conflict(subject) or self._conflict_names(row["id"]):
            return "disputed"
        moment = datetime.now(UTC)
        if row.get("valid_until") and not row_is_current(row, moment):
            return "expired"
        return "live"

    def _was_omitted(self, projection_id: str | None, row: dict[str, Any]) -> bool:
        if not projection_id:
            return False
        receipts = [
            item
            for item in self.store.list("disclosure_receipt")
            if item.get("contract_id") == projection_id
        ]
        if not receipts:
            return False
        item_ids = {str(item) for item in (receipts[0].get("item_ids") or [])}
        return row["id"] not in item_ids

    def _conflict_names(self, obj_id: str) -> bool:
        return any(
            row.get("status") == "open" and obj_id in list(row.get("claim_ids") or [])
            for row in self.store.list("state_conflict")
        )

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

    def _contradicting(self, subject: str, chosen: dict[str, Any] | None) -> list[dict[str, Any]]:
        support: set[str] = set()
        if chosen is not None:
            support = self._citations(chosen)
        ids: list[str] = []
        names = {subject}
        if chosen is not None:
            names.add(str(chosen.get("key") or ""))
            names.add(chosen["id"])
        for row in self.store.list("state_conflict"):
            if row.get("status") != "open":
                continue
            claim_ids = {str(item) for item in (row.get("claim_ids") or [])}
            if row.get("subject") not in names and not (names & claim_ids):
                continue
            for evidence_id in row.get("evidence_ids") or []:
                if str(evidence_id) not in support:
                    ids.append(str(evidence_id))
        return self._evidence_views(ids)

    def _previous_value(self, chosen: dict[str, Any] | None, transition: dict[str, Any] | None) -> Any:
        if transition is not None:
            return transition.get("previous_value")
        if chosen is None:
            return None
        history = self.store.versions.history(chosen["id"])
        if len(history) < 2:
            return None
        prior = history[-2]
        return prior.get("value", prior.get("statement", prior.get("title")))

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
        if chosen is not None and status == "live":
            shown_value = value if value is not None else _shown_value(chosen)
        else:
            shown_value = value
        effective = None if chosen is None else (chosen.get("valid_from") or chosen.get("created_at"))
        return {
            "subject": key,
            "kind": None if chosen is None else chosen.get("type"),
            "status": status,
            "value": shown_value,
            "authority": None if chosen is None else chosen.get("authority"),
            "effective_from": None if chosen is None else chosen.get("valid_from"),
            "effective_time": effective,
            "effective_until": None if chosen is None else chosen.get("valid_until"),
            "evidence": self._evidence_views(evidence_ids),
            "contradicting": self._contradicting(key, chosen),
            "previous_value": self._previous_value(chosen, transition),
            "preference_id": None if chosen is None else chosen["id"],
            "conflict_status": conflict_status,
        }

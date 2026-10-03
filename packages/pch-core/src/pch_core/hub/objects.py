from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pch_core.errors import ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.memory.orphans import orphan_derived
from pch_core.policy.evaluator import PolicyInput, evaluate
from pch_core.retrieval.search import citations_for
from pch_core.retrieval.search import search as fts_search
from pch_core.schema.audit import EventKind
from pch_core.schema.project import OperationalPhase
from pch_core.timeutil import now_iso, row_is_current, validate_interval


class ObjectsMixin:
    def _base(self, type_: str, extra: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        owner = self.person_id()
        payload = {
            "id": extra.get("id") or new_id(type_),
            "space_id": "personal",
            "type": type_,
            "labels": extra.get("labels") or [],
            "classification": extra.get("classification", "personal"),
            "owner": owner,
            "created_at": extra.get("created_at") or now,
            "updated_at": now,
            "source_refs": extra.get("source_refs") or [],
            "confidence": extra.get("confidence", 1.0),
            "authority": extra.get("authority", "user_confirmed"),
            "retention": extra.get("retention") or {"mode": "until_revoked"},
            "policy_tags": extra.get("policy_tags") or [],
            "version": extra.get("version", 1),
        }
        skip = set(payload) | {"id"}
        for k, _v in extra.items():
            if k not in skip or k in extra:
                payload[k] = extra[k]
        payload["id"] = extra.get("id") or payload["id"]
        payload["type"] = type_
        payload["owner"] = owner
        if type_ in ("preference", "memory"):
            payload.setdefault("valid_from", payload["created_at"])
            payload.setdefault("valid_until", None)
            payload.setdefault("never_true", False)
        return payload

    def _assert_interval(self, payload: dict[str, Any]) -> None:
        try:
            validate_interval(payload.get("valid_from"), payload.get("valid_until"))
        except ValueError as exc:
            raise ValidationFailed(str(exc)) from exc

    def _assert_operational(self, payload: dict[str, Any]) -> None:
        phase = payload.get("operational_phase")
        if phase is not None:
            try:
                OperationalPhase(phase)
            except ValueError as exc:
                raise ValidationFailed("unknown operational_phase") from exc
        for key in ("current_step", "situation_intent"):
            value = payload.get(key)
            if value is None:
                continue
            text = str(value)
            if len(text) > 200:
                raise ValidationFailed(f"{key} exceeds 200 characters")

    def _assert_preference_slot(self, payload: dict[str, Any]) -> None:
        new_condition = str(payload.get("condition") or "").strip() or None
        at = datetime.now(UTC)
        for row in self.store.list("preference"):
            if row.get("key") != payload.get("key"):
                continue
            if not row_is_current(row, at):
                continue
            row_condition = str(row.get("condition") or "").strip() or None
            if row_condition == new_condition:
                raise ValidationFailed(
                    "a current preference with this key and condition already exists; supersede it"
                )

    def _current_preference_for_key(self, key: str, *, exclude_id: str | None = None) -> dict | None:
        at = datetime.now(UTC)
        for row in self.store.list("preference"):
            if row.get("key") != key or row["id"] == exclude_id:
                continue
            if row_is_current(row, at):
                return row
        return None

    def create(self, type_: str, body: dict[str, Any], actor: str = OWNER) -> dict:
        with self.engine.tx():
            payload = self._base(type_, body)
            payload["authority"] = body.get("authority", "user_confirmed")
            if type_ in ("preference", "memory"):
                self._assert_interval(payload)
            if type_ in ("project", "goal"):
                self._assert_operational(payload)
            if type_ == "preference":
                self._assert_preference_slot(payload)
            stored = self.store.put(payload, new=True)
            self.ledger.append(EventKind.OBJECT_WRITE, actor, f"Created {type_}", [stored["id"]])
            if type_ in ("memory", "preference"):
                self.sync_state_conflicts()
            return stored

    def get(self, obj_id: str, include_deleted: bool = False) -> dict:
        return self.store.get(obj_id, include_deleted=include_deleted)

    def list(self, type_: str | None = None, project_id: str | None = None) -> list[dict]:
        return self.store.list(type_, project_id)

    def patch(self, obj_id: str, body: dict[str, Any], if_match: int | None, actor: str = OWNER) -> dict:
        with self.engine.tx():
            current = self.store.get(obj_id)
            self.store.versions.check(int(current.get("version", 1)), if_match)
            merged = {**current, **body}
            merged["id"] = obj_id
            merged["type"] = current["type"]
            merged["version"] = int(current.get("version", 1)) + 1
            if actor == OWNER:
                merged["authority"] = "user_confirmed"
            if current.get("type") in ("preference", "memory"):
                self._assert_interval(merged)
            if current.get("type") in ("project", "goal"):
                self._assert_operational(merged)
            stored = self.store.put(merged)
            self.ledger.append(EventKind.OBJECT_WRITE, actor, f"Updated {current['type']}", [obj_id])
            return stored

    def supersede(
        self,
        obj_id: str,
        body: dict[str, Any],
        actor: str = OWNER,
        *,
        experience_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        reason: str | None = None,
        rule_id: str | None = None,
    ) -> dict:
        with self.engine.tx():
            current = self.store.get(obj_id)
            if current.get("type") not in ("preference", "memory"):
                raise ValidationFailed("only preferences and memories can be superseded")
            now = now_iso()
            if not row_is_current(current, datetime.now(UTC)):
                raise ValidationFailed("target is not current")
            predecessor = {
                **current,
                "valid_until": now,
                "version": int(current.get("version", 1)) + 1,
            }
            if actor == OWNER:
                predecessor["authority"] = "user_confirmed"
            pred_stored = self.store.put(predecessor)
            skip = {"id", "version", "created_at", "updated_at"}
            extra = {k: v for k, v in current.items() if k not in skip}
            extra.update(body)
            extra.pop("id", None)
            extra["valid_from"] = now
            extra["valid_until"] = None
            extra["never_true"] = False
            if actor == OWNER:
                extra["authority"] = "user_confirmed"
            else:
                extra["authority"] = extra.get("authority", "user_confirmed")
            successor = self.create(current["type"], extra, actor=actor)
            if current["type"] == "preference":
                previous_value = current.get("value")
                new_value = successor.get("value")
            else:
                previous_value = current.get("statement")
                new_value = successor.get("statement")
            transition = self._write_transition(
                subject_id=successor["id"],
                subject_type=current["type"],
                kind="supersession",
                previous_value=previous_value,
                new_value=new_value,
                reason=reason or str(body.get("rationale") or "superseded"),
                experience_ids=list(experience_ids or []),
                evidence_ids=list(evidence_ids or []),
                actor=actor,
                valid_from=successor.get("valid_from"),
                rule_id=rule_id,
            )
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                actor,
                f"Superseded {current['type']}",
                [pred_stored["id"], successor["id"]],
                extra={"supersedes": pred_stored["id"], "successor": successor["id"]},
            )
            return {"predecessor": pred_stored, "successor": successor, "transition": transition}

    def retract_never_true(self, obj_id: str, actor: str = OWNER) -> dict:
        with self.engine.tx():
            current = self.store.get(obj_id)
            if current.get("type") not in ("preference", "memory"):
                raise ValidationFailed("only preferences and memories can be retracted")
            current["never_true"] = True
            current["version"] = int(current.get("version", 1)) + 1
            self.store.put(current)
            stored = self.store.tombstone(obj_id)
            stored["never_true"] = True
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                actor,
                f"Retracted {current['type']} as never true",
                [obj_id],
            )
            return stored

    def list_truth(self, type_: str) -> list[dict]:
        return [row for row in self.store.list(type_) if not row.get("never_true")]

    def delete(self, obj_id: str, actor: str = OWNER) -> dict:
        with self.engine.tx():
            stored = self.store.tombstone(obj_id)
            orphans = orphan_derived(self.store.list("memory"), obj_id)
            self.ledger.append(EventKind.OBJECT_WRITE, actor, "Deleted object", [obj_id])
            stored["_orphans"] = [o["id"] for o in orphans]
            return stored

    def versions(self, obj_id: str) -> list[dict]:
        return self.store.versions.history(obj_id)

    def search(
        self,
        query: str,
        *,
        type_: str | None = None,
        project_id: str | None = None,
        classification: str | None = None,
        actor: str = OWNER,
        purpose: str | None = None,
        starts_from: str | None = None,
        starts_to: str | None = None,
    ) -> dict:
        rows = fts_search(
            self.engine,
            query,
            type_=type_,
            project_id=project_id,
            classification=classification,
        )
        if starts_from or starts_to:
            filtered = []
            for row in rows:
                start = row.get("starts_at") or ""
                if starts_from and start < starts_from:
                    continue
                if starts_to and start > starts_to:
                    continue
                filtered.append(row)
            rows = filtered
        grants = self.grants_for(actor) if actor != OWNER else []
        kept = []
        redactions: list[str] = []
        for row in rows:
            result = evaluate(
                PolicyInput(
                    actor=actor,
                    is_owner=actor == OWNER,
                    grants=grants,
                    resource_type=row.get("type", ""),
                    resource_project=row.get("project_id"),
                    classification=row.get("classification", "personal"),
                    capability=self._cap_for(row.get("type", "")),
                    purpose=purpose,
                )
            )
            self.ledger.append(
                EventKind.POLICY_DECISION,
                actor,
                f"search {result.decision}",
                [row.get("id", "")],
                extra={"decision": result.decision},
            )
            if result.decision.value == "allow":
                item = {**row, "citations": citations_for(row)}
                kept.append(item)
            else:
                redactions.extend(result.redactions or [result.reason])
        self.ledger.append(EventKind.CONTEXT_REQUEST, actor, f"search {query!r}", [r["id"] for r in kept])
        return {"results": kept, "redactions": redactions}

from __future__ import annotations

from pch_core.errors import PolicyDenied, ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.schema.action import ActionIntent, IntentStatus
from pch_core.schema.approval import Approval, DecisionKind
from pch_core.schema.audit import EventKind
from pch_core.timeutil import now_iso


class ActionsMixin:
    def propose_action(
        self,
        actor: str,
        kind: str,
        summary: str,
        payload: dict,
        basis_refs: list[str],
        idempotency_key: str,
        contract_id: str | None = None,
    ) -> dict:
        if not str(contract_id or "").strip():
            raise ValidationFailed("contract_id is required")
        existing = None
        for row in self.store.list("action_intent"):
            if row.get("connection_id") == actor and row.get("idempotency_key") == idempotency_key:
                existing = row
                break
        if existing:
            return existing
        intent = ActionIntent(
            id=new_id("action_intent"),
            connection_id=actor,
            kind=kind,
            summary_human=summary,
            payload=payload,
            basis_refs=basis_refs,
            idempotency_key=idempotency_key,
            contract_id=str(contract_id),
            status=IntentStatus.PENDING,
            created_at=now_iso(),
        )
        body = intent.model_dump(mode="json")
        body.update(
            {
                "type": "action_intent",
                "owner": self.person_id(),
                "labels": [],
                "classification": "personal",
                "created_at": intent.created_at,
                "updated_at": now_iso(),
                "source_refs": basis_refs,
                "confidence": 1.0,
                "authority": "agent_inferred",
                "retention": {"mode": "until_revoked"},
                "policy_tags": [],
                "version": 1,
            }
        )
        declined = [
            r
            for r in self.store.list("action_intent")
            if r.get("connection_id") == actor
            and r.get("kind") == kind
            and r.get("status") == "declined"
        ]
        if declined:
            body["declined_parent_id"] = declined[-1]["id"]
        with self.engine.tx():
            self.store.put(body)
            self.ledger.append(EventKind.ACTION_INTENT, actor, summary, [intent.id])
        return body

    def decide_approval(self, intent_id: str, approved: bool) -> dict:
        with self.engine.tx():
            intent = self.store.get(intent_id)
            intent["status"] = "approved" if approved else "declined"
            intent["decided_at"] = now_iso()
            self.store.put(intent)
            approval = Approval(
                id=new_id("approval"),
                intent_ref=intent_id,
                decision=DecisionKind.APPROVED if approved else DecisionKind.DECLINED,
                decided_at=intent["decided_at"],
                context_shown={
                    "summary": intent.get("summary_human"),
                    "who": intent.get("connection_id"),
                },
            )
            ap = approval.model_dump(mode="json")
            ap.update(
                {
                    "type": "approval",
                    "owner": self.person_id(),
                    "labels": [],
                    "classification": "personal",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "source_refs": [],
                    "confidence": 1.0,
                    "authority": "user_confirmed",
                    "retention": {"mode": "until_revoked"},
                    "policy_tags": [],
                    "version": 1,
                }
            )
            self.store.put(ap)
            self.ledger.append(
                EventKind.APPROVAL_DECIDED,
                OWNER,
                "approved" if approved else "declined",
                [intent_id],
            )
            return intent

    def decide_action(
        self, intent_id: str, decision: str, narrowed_payload: dict | None = None
    ) -> dict:
        allowed = {"refuse", "narrow", "require_approval", "authorize"}
        if decision not in allowed:
            raise ValidationFailed("unknown action decision")
        with self.engine.tx():
            intent = self.store.get(intent_id)
            if intent.get("type") != "action_intent":
                raise ValidationFailed("not an action intent")
            if not str(intent.get("contract_id") or "").strip():
                raise ValidationFailed("contract_id is required")
            intent["decision"] = decision
            intent["decided_at"] = now_iso()
            if decision == "refuse":
                intent["status"] = "declined"
            elif decision == "authorize":
                intent["status"] = "approved"
            elif decision == "require_approval":
                intent["status"] = "pending"
            else:
                if narrowed_payload is None:
                    raise ValidationFailed("narrowed payload is required")
                intent["payload"] = narrowed_payload
                intent["status"] = "pending"
            self.store.put(intent)
            self.ledger.append(EventKind.APPROVAL_DECIDED, OWNER, decision, [intent_id])
            return intent

    def action_result(self, intent_id: str, status: str, actor: str) -> dict:
        with self.engine.tx():
            intent = self.store.get(intent_id)
            if intent.get("status") != "approved" and status == "executed":
                raise PolicyDenied("cannot execute unapproved intent")
            intent["status"] = status
            self.store.put(intent)
            kind = EventKind.ACTION_EXECUTED if status == "executed" else EventKind.ACTION_FAILED
            self.ledger.append(kind, actor, f"action {status}", [intent_id])
            return intent

    def events(self, kind: str | None = None, actor: str | None = None) -> list[dict]:
        return [e.model_dump(mode="json") for e in self.ledger.list_events(kind, actor)]

    def verify_events(self) -> dict:
        return self.ledger.verify()

    def idempotency_get(self, key: str) -> tuple[int, str] | None:
        row = self.engine.conn.execute(
            "SELECT status, body FROM idempotency WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return int(row["status"]), row["body"]
        return None

    def idempotency_set(self, key: str, status: int, body: str) -> None:
        self.engine.conn.execute(
            "INSERT OR REPLACE INTO idempotency (key, status, body, created_at) VALUES (?, ?, ?, ?)",
            (key, status, body, now_iso()),
        )
        self.engine.conn.commit()

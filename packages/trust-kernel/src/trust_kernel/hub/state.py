from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pch_core.errors import NotFound, PolicyDenied
from pch_core.hub.const import OWNER
from pch_core.policy.evaluator import PolicyInput, evaluate
from pch_core.schema.audit import EventKind
from pch_core.schema.state import SharedState, StateVisibility
from pch_core.timeutil import now_iso


class StateMixin:
    def set_state(self, key: str, value: Any, ttl: int, visibility: str, actor: str) -> dict:
        if actor != OWNER:
            grants = self.grants_for(actor)
            result = evaluate(PolicyInput(actor, False, grants, "shared_state", None, "personal", "state.write"))
            if result.decision.value != "allow":
                raise PolicyDenied(result.reason)
            if visibility == "shared":
                evaluate(PolicyInput(actor, False, grants, "shared_state", None, "personal", "state.share"))
                # allow share if they have state.write and visibility requested; require state.share if present in vocab
                has_share = any("state.share" in [str(c) for c in g.capabilities] for g in grants)
                if not has_share:
                    # still allow if owner-equivalent write grant exists? spec says shared requires permission
                    raise PolicyDenied("missing state.share")
        expires = (datetime.now(UTC) + timedelta(seconds=ttl)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        state = SharedState(
            key=key, value=value, ttl_seconds=ttl, expires_at=expires,
            visibility=StateVisibility(visibility), created_by=actor,
        )
        payload = state.model_dump(mode="json")
        payload.update({
            "id": f"st_{key}",
            "type": "shared_state",
            "owner": self.person_id() if self._kv_get("person_id") else actor,
            "labels": [],
            "classification": "personal",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source_refs": [],
            "confidence": 1.0,
            "authority": "agent_inferred",
            "retention": {"mode": "expires", "at": expires},
            "policy_tags": [],
            "version": 1,
        })
        with self.engine.tx():
            self.store.put(payload)
            self.ledger.append(EventKind.STATE_WRITE, actor, f"state {key}", [payload["id"]])
        return payload

    def get_state(self, key: str, actor: str) -> dict:
        payload = self.store.get(f"st_{key}")
        if payload.get("expires_at") and payload["expires_at"] < now_iso():
            raise NotFound("state expired")
        if actor != OWNER and payload.get("created_by") != actor and payload.get("visibility") != "shared":
            raise PolicyDenied()
        return payload

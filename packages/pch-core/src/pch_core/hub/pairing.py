from __future__ import annotations

import hashlib
import secrets

from pch_core.errors import PolicyDenied, Revoked, ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.policy.grants import grant_from_caps, grant_from_preset
from pch_core.retrieval.manifests import build_manifest
from pch_core.schema.audit import EventKind
from pch_core.schema.connection import AgentConnection, ConnectionStatus
from pch_core.schema.grant import Grant
from pch_core.timeutil import now_iso


class PairingMixin:
    def mint_link(self, name: str = "agent", *, labels: list[str] | None = None) -> dict:
        code = secrets.token_urlsafe(16)
        conn = AgentConnection(id=new_id("connection"), name=name, status=ConnectionStatus.PENDING)
        with self.engine.tx():
            self.store.put({**conn.model_dump(mode="json"), "type": "connection", "owner": self.person_id(),
                            "labels": list(labels or []), "classification": "private", "created_at": now_iso(),
                            "updated_at": now_iso(), "source_refs": [], "confidence": 1.0,
                            "authority": "user_confirmed", "retention": {"mode": "until_revoked"},
                            "policy_tags": [], "version": 1})
            self._kv_set(f"link:{code}", conn.id)
        return {"link": f"pch://pair/{code}", "code": code, "connection_id": conn.id}

    def pair(self, code: str, runtime_info: dict | None = None) -> dict:
        conn_id = self._kv_get(f"link:{code}")
        if not conn_id:
            raise ValidationFailed("invalid pairing code")
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.engine.tx():
            payload = self.store.get(conn_id)
            if payload.get("status") == "revoked":
                raise Revoked()
            payload["status"] = "active"
            payload["credential_hash"] = token_hash
            payload["paired_at"] = now_iso()
            payload["runtime_info"] = runtime_info or {}
            payload["version"] = int(payload.get("version", 1)) + 1
            self.store.put(payload)
            self._kv_set(f"token:{token_hash}", conn_id)
            self.ledger.append(EventKind.CONNECTION_PAIRED, conn_id, f"Paired {payload.get('name')}", [conn_id])
        return {"connection_id": conn_id, "token": token}

    def issue_connection_token(self, connection_id: str) -> str:
        payload = self.store.get(connection_id)
        if payload.get("status") == "revoked":
            raise Revoked()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.engine.tx():
            payload["status"] = "active"
            payload["credential_hash"] = token_hash
            payload["paired_at"] = payload.get("paired_at") or now_iso()
            payload["version"] = int(payload.get("version", 1)) + 1
            self.store.put(payload)
            self._kv_set(f"token:{token_hash}", connection_id)
        return token

    def actor_from_token(self, token: str) -> tuple[str, bool]:
        if token == self.owner_token:
            return OWNER, True
        digest = hashlib.sha256(token.encode()).hexdigest()
        conn_id = self._kv_get(f"token:{digest}")
        if not conn_id:
            raise Revoked("invalid token")
        payload = self.store.get(conn_id)
        if payload.get("status") == "revoked":
            raise Revoked()
        return conn_id, False

    def connections(self) -> list[dict]:
        return self.store.list("connection")

    def revoke_connection(self, conn_id: str) -> dict:
        with self.engine.tx():
            payload = self.store.get(conn_id)
            payload["status"] = "revoked"
            payload["revoked_at"] = now_iso()
            payload["version"] = int(payload.get("version", 1)) + 1
            self.store.put(payload)
            for grant in self.grants_for(conn_id):
                g = grant.model_dump()
                g["status"] = "revoked"
                self._put_grant(Grant.model_validate(g))
            for man in self.store.list("manifest"):
                if man.get("connection_id") == conn_id:
                    man["status"] = "invalidated"
                    self.store.put(man)
            self.ledger.append(EventKind.CONNECTION_REVOKED, OWNER, "Connection revoked", [conn_id])
        return payload

    def recipe_issued(self, connection_id: str, assistant: str) -> None:
        self.ledger.append(
            EventKind.CONNECTION_RECIPE_ISSUED,
            OWNER,
            f"recipe issued for {assistant}",
            [connection_id],
        )

    def _put_grant(self, grant: Grant) -> dict:
        payload = grant.model_dump(mode="json")
        payload.update({
            "type": "grant",
            "owner": self.person_id(),
            "labels": [],
            "classification": "private",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source_refs": [],
            "confidence": 1.0,
            "authority": "user_confirmed",
            "retention": {"mode": "until_revoked"},
            "policy_tags": [],
            "version": 1,
            "id": grant.id,
        })
        return self.store.put(payload)

    def create_grant(self, connection_id: str, preset: str | None, capabilities: list[str] | None,
                     selectors: dict | None, classification_ceiling: str = "private") -> dict:
        if preset:
            grant = grant_from_preset(connection_id, preset, selectors, classification_ceiling)
        else:
            grant = grant_from_caps(connection_id, capabilities or [], selectors, classification_ceiling)
        with self.engine.tx():
            stored = self._put_grant(grant)
            self.ledger.append(EventKind.GRANT_CREATED, OWNER, grant.summary_human, [grant.id, connection_id])
        return stored

    def revoke_grant(self, grant_id: str) -> dict:
        with self.engine.tx():
            payload = self.store.get(grant_id)
            payload["status"] = "revoked"
            stored = self.store.put(payload)
            self.ledger.append(EventKind.GRANT_REVOKED, OWNER, "Grant revoked", [grant_id])
        return stored

    def grants_for(self, connection_id: str) -> list[Grant]:
        out = []
        for row in self.store.list("grant"):
            if row.get("connection_id") == connection_id:
                out.append(Grant.model_validate({k: v for k, v in row.items() if k in Grant.model_fields}))
        return out

    def all_grants(self, connection_id: str | None = None) -> list[dict]:
        rows = self.store.list("grant")
        if connection_id:
            rows = [r for r in rows if r.get("connection_id") == connection_id]
        return rows

    def create_manifest(self, actor: str, purpose: str, requested: list[str],
                        selectors: dict, ttl: int = 900) -> dict:
        if actor == OWNER:
            raise ValidationFailed("owner uses CRUD, not manifests")
        conn = self.store.get(actor)
        if conn.get("status") == "revoked":
            raise Revoked()
        scoped = selectors.get("project")
        search_result = self.search("", project_id=scoped, actor=actor, purpose=purpose)
        entities = search_result["results"]
        redactions = search_result["redactions"]
        # also include project itself if allowed
        manifest = build_manifest(actor, purpose, requested, selectors, entities, redactions, ttl)
        payload = manifest.model_dump(mode="json")
        payload.update({
            "type": "manifest",
            "owner": self.person_id(),
            "labels": [],
            "classification": "private",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source_refs": [],
            "confidence": 1.0,
            "authority": "user_confirmed",
            "retention": {"mode": "expires", "at": manifest.expires_at},
            "policy_tags": [],
            "version": 1,
        })
        with self.engine.tx():
            self.store.put(payload)
            self.ledger.append(EventKind.CONTEXT_DISCLOSE, actor, f"manifest {purpose}", [manifest.id])
        return payload

    def get_manifest(self, manifest_id: str, actor: str) -> dict:
        man = self.store.get(manifest_id)
        if man.get("status") == "invalidated":
            raise Revoked("manifest invalidated")
        expires = man.get("expires_at")
        if expires and expires < now_iso():
            man["status"] = "expired"
            self.store.put(man)
            raise Revoked("manifest expired")
        if actor != OWNER and man.get("connection_id") != actor:
            raise PolicyDenied()
        return man

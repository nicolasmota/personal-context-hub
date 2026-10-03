from __future__ import annotations

from pch_core.errors import NotFound, ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.schema.audit import EventKind
from pch_core.timeutil import now_iso
from pch_core.vault.keys import key_storage


class SetupMixin:
    def _kv_get(self, key: str) -> str | None:
        row = self.engine.conn.execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
        return row["v"] if row else None

    def _kv_set(self, key: str, value: str) -> None:
        self.engine.conn.execute(
            "INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            (key, value),
        )
        self.engine.conn.commit()

    def setup_status(self) -> dict:
        person_id = self._kv_get("person_id")
        name = None
        if person_id:
            try:
                name = self.store.get(person_id).get("name")
            except NotFound:
                name = None
        return {
            "initialized": bool(self._kv_get("setup_complete")),
            "in_progress": bool(self._kv_get("setup_started")) and not self._kv_get("setup_complete"),
            "name": name,
            "encrypted": self.engine.encrypted,
            "key_storage": key_storage(self.data_dir),
        }

    def setup(self, name: str = "Me", restart: bool = False) -> dict:
        with self.engine.tx():
            if restart:
                self.engine.conn.execute("DELETE FROM objects")
                self.engine.conn.execute("DELETE FROM objects_fts")
                self.engine.conn.execute("DELETE FROM object_versions")
            already = bool(self._kv_get("setup_complete")) and not restart
            person_id = self._kv_get("person_id") or new_id("person")
            space_id = "personal"
            now = now_iso()
            if already:
                person = self.store.get(person_id)
                person["name"] = name
                person["updated_at"] = now
                person["version"] = int(person.get("version", 1)) + 1
                self.store.put(person)
                return {"person": person, "space_id": space_id, "owner_token": self.owner_token}
            self._kv_set("setup_started", "1")
            person = {
                "id": person_id,
                "space_id": space_id,
                "type": "person",
                "name": name,
                "time_zone": "UTC",
                "identities": [],
                "owner": person_id,
                "labels": [],
                "classification": "personal",
                "created_at": now,
                "updated_at": now,
                "source_refs": [],
                "confidence": 1.0,
                "authority": "user_confirmed",
                "retention": {"mode": "until_revoked"},
                "policy_tags": [],
                "version": 1,
            }
            space = {
                **person,
                "id": new_id("space"),
                "type": "space",
                "name": "Personal",
                "kind": "personal",
            }
            profile = {
                **person,
                "id": new_id("profile"),
                "type": "profile",
                "contact_norms": "",
                "working_hours": "",
                "extra": {},
            }
            self.store.put(person)
            self.store.put(space)
            self.store.put(profile)
            self._kv_set("person_id", person_id)
            self._kv_set("setup_complete", "1")
            self.ledger.append(EventKind.SETUP, OWNER, "Personal space created", [person_id])
        return {"person": person, "space_id": space_id, "owner_token": self.owner_token}

    def person_id(self) -> str:
        pid = self._kv_get("person_id")
        if not pid:
            raise ValidationFailed("setup not complete")
        return pid

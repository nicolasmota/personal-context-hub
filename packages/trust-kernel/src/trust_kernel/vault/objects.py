from __future__ import annotations

import json
from typing import Any

from pch_core.errors import NotFound
from pch_core.timeutil import now_iso
from pch_core.vault.engine import Engine
from pch_core.vault.versions import VersionStore


def _project_id(payload: dict) -> str | None:
    return payload.get("project_id")


def _search_text(payload: dict) -> str:
    parts = [
        payload.get("title") or "",
        payload.get("statement") or "",
        payload.get("charter") or "",
        payload.get("rationale") or "",
        payload.get("outcome") or "",
        payload.get("name") or "",
        payload.get("key") or "",
        payload.get("body") or "",
        payload.get("subject") or "",
        payload.get("body_text") or "",
        payload.get("sender") or "",
        " ".join(payload.get("labels") or []),
    ]
    return " ".join(p for p in parts if p)


class ObjectStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.versions = VersionStore(engine)

    def get(self, obj_id: str, include_deleted: bool = False) -> dict[str, Any]:
        row = self.engine.conn.execute(
            "SELECT json, deleted FROM objects WHERE id = ?", (obj_id,)
        ).fetchone()
        if not row or (row["deleted"] and not include_deleted):
            raise NotFound(obj_id)
        return json.loads(row["json"])

    def list(
        self,
        type_: str | None = None,
        project_id: str | None = None,
        space_id: str = "personal",
    ) -> list[dict[str, Any]]:
        sql = "SELECT json FROM objects WHERE deleted = 0 AND space_id = ?"
        args: list[Any] = [space_id]
        if type_:
            sql += " AND type = ?"
            args.append(type_)
        if project_id:
            sql += " AND project_id = ?"
            args.append(project_id)
        sql += " ORDER BY updated_at DESC"
        return [json.loads(r["json"]) for r in self.engine.conn.execute(sql, args)]

    def put(self, payload: dict[str, Any], *, new: bool = False) -> dict[str, Any]:
        obj_id = payload["id"]
        payload["updated_at"] = now_iso()
        search = _search_text(payload)
        source_key = payload.get("source_key")
        self.engine.conn.execute(
            """INSERT INTO objects (id, space_id, type, project_id, classification, authority,
                 version, deleted, json, search_text, created_at, updated_at, source_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 project_id=excluded.project_id,
                 classification=excluded.classification,
                 authority=excluded.authority,
                 version=excluded.version,
                 deleted=0,
                 json=excluded.json,
                 search_text=excluded.search_text,
                 updated_at=excluded.updated_at,
                 source_key=excluded.source_key
            """,
            (
                obj_id,
                payload.get("space_id", "personal"),
                payload["type"],
                _project_id(payload),
                payload.get("classification"),
                payload.get("authority"),
                payload.get("version", 1),
                json.dumps(payload),
                search,
                payload.get("created_at", now_iso()),
                payload["updated_at"],
                source_key,
            ),
        )
        self.engine.conn.execute("DELETE FROM objects_fts WHERE id = ?", (obj_id,))
        self.engine.conn.execute(
            "INSERT INTO objects_fts (id, search_text) VALUES (?, ?)", (obj_id, search)
        )
        self.versions.snapshot(obj_id, payload.get("version", 1), payload)
        return payload

    def tombstone(self, obj_id: str) -> dict[str, Any]:
        payload = self.get(obj_id)
        payload["tombstone"] = True
        payload["version"] = int(payload.get("version", 1)) + 1
        payload["updated_at"] = now_iso()
        self.engine.conn.execute(
            "UPDATE objects SET deleted = 1, version = ?, json = ?, updated_at = ? WHERE id = ?",
            (payload["version"], json.dumps(payload), payload["updated_at"], obj_id),
        )
        self.engine.conn.execute("DELETE FROM objects_fts WHERE id = ?", (obj_id,))
        self.versions.snapshot(obj_id, payload["version"], payload)
        return payload

    def get_by_source_key(
        self, source_key: str, include_deleted: bool = False
    ) -> dict[str, Any] | None:
        row = self.engine.conn.execute(
            "SELECT json, deleted FROM objects WHERE source_key = ?", (source_key,)
        ).fetchone()
        if not row:
            return None
        if row["deleted"] and not include_deleted:
            return None
        return json.loads(row["json"])

    def list_by_source_prefix(self, prefix: str) -> list[dict[str, Any]]:
        rows = self.engine.conn.execute(
            "SELECT json FROM objects WHERE deleted = 0 AND source_key LIKE ?",
            (f"{prefix}%",),
        ).fetchall()
        return [json.loads(r["json"]) for r in rows]

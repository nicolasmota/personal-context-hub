from __future__ import annotations

import json

from pch_core.errors import VersionConflict
from pch_core.timeutil import now_iso
from pch_core.vault.engine import Engine


class VersionStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def snapshot(self, obj_id: str, version: int, payload: dict) -> None:
        self.engine.conn.execute(
            "INSERT OR REPLACE INTO object_versions (id, version, json, recorded_at) VALUES (?, ?, ?, ?)",
            (obj_id, version, json.dumps(payload, sort_keys=True), now_iso()),
        )

    def history(self, obj_id: str) -> list[dict]:
        rows = self.engine.conn.execute(
            "SELECT version, json, recorded_at FROM object_versions WHERE id = ? ORDER BY version",
            (obj_id,),
        ).fetchall()
        out = []
        for row in rows:
            item = json.loads(row["json"])
            item["_recorded_at"] = row["recorded_at"]
            out.append(item)
        return out

    def check(self, current: int, if_match: int | None) -> None:
        if if_match is not None and if_match != current:
            raise VersionConflict(f"If-Match {if_match} does not match version {current}")

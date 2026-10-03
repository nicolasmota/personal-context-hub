from __future__ import annotations

import hashlib
import json

from pch_core.schema.audit import AuditEvent, EventKind
from pch_core.timeutil import now_iso
from pch_core.vault.engine import Engine


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class Ledger:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def head_hash(self) -> str:
        row = self.engine.conn.execute(
            "SELECT hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row["hash"] if row else "0" * 64

    def append(
        self,
        kind: EventKind | str,
        actor: str,
        summary: str,
        refs: list[str] | None = None,
        extra: dict | None = None,
    ) -> AuditEvent:
        prev = self.head_hash()
        created = now_iso()
        refs = refs or []
        extra = extra or {}
        body = {
            "kind": str(kind),
            "actor": actor,
            "refs": refs,
            "summary_human": summary,
            "prev_hash": prev,
            "created_at": created,
            "extra": extra,
        }
        digest = hashlib.sha256((prev + _canonical(body)).encode()).hexdigest()
        cur = self.engine.conn.execute(
            """INSERT INTO events (kind, actor, refs, summary_human, prev_hash, hash, created_at, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(kind),
                actor,
                json.dumps(refs),
                summary,
                prev,
                digest,
                created,
                json.dumps(extra),
            ),
        )
        seq = cur.lastrowid or 0
        return AuditEvent(
            seq=seq,
            kind=EventKind(str(kind)) if str(kind) in EventKind else EventKind.OBJECT_WRITE,
            actor=actor,
            refs=refs,
            summary_human=summary,
            prev_hash=prev,
            hash=digest,
            created_at=created,
            extra=extra,
        )

    def list_events(
        self,
        kind: str | None = None,
        actor: str | None = None,
        limit: int = 200,
    ) -> list[AuditEvent]:
        sql = "SELECT * FROM events WHERE 1=1"
        args: list = []
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        if actor:
            sql += " AND actor = ?"
            args.append(actor)
        sql += " ORDER BY seq DESC LIMIT ?"
        args.append(limit)
        rows = self.engine.conn.execute(sql, args).fetchall()
        events = []
        for row in rows:
            kind_val = row["kind"]
            try:
                ek = EventKind(kind_val)
            except ValueError:
                ek = EventKind.OBJECT_WRITE
            events.append(
                AuditEvent(
                    seq=row["seq"],
                    kind=ek,
                    actor=row["actor"],
                    refs=json.loads(row["refs"]),
                    summary_human=row["summary_human"],
                    prev_hash=row["prev_hash"],
                    hash=row["hash"],
                    created_at=row["created_at"],
                    extra=json.loads(row["extra"] or "{}"),
                )
            )
        return events

    def verify(self) -> dict:
        rows = self.engine.conn.execute(
            "SELECT * FROM events ORDER BY seq"
        ).fetchall()
        prev = "0" * 64
        for row in rows:
            body = {
                "kind": row["kind"],
                "actor": row["actor"],
                "refs": json.loads(row["refs"]),
                "summary_human": row["summary_human"],
                "prev_hash": prev,
                "created_at": row["created_at"],
                "extra": json.loads(row["extra"] or "{}"),
            }
            expected = hashlib.sha256((prev + _canonical(body)).encode()).hexdigest()
            if row["hash"] != expected or row["prev_hash"] != prev:
                return {"ok": False, "broken_at": row["seq"]}
            prev = row["hash"]
        return {"ok": True, "count": len(rows), "head": prev}

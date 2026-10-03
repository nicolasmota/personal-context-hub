from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pch_core.vault.engine import Engine

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


class Ranker(Protocol):
    def rank(self, rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]: ...


class DefaultRanker:
    def rank(self, rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        def score(item: dict[str, Any]) -> tuple:
            authority = item.get("authority") == "user_confirmed"
            return (1 if authority else 0, item.get("updated_at") or "")

        return sorted(rows, key=score, reverse=True)


def fts5_match_expr(raw: str) -> str | None:
    """Build an FTS5 MATCH expression from user text.

    SQLCipher's FTS5 parser treats bound ``?`` as syntax, so callers interpolate
    this string. Tokens are restricted to ``[A-Za-z0-9_]``.
    """
    tokens = _TOKEN.findall(raw)
    if not tokens:
        return None
    quoted = [f'"{tok}"' for tok in tokens]
    return " AND ".join(quoted)


def search(
    engine: Engine,
    query: str,
    *,
    type_: str | None = None,
    project_id: str | None = None,
    classification: str | None = None,
    ranker: Ranker | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ranker = ranker or DefaultRanker()
    args: list[Any] = []
    if query.strip():
        ids: list[str] = []
        match = fts5_match_expr(query)
        if match:
            # MATCH does not accept bound parameters on sqlcipher3 FTS5.
            fts = engine.conn.execute(
                f"SELECT id FROM objects_fts WHERE objects_fts MATCH '{match}' LIMIT 200"
            ).fetchall()
            ids = [r["id"] for r in fts]
        if not ids:
            sql = "SELECT json FROM objects WHERE deleted = 0 AND search_text LIKE ?"
            args = [f"%{query.strip()}%"]
        else:
            placeholders = ",".join("?" * len(ids))
            sql = f"SELECT json FROM objects WHERE deleted = 0 AND id IN ({placeholders})"
            args = list(ids)
    else:
        sql = "SELECT json FROM objects WHERE deleted = 0"
    if type_:
        sql += " AND type = ?"
        args.append(type_)
    if project_id:
        sql += " AND project_id = ?"
        args.append(project_id)
    if classification:
        sql += " AND classification = ?"
        args.append(classification)
    rows = [json.loads(r["json"]) for r in engine.conn.execute(sql, args)]
    return ranker.rank(rows, query)[:limit]


def citations_for(payload: dict[str, Any]) -> list[dict[str, str]]:
    refs = payload.get("source_refs") or []
    return [{"id": r, "role": "source"} for r in refs]

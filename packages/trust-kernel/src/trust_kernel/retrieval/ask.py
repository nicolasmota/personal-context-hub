from __future__ import annotations

import json
import re
from typing import Any

from pch_core.vault.engine import Engine

_TOKEN = re.compile(r"[A-Za-z0-9_]+")

_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "for",
        "on",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "i",
        "my",
        "me",
        "we",
        "our",
        "you",
        "your",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "do",
        "does",
        "did",
        "about",
        "it",
        "this",
        "that",
        "with",
        "from",
        "o",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "da",
        "das",
        "dos",
        "e",
        "ou",
        "que",
        "qual",
        "quais",
        "como",
        "quando",
        "onde",
        "porque",
        "por",
        "para",
        "pra",
        "com",
        "sem",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "eu",
        "meu",
        "minha",
        "meus",
        "minhas",
        "voce",
        "ele",
        "ela",
        "eles",
        "elas",
        "seu",
        "sua",
        "seus",
        "suas",
        "se",
        "ser",
        "ter",
        "tem",
        "foi",
        "esta",
        "estou",
        "estamos",
    }
)

ANSWER_TYPES = frozenset(
    {
        "memory",
        "project",
        "goal",
        "commitment",
        "decision",
        "preference",
        "profile",
        "artifact",
        "person",
    }
)

MISS = (
    "Não encontrei isso no seu contexto. "
    "Grave uma memória em Memories e pergunte de novo."
)


def significant_tokens(raw: str) -> list[str]:
    toks = [t.lower() for t in _TOKEN.findall(raw)]
    return [t for t in toks if t not in _STOP and len(t) > 1]


def _blob(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(k) or "")
        for k in ("title", "statement", "charter", "rationale", "outcome", "name", "body")
    ).lower()


def retrieve(engine: Engine, question: str, *, limit: int = 8) -> list[dict[str, Any]]:
    tokens = significant_tokens(question)
    if not tokens:
        return []
    quoted = " OR ".join(f'"{tok}"' for tok in tokens)
    fts_ids: list[str] = []
    fts = engine.conn.execute(
        f"SELECT id FROM objects_fts WHERE objects_fts MATCH '{quoted}' LIMIT 200"
    ).fetchall()
    fts_ids = [r["id"] for r in fts]
    by_id: dict[str, dict[str, Any]] = {}
    if fts_ids:
        placeholders = ",".join("?" * len(fts_ids))
        for row in engine.conn.execute(
            f"SELECT json FROM objects WHERE deleted = 0 AND id IN ({placeholders})",
            fts_ids,
        ):
            payload = json.loads(row["json"])
            by_id[payload["id"]] = payload
    for row in engine.conn.execute("SELECT json FROM objects WHERE deleted = 0"):
        payload = json.loads(row["json"])
        by_id.setdefault(payload["id"], payload)
    scored: list[tuple[int, dict[str, Any]]] = []
    for payload in by_id.values():
        if payload.get("type") not in ANSWER_TYPES:
            continue
        blob = _blob(payload)
        score = sum(1 for tok in tokens if tok in blob)
        if score:
            scored.append((score, payload))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [payload for _, payload in scored[:limit]]


def compose(rows: list[dict[str, Any]]) -> dict[str, Any]:
    citations: list[dict[str, str]] = []
    lines: list[str] = []
    for row in rows:
        snippet = (
            row.get("statement")
            or row.get("title")
            or row.get("name")
            or row.get("charter")
            or ""
        )
        if not snippet:
            continue
        lines.append(f"• {snippet}")
        citations.append(
            {
                "id": row["id"],
                "type": str(row.get("type") or ""),
                "snippet": snippet,
            }
        )
    if not citations:
        return {"answer": MISS, "citations": [], "notices": ["empty"]}
    return {
        "answer": "Com base no que está no seu vault:\n" + "\n".join(lines),
        "citations": citations,
        "notices": [],
    }

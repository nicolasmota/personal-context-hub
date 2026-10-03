from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from trust_kernel.retrieval.ask import significant_tokens

_SCORE_FIELDS = (
    "title",
    "charter",
    "statement",
    "outcome",
    "rationale",
    "key",
    "name",
)


def score_text(obj: dict[str, Any]) -> str:
    return " ".join(str(obj.get(key) or "") for key in _SCORE_FIELDS).lower()


class RetrievalCandidate(BaseModel):
    item_id: str
    item_type: str
    source_ref: list[str]
    relevance: float
    signals: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    finder_notes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


def source_ref_for(row: dict[str, Any]) -> list[str]:
    refs = [str(row["id"])]
    for ref in row.get("source_refs") or []:
        text = str(ref)
        if text not in refs:
            refs.append(text)
    return refs


def candidate_from_row(
    row: dict[str, Any],
    purpose: str,
    relevance: float,
    notes: dict[str, Any] | None = None,
) -> RetrievalCandidate:
    text = score_text(row)
    tokens = significant_tokens(purpose)
    signals = [token for token in tokens if token in text]
    return RetrievalCandidate(
        item_id=str(row["id"]),
        item_type=str(row.get("type") or ""),
        source_ref=source_ref_for(row),
        relevance=relevance,
        signals=signals,
        excerpt=text or None,
        finder_notes=dict(notes or {}),
    )


def dedupe_candidates(candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
    best: dict[str, RetrievalCandidate] = {}
    order: list[str] = []
    for candidate in candidates:
        previous = best.get(candidate.item_id)
        if previous is None:
            order.append(candidate.item_id)
            best[candidate.item_id] = candidate
            continue
        if candidate.relevance > previous.relevance:
            best[candidate.item_id] = candidate
    return [best[item_id] for item_id in order]

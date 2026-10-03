from __future__ import annotations

from typing import Any, Protocol

from pch_core.retrieval.ask import significant_tokens
from pch_core.retrieval.candidate import (
    RetrievalCandidate,
    candidate_from_row,
    dedupe_candidates,
    score_text,
)


class PurposeRetriever(Protocol):
    def relevance(self, text: str, purpose: str) -> float: ...


class TokenOverlapRetriever:
    """Default retriever: fraction of purpose tokens present in the text.

    Swap this for an embedding or external memory retriever on ``Hub.retriever``.
    Policy, omissions, and the contract envelope stay in the core either way.
    """

    def relevance(self, text: str, purpose: str) -> float:
        tokens = significant_tokens(purpose)
        if not tokens:
            return 0.0
        blob = text.lower()
        hits = sum(1 for token in tokens if token in blob)
        return hits / len(tokens)

    def find_candidates(
        self,
        rows: list[dict[str, Any]],
        purpose: str,
        *,
        limit: int | None = None,
    ) -> list[RetrievalCandidate]:
        found: list[RetrievalCandidate] = []
        for row in rows:
            relevance = self.relevance(score_text(row), purpose)
            if relevance <= 0:
                continue
            found.append(candidate_from_row(row, purpose, relevance))
        found.sort(key=lambda item: (-item.relevance, item.item_id))
        deduped = dedupe_candidates(found)
        if limit is None:
            return deduped
        return deduped[:limit]

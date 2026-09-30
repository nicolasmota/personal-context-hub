from __future__ import annotations

from typing import Protocol

from pch_core.retrieval.ask import significant_tokens


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

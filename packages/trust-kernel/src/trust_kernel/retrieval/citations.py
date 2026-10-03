from __future__ import annotations

from typing import Any


def assemble(payload: dict[str, Any]) -> list[dict[str, str]]:
    from pch_core.retrieval.search import citations_for

    return citations_for(payload)

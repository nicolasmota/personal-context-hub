from __future__ import annotations

from typing import Any


def orphan_derived(memories: list[dict[str, Any]], deleted_id: str) -> list[dict[str, Any]]:
    out = []
    for mem in memories:
        refs = mem.get("source_refs") or []
        if deleted_id in refs:
            out.append(mem)
    return out

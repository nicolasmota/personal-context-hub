from __future__ import annotations

from typing import Any


def select_for_purpose(
    rows: list[dict[str, Any]],
    tokens: list[str],
    overlaps,
) -> tuple[list[dict[str, Any]], int]:
    if not tokens:
        return list(rows), 0
    kept = [row for row in rows if overlaps(row, tokens)]
    return kept, len(rows) - len(kept)


def rank_established_first(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            0 if row.get("authority") == "user_confirmed" else 1,
            row.get("created_at") or "",
            row["id"],
        ),
    )

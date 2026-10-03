from __future__ import annotations


def apply_budget[T](ranked: list[T], cap: int) -> tuple[list[T], int]:
    if cap < 0:
        cap = 0
    kept = ranked[:cap]
    overflow = max(0, len(ranked) - cap)
    return kept, overflow

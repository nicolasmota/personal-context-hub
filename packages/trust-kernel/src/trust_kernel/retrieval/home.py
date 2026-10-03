from __future__ import annotations

from typing import Any

HOME_PURPOSE = "what matters now"

_OPS_FIELDS = ("operational_phase", "current_step", "situation_intent")


def pick_home_project(projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    live = [p for p in projects if p.get("status") != "archived"]
    live.sort(key=lambda p: str(p.get("updated_at") or ""), reverse=True)
    if not live:
        return None
    ops = [p for p in live if any(p.get(field) for field in _OPS_FIELDS)]
    return (ops or live)[0]

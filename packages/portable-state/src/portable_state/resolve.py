from __future__ import annotations

from typing import Any


def plan_resolutions(
    incoming: list[dict[str, Any]],
    existing_ids: set[str],
    existing_by_id: dict[str, dict],
) -> list[dict[str, Any]]:
    out = []
    for rec in incoming:
        rid = rec.get("id")
        if rid not in existing_ids:
            out.append({"id": rid, "action": "create", "record": rec})
            continue
        old = existing_by_id.get(rid, {})
        if old.get("statement") == rec.get("statement") and old.get("title") == rec.get("title"):
            out.append({"id": rid, "action": "skip", "record": rec})
        else:
            out.append({"id": rid, "action": "conflict", "record": rec, "existing": old})
    return out


def apply_resolution(choice: str, rec: dict[str, Any]) -> dict[str, Any]:
    rec = dict(rec)
    if rec.get("authority") == "agent_inferred":
        rec["authority"] = "agent_inferred"
    if rec.get("type") == "artifact":
        rec["untrusted"] = True
    if choice == "keep_separate":
        from pch_core.ids import new_id

        rec["imported_from"] = rec.get("id")
        rec["id"] = new_id(rec.get("type", "memory"))
    return rec

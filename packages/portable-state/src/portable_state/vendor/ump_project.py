from __future__ import annotations

from typing import Any


def _kind(row: dict[str, Any]) -> str:
    type_ = row.get("type")
    if type_ in {"profile", "person"}:
        return "identity"
    if type_ == "preference":
        return "semantic"
    kind = row.get("kind")
    if kind in {"semantic", "episodic", "procedural"}:
        return kind
    return "semantic"


def _text(row: dict[str, Any]) -> str:
    if row.get("type") == "preference":
        return str(row.get("value") if row.get("value") is not None else row.get("key") or "")
    if row.get("type") in {"profile", "person"}:
        return str(row.get("name") or row.get("contact_norms") or row.get("id"))
    return str(row.get("statement") or "")


def ump_records(rows: list[dict[str, Any]], owner: str) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        records.append(
            {
                "ump": "0.1",
                "id": f"urn:ump:{row['id']}",
                "kind": _kind(row),
                "body": {"text": _text(row)},
                "scope": {"owner": owner or "person", "visibility": "private"},
                "time": {"created": row.get("created_at") or row.get("updated_at") or ""},
                "provenance": {
                    "actor": owner or "person",
                    "actor_kind": "user" if row.get("authority") == "user_confirmed" else "import",
                    "method": "api_export",
                },
            }
        )
    return records

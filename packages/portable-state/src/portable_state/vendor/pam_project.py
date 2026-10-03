from __future__ import annotations

from typing import Any


def _pam_type(row: dict[str, Any]) -> str:
    type_ = row.get("type")
    if type_ == "preference":
        return "preference"
    if type_ in {"profile", "person"}:
        return "identity" if type_ == "person" else "fact"
    kind = row.get("kind")
    if kind == "procedural":
        return "instruction"
    if kind == "episodic":
        return "episode"
    return "fact"


def _content(row: dict[str, Any]) -> str:
    if row.get("type") == "preference":
        return str(row.get("value") if row.get("value") is not None else row.get("key") or "")
    if row.get("type") in {"profile", "person"}:
        return str(
            row.get("name") or row.get("contact_norms") or row.get("statement") or row.get("id")
        )
    return str(row.get("statement") or "")


def pam_memory_store(
    rows: list[dict[str, Any]], *, exported_by: str, export_date: str
) -> dict[str, Any]:
    memories = []
    for row in rows:
        content = _content(row)
        memories.append(
            {
                "id": row["id"],
                "type": _pam_type(row),
                "content": content,
                "provenance": {
                    "platform": "personal-context-hub",
                    "extraction_method": "api_export",
                },
            }
        )
    return {
        "schema": "portable-ai-memory",
        "schema_version": "1.0",
        "spec_uri": "https://portable-ai-memory.org/spec/v1.0",
        "exported_by": exported_by,
        "export_date": export_date,
        "memories": memories,
        "relations": [],
        "conversations_index": [],
        "integrity": {"algorithm": "sha256", "count": len(memories)},
        "export_type": "full",
    }

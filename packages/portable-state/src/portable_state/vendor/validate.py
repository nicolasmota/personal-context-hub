from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMA = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "pam"
    / "portable-ai-memory.schema.json"
)


def validate_pam_store(doc: dict[str, Any]) -> None:
    if doc.get("schema") != "portable-ai-memory":
        raise ValueError("PAM schema field missing")
    if not isinstance(doc.get("schema_version"), str):
        raise ValueError("PAM schema_version missing")
    if not isinstance(doc.get("exported_by"), str) or not doc["exported_by"]:
        raise ValueError("PAM exported_by missing")
    if not isinstance(doc.get("export_date"), str):
        raise ValueError("PAM export_date missing")
    memories = doc.get("memories")
    if not isinstance(memories, list):
        raise ValueError("PAM memories must be a list")
    for item in memories:
        if not isinstance(item, dict):
            raise ValueError("PAM memory must be an object")
        if not item.get("id") or not isinstance(item.get("content"), str):
            raise ValueError("PAM memory needs id and content")
        prov = item.get("provenance") or {}
        if not isinstance(prov, dict) or not prov.get("platform"):
            raise ValueError("PAM memory needs provenance.platform")
    json.loads(_SCHEMA.read_text(encoding="utf-8"))


def validate_ump_records(records: list[Any]) -> None:
    if not isinstance(records, list):
        raise ValueError("UMP file must be a JSON array")
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("UMP record must be an object")
        if item.get("ump") != "0.1":
            raise ValueError("UMP ump must be 0.1")
        if not item.get("id"):
            raise ValueError("UMP id missing")
        if not item.get("kind"):
            raise ValueError("UMP kind missing")
        body = item.get("body") or {}
        if not isinstance(body, dict) or not isinstance(body.get("text"), str):
            raise ValueError("UMP body.text missing")
        scope = item.get("scope") or {}
        if not isinstance(scope, dict) or not scope.get("owner"):
            raise ValueError("UMP scope.owner missing")
        time = item.get("time") or {}
        if not isinstance(time, dict) or not time.get("created"):
            raise ValueError("UMP time.created missing")

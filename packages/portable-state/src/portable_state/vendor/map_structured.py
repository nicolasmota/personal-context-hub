from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pch_archive.vendor.detect import _find, load_tree


def _statement(obj: dict[str, Any]) -> str:
    for key in ("content", "text", "memory", "value"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict) and isinstance(value.get("text"), str) and value["text"].strip():
            return value["text"].strip()
    return ""


def _kind(obj: dict[str, Any]) -> str:
    raw = str(obj.get("type") or obj.get("kind") or "semantic").lower()
    if raw in {"procedural", "instruction"}:
        return "procedural"
    if raw in {"episodic", "episode"}:
        return "episodic"
    return "semantic"


def _from_memories_array(items: Any, source: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(items, list):
        return out
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        statement = _statement(item)
        if not statement:
            continue
        original = str(item.get("id") or item.get("uuid") or f"{source}-mem-{index}")
        out.append({"original_id": original, "statement": statement, "kind": _kind(item)})
    return out


def map_structured(path: Path, source: str) -> list[dict[str, str]]:
    tree = load_tree(path)
    if source == "pam":
        rel = _find(tree, "memory-store.json")
        if rel is None:
            return []
        store = json.loads(tree[rel].decode("utf-8"))
        return _from_memories_array(store.get("memories"), "pam")
    if source == "ump":
        rows: list[dict[str, str]] = []
        for key, raw in tree.items():
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            named = key.endswith(".ump.json") or key.endswith("memories.ump.json")
            head = payload[0] if isinstance(payload, list) and payload else None
            looks_ump = isinstance(head, dict) and bool(head.get("ump"))
            if not named and not looks_ump:
                continue
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                body = item.get("body") or {}
                text = body.get("text") if isinstance(body, dict) else None
                if not isinstance(text, str) or not text.strip():
                    continue
                rows.append(
                    {
                        "original_id": str(item.get("id") or text),
                        "statement": text.strip(),
                        "kind": str(item.get("kind") or "semantic"),
                    }
                )
        return rows
    rows = []
    mem_rel = _find(tree, "memories.json")
    if mem_rel:
        try:
            rows.extend(_from_memories_array(json.loads(tree[mem_rel].decode("utf-8")), source))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    if source == "chatgpt":
        user_rel = _find(tree, "user.json")
        if user_rel:
            try:
                user = json.loads(tree[user_rel].decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                user = {}
            if isinstance(user, dict):
                for field in ("about_user_message", "custom_instructions", "chatgpt_plus_user"):
                    value = user.get(field)
                    if isinstance(value, str) and value.strip():
                        rows.append(
                            {
                                "original_id": field,
                                "statement": value.strip(),
                                "kind": "procedural",
                            }
                        )
    return rows

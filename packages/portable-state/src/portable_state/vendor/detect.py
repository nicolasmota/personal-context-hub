from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any


def load_tree(path: Path) -> dict[str, bytes]:
    path = path.expanduser()
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            return {name: zf.read(name) for name in zf.namelist() if not name.endswith("/")}
    if path.is_file():
        return {path.name: path.read_bytes()}
    tree: dict[str, bytes] = {}
    for child in path.rglob("*"):
        if child.is_file():
            tree[child.relative_to(path).as_posix()] = child.read_bytes()
    return tree


def _find(tree: dict[str, bytes], name: str) -> str | None:
    if name in tree:
        return name
    matches = [key for key in tree if key == name or key.endswith("/" + name)]
    return matches[0] if matches else None


def _conversations_blob(tree: dict[str, bytes]) -> Any | None:
    rel = _find(tree, "conversations.json")
    if rel is None:
        return None
    try:
        return json.loads(tree[rel].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def detect_source(path: Path) -> str:
    tree = load_tree(path)
    keys = [key.replace("\\", "/") for key in tree]
    for key in keys:
        if key.endswith(".ump.json") or key.endswith(".ump.md"):
            return "ump"
        try:
            payload = json.loads(tree[key].decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            continue
        first = payload[0] if isinstance(payload, list) and payload else None
        if isinstance(first, dict) and first.get("ump"):
            return "ump"
    for key in keys:
        if key.endswith("memory-store.json"):
            try:
                payload = json.loads(tree[key].decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(payload, dict) and payload.get("schema") == "portable-ai-memory":
                return "pam"
    if any("Gemini Apps" in key or key.endswith("MyActivity.json") for key in keys):
        return "gemini"
    blob = _conversations_blob(tree)
    if isinstance(blob, list) and blob:
        first = blob[0] if isinstance(blob[0], dict) else {}
        if "mapping" in first:
            return "chatgpt"
        if "chat_messages" in first:
            return "claude"
    if _find(tree, "memories.json") and _find(tree, "conversations.json"):
        blob = _conversations_blob(tree)
        if isinstance(blob, list) and blob and isinstance(blob[0], dict):
            if "chat_messages" in blob[0]:
                return "claude"
        return "chatgpt"
    if _find(tree, "memories.json"):
        return "claude"
    return "unknown"

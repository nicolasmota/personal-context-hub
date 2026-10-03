from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pch_archive.vendor.detect import _conversations_blob, _find, load_tree


def _chatgpt_text(conv: dict[str, Any]) -> str:
    parts: list[str] = []
    mapping = conv.get("mapping") or {}
    if isinstance(mapping, dict):
        for node in mapping.values():
            if not isinstance(node, dict):
                continue
            message = node.get("message") or {}
            content = message.get("content") or {}
            for part in content.get("parts") or []:
                if isinstance(part, str):
                    parts.append(part)
    return "\n".join(parts)


def _claude_text(conv: dict[str, Any]) -> str:
    parts: list[str] = []
    for msg in conv.get("chat_messages") or []:
        if isinstance(msg, dict) and isinstance(msg.get("text"), str):
            parts.append(msg["text"])
    return "\n".join(parts)


def list_conversations(path: Path, source: str) -> list[dict[str, str]]:
    tree = load_tree(path)
    if source in {"chatgpt", "claude"}:
        blob = _conversations_blob(tree)
        if not isinstance(blob, list):
            return []
        out: list[dict[str, str]] = []
        for conv in blob:
            if not isinstance(conv, dict):
                continue
            cid = str(conv.get("id") or conv.get("uuid") or conv.get("title") or "thread")
            title = str(conv.get("title") or conv.get("name") or cid)
            body = _chatgpt_text(conv) if source == "chatgpt" else _claude_text(conv)
            out.append({"original_id": cid, "title": title, "body": body})
        return out
    if source == "gemini":
        out = []
        for key, raw in tree.items():
            if "Gemini Apps" not in key.replace("\\", "/"):
                continue
            if key.endswith("memories.json"):
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            threads = payload if isinstance(payload, list) else [payload]
            for conv in threads:
                if not isinstance(conv, dict):
                    continue
                cid = str(conv.get("id") or conv.get("title") or key)
                title = str(conv.get("title") or cid)
                messages = conv.get("messages") or []
                body_parts = []
                if isinstance(messages, list):
                    for msg in messages:
                        if isinstance(msg, dict) and isinstance(msg.get("text"), str):
                            body_parts.append(msg["text"])
                out.append({"original_id": cid, "title": title, "body": "\n".join(body_parts)})
        return out
    if source == "pam":
        rel = _find(tree, "memory-store.json")
        if rel is None:
            return []
        store = json.loads(tree[rel].decode("utf-8"))
        index = store.get("conversations_index") or []
        return [
            {
                "original_id": str(item.get("id") or i),
                "title": str(item.get("title") or "conversation"),
                "body": "",
            }
            for i, item in enumerate(index)
            if isinstance(item, dict)
        ]
    return []

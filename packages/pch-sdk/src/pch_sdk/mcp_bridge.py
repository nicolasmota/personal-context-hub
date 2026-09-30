from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

from pch_sdk.capture_guidance import (
    MEMORY_PROPOSE_DESCRIPTION,
    NON_CAPTURE_DESCRIPTION,
    SITUATION_READ_DESCRIPTION,
)

TOOL_NAMES = [
    "search_personal_context",
    "get_context_manifest",
    "propose_memory",
    "set_shared_state",
    "get_shared_state",
    "request_approval",
    "propose_action",
    "check_action_status",
    "get_context_contract",
    "propose_operational_state",
    "propose_relation",
]

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "search_personal_context": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "purpose": {"type": "string"},
            "scope": {"type": "object"},
        },
        "required": ["query", "purpose"],
    },
    "get_context_manifest": {
        "type": "object",
        "properties": {
            "purpose": {"type": "string"},
            "requested_capabilities": {"type": "array", "items": {"type": "string"}},
            "selectors": {"type": "object"},
            "ttl_seconds": {"type": "integer"},
        },
        "required": ["purpose", "requested_capabilities"],
    },
    "propose_memory": {
        "type": "object",
        "properties": {
            "memory": {"type": "object"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "retention": {"type": "object"},
        },
        "required": ["memory", "evidence_refs"],
    },
    "set_shared_state": {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {},
            "ttl_seconds": {"type": "integer"},
            "visibility": {"type": "string"},
        },
        "required": ["key", "value", "ttl_seconds", "visibility"],
    },
    "get_shared_state": {
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    },
    "request_approval": {
        "type": "object",
        "properties": {
            "intent_summary": {"type": "string"},
            "rationale": {"type": "string"},
            "impact": {"type": "string"},
        },
        "required": ["intent_summary", "rationale", "impact"],
    },
    "propose_action": {
        "type": "object",
        "properties": {
            "kind": {"type": "string"},
            "summary_human": {"type": "string"},
            "payload": {"type": "object"},
            "basis_refs": {"type": "array", "items": {"type": "string"}},
            "idempotency_key": {"type": "string"},
        },
        "required": ["kind", "summary_human", "payload", "basis_refs", "idempotency_key"],
    },
    "check_action_status": {
        "type": "object",
        "properties": {"intent_id": {"type": "string"}},
        "required": ["intent_id"],
    },
    "get_context_contract": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "purpose": {
                "type": "string",
                "minLength": 1,
                "description": "What the agent is trying to do for the person right now.",
            },
            "subject_ref": {
                "type": ["string", "null"],
                "description": "Optional Project id to anchor the situation.",
            },
            "max_items": {
                "type": ["integer", "null"],
                "minimum": 1,
                "description": "Optional per-category cap; engine sufficiency caps still apply.",
            },
            "as_of": {
                "type": ["string", "null"],
                "description": (
                    "UTC instant for current vs historical. Null means now."
                ),
            },
        },
        "required": ["purpose"],
    },
    "propose_operational_state": {
        "type": "object",
        "additionalProperties": False,
        "required": ["target_id"],
        "properties": {
            "target_id": {
                "type": "string",
                "description": "Project or Goal id to patch on accept.",
            },
            "operational_phase": {
                "type": ["string", "null"],
                "enum": [
                    "planning",
                    "comparing_itineraries",
                    "waiting_for_approval",
                    "choosing_hotel",
                    "other",
                    None,
                ],
            },
            "current_step": {"type": ["string", "null"], "maxLength": 200},
            "situation_intent": {"type": ["string", "null"], "maxLength": 200},
        },
    },
    "propose_relation": {
        "type": "object",
        "additionalProperties": False,
        "required": ["from_id", "to_id", "relation_type"],
        "properties": {
            "from_id": {"type": "string"},
            "to_id": {"type": "string"},
            "relation_type": {
                "type": "string",
                "enum": ["owned_by", "depends_on", "blocked_by", "related_to"],
            },
        },
    },
}


def healthcheck(base: str) -> None:
    r = httpx.get(f"{base.rstrip('/')}/health", timeout=10.0)
    r.raise_for_status()


def call_hub(base: str, token: str, name: str, arguments: dict[str, Any]) -> tuple[int, Any]:
    url = f"{base.rstrip('/')}/v1/mcp/tools/{name}"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=arguments,
        timeout=30.0,
    )
    try:
        body = r.json()
    except Exception:
        body = {"detail": r.text}
    return r.status_code, body


def map_tool_result(status: int, body: Any, *, base: str | None = None) -> dict[str, Any]:
    if status == 401:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Connection revoked by the user in the Hub."}],
        }
    if status == 0 or status >= 400:
        text = body.get("detail") if isinstance(body, dict) else str(body)
        if isinstance(text, list):
            text = json.dumps(text)
        if status == 0 or "Connection" in str(text) or "unreachable" in str(text).lower():
            payload = {
                "code": "hub_unreachable",
                "base": (base or "http://127.0.0.1:8765").rstrip("/"),
                "message": "Hub unreachable at configured PCH_BASE.",
            }
            return {
                "isError": True,
                "content": [{"type": "text", "text": json.dumps(payload)}],
            }
        return {"isError": True, "content": [{"type": "text", "text": str(text)}]}
    return {"isError": False, "content": [{"type": "text", "text": json.dumps(body)}]}


def _tool_description(name: str) -> str:
    if name == "get_context_contract":
        return SITUATION_READ_DESCRIPTION
    if name == "propose_memory":
        return MEMORY_PROPOSE_DESCRIPTION
    return f"{name.replace('_', ' ')}. {NON_CAPTURE_DESCRIPTION}"


def _mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": _tool_description(name),
            "inputSchema": TOOL_SCHEMAS[name],
        }
        for name in TOOL_NAMES
    ]


def _jsonrpc_result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def handle_message(msg: dict[str, Any], base: str, token: str) -> dict[str, Any] | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}
    if method == "initialize":
        return _jsonrpc_result(
            msg_id,
            {
                "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "personal-context-hub", "version": "0.1.0"},
            },
        )
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return _jsonrpc_result(msg_id, {})
    if method == "tools/list":
        return _jsonrpc_result(msg_id, {"tools": _mcp_tools()})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in TOOL_NAMES:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown tool {name}"},
            }
        try:
            status, body = call_hub(base, token, name, arguments)
        except httpx.HTTPError as exc:
            status, body = 0, {"detail": f"Hub unreachable at {base}: {exc}"}
        mapped = map_tool_result(status, body, base=base)
        return _jsonrpc_result(msg_id, mapped)
    if msg_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio(token: str, base: str) -> None:
    if not token:
        sys.stderr.write("PCH_TOKEN is required\n")
        raise SystemExit(1)
    try:
        healthcheck(base)
    except Exception as exc:
        sys.stderr.write(f"Hub health check failed at {base}: {exc}\n")
    stdin = sys.stdin
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        reply = handle_message(msg, base, token)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


def main(token: str | None = None, base: str | None = None) -> None:
    token = token or os.environ.get("PCH_TOKEN") or ""
    base = (base or os.environ.get("PCH_BASE") or "http://127.0.0.1:8765").rstrip("/")
    run_stdio(token, base)

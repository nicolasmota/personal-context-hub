from __future__ import annotations

import sys

from pch_sdk.capture_guidance import RUNTIME_RULE

ASSISTANTS: list[dict] = [
    {
        "id": "cursor",
        "name": "Cursor",
        "supported": True,
        "validated": True,
        "notes": "Validated via the published Cursor mcpServers recipe: stdio bridge calls get_context_contract. Cursor IDE is not launched in CI.",
    },
    {
        "id": "claude-code",
        "name": "Claude Code",
        "supported": True,
        "validated": False,
        "notes": "Recipe provided. Not a daily-driver we have run.",
    },
    {
        "id": "claude-desktop",
        "name": "Claude Desktop",
        "supported": True,
        "validated": False,
        "notes": "On WSL, run the bridge inside WSL. Recipe provided; not validated.",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "supported": True,
        "validated": False,
        "notes": "Requires MCP on the user's plan. Recipe provided; not validated.",
    },
    {
        "id": "hermes",
        "name": "Hermes",
        "supported": True,
        "validated": True,
        "notes": "Validated via Hermes MCP (isolated HERMES_HOME mcp add/test) against the stdio bridge.",
    },
    {
        "id": "openclaw",
        "name": "OpenClaw",
        "supported": True,
        "validated": False,
        "notes": "Paste under mcp.servers in ~/.openclaw/openclaw.json. Recipe provided; not validated.",
    },
]


def list_assistants() -> list[dict]:
    return [dict(item) for item in ASSISTANTS]


def get_assistant(assistant_id: str) -> dict | None:
    for item in ASSISTANTS:
        if item["id"] == assistant_id:
            return dict(item)
    return None


def _bridge(token: str, base_url: str) -> dict:
    return {
        "command": sys.executable,
        "args": ["-m", "pch_sdk", "mcp-bridge"],
        "env": {"PCH_TOKEN": token, "PCH_BASE": base_url},
    }


def render_recipe(assistant_id: str, token: str, base_url: str) -> dict:
    entry = get_assistant(assistant_id)
    if not entry:
        return {}
    if not entry["supported"]:
        return {}
    bridge = _bridge(token, base_url)
    if assistant_id == "hermes":
        snippet: dict = {"mcp_servers": {"personal-context-hub": bridge}}
        fmt = "hermes-yaml"
        instructions = (
            "Add this under mcp_servers in ~/.hermes/config.yaml, then reload MCP "
            "in the session (/reload-mcp). Paste the runtime_rule into that assistant's "
            "personal guidance."
        )
    elif assistant_id == "openclaw":
        snippet = {"mcp": {"servers": {"personal-context-hub": bridge}}}
        fmt = "openclaw-json"
        instructions = (
            "Add this under mcp.servers in ~/.openclaw/openclaw.json "
            "(or Settings → MCP), then reload. Paste the runtime_rule into that "
            "assistant's personal guidance."
        )
    else:
        snippet = {"mcpServers": {"personal-context-hub": bridge}}
        fmt = "cursor-mcp-json"
        instructions = {
            "cursor": (
                "Add this MCP server in Cursor Settings → MCP (user / this machine) "
                "so every window of Cursor can reach the Hub, then reload MCP servers. "
                "Pasting into a single project's .cursor/mcp.json is optional, not the "
                "only path."
            ),
            "claude-code": (
                "Add this MCP server in Claude Code user settings so every window can "
                "reach the Hub. Paste the runtime_rule into personal guidance."
            ),
            "claude-desktop": (
                "Paste into Claude Desktop user mcpServers config so every window can "
                "reach the Hub. Paste the runtime_rule into personal guidance."
            ),
            "chatgpt": (
                "Add as an MCP connector in ChatGPT settings (user/runtime), not a "
                "single project folder. Paste the runtime_rule into personal guidance."
            ),
        }.get(
            assistant_id,
            "Paste this MCP config into the assistant's user/runtime settings "
            "so every window can use it.",
        )
    return {
        "assistant": assistant_id,
        "format": fmt,
        "instructions": instructions,
        "snippet": snippet,
        "runtime_rule": RUNTIME_RULE,
    }

# Python SDK

Package `agent-client`. Public import: `from agent_client import Client`.

The client is a thin HTTP wrapper around pairing, MCP tools, and MCP resources. It is not an agent runtime.

## Install (workspace)

```bash
uv sync
```

From a published wheel, depend on `agent-client` (same version as the Hub, currently **0.2.0**).

## Client

```python
from agent_client import Client

c = Client("http://127.0.0.1:8765", token="")
result = c.pair("<pairing-code>")   # stores result["token"]
print(c.search("Atlas", purpose="status_update"))
print(c.call("get_context_contract", purpose="continue planning the trip"))
print(c.resource("hub://connection/self"))
```

| Method | Behavior |
|---|---|
| `Client(base, token)` | `httpx.Client` timeout 30s |
| `pair(code)` | `POST /v1/connections/pair`; assigns `self.token` |
| `call(tool, **kwargs)` | `POST /v1/mcp/tools/{tool}` |
| `search(query, purpose, project=None)` | `search_personal_context` |
| `resource(uri)` | `GET /v1/mcp/resources?uri=` |

Headers: `Authorization: Bearer {token}`.

`raise_for_status()` is used; handle `httpx.HTTPStatusError` for 401 (revoked) and 4xx validation.

## Capture guidance (for adapters)

`agent_client.capture_guidance` exports the strings baked into recipes:

- `SITUATION_READ_DESCRIPTION` — when to call `get_context_contract`
- `MEMORY_PROPOSE_DESCRIPTION` — when to call `propose_memory`
- `RUNTIME_RULE` — paste into the assistant’s personal guidance
- `NON_CAPTURE_DESCRIPTION` — for tools that must not store the person’s life

## Demo agent

```bash
uv run pch-sdk demo-agent --pair <code> --base http://127.0.0.1:8765
```

Pairs, then calls `search_personal_context` with query `Atlas` and purpose `demo`. It is a smoke client, not a product assistant.

## MCP bridge

```bash
PCH_TOKEN=… PCH_BASE=http://127.0.0.1:8765 uv run pch-sdk mcp-bridge
```

Implementation: `agent_client.mcp_bridge`. Tool names and JSON Schema: [MCP tools](mcp.md).

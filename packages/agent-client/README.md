# agent-client

Python client, MCP stdio bridge, and demo agent for Personal Context.

```python
from agent_client import Client

c = Client("http://127.0.0.1:8765", token="")
c.pair("<code>")
print(c.call("get_context_contract", purpose="continue planning the trip"))
```

```bash
uv run personal-context mcp-bridge --token "$PERSONAL_CONTEXT_TOKEN" --base http://127.0.0.1:8765
```

Documentation: [Python SDK](../../docs/reference/python-sdk.md) · [MCP tools](../../docs/reference/mcp.md)

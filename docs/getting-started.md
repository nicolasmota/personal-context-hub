# Getting started

Install the core, create a vault, and compile a context contract. The checkout does not include a web interface or a desktop shell. `packages/trust-kernel` holds personal state.

## What you need

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.12 or newer

## Install and launch

```bash
make install
uv run pch-sdk vault-init --data-dir /tmp/pch-demo --name Synthetic
uv run pch-server --host 127.0.0.1 --port 8765 --data-dir /tmp/pch-demo
```

Python 3.12 or newer is pulled in by uv. The Hub listens on `http://127.0.0.1:8765`. Full flags: [CLI](reference/cli.md).

## First-run setup

1. `uv run pch-sdk vault-init` creates the vault in the directory you pass.
2. Record an experience and evidence, then `uv run pch-sdk evolve` when a preference changes.
3. `uv run pch-sdk compile` prints one context contract for a purpose and a budget.

The vault file is `~/.pch/vault.db`, encrypted with SQLCipher. The key lives in the OS keyring when available. See [Configuration](reference/configuration.md).

## Pair an assistant (five minutes)

The Hub does not scrape your chats. An assistant sees only what a **grant** allows. Cursor and Hermes are validated MCP runtimes; other runtimes ship a recipe.

1. Start the loopback server (`make serve` or the `pch-server` command above).
2. Read the owner token from `owner.token` in the data directory, or `uv run pch token --data-dir` that directory. The HTTP API does not return it.
3. `POST /v1/connections/links` with that token to mint a pairing link.
4. `POST /v1/connections/{id}/recipe` with `"assistant": "cursor"` or `"hermes"` and paste the snippet into that runtime’s user or machine MCP settings.
5. `POST /v1/grants` for that connection.

Then, in the assistant, ask something that depends on who you are. A well-behaved client calls `get_context_contract` with a purpose string before inventing facts.

Full walkthrough: [Pair an agent](guides/pair-an-agent.md). What comes back: [Situation package](guides/situation-package.md). Tool catalog: [MCP reference](reference/mcp.md).

### Cursor recipe shape

The recipe endpoint returns this shape. Do not commit `.cursor/mcp.json` — it contains a live token.

```json
{
  "mcpServers": {
    "personal-context-hub": {
      "command": "<python>",
      "args": ["-m", "agent_client", "mcp-bridge"],
      "env": {
        "PCH_TOKEN": "<connection-token>",
        "PCH_BASE": "http://127.0.0.1:8765"
      }
    }
  }
}
```

From a source checkout you can also run `make bridge TOKEN=...`.

## Optional: from source

If you are developing the Hub itself:

```bash
git clone <this-repo>
cd pch
make install
make serve
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [Architecture](architecture.md). The kernel, loopback service, SDK, and archive library are `trust-kernel`, `loopback-service`, `agent-client`, and `portable-state`.

## Check that it works

```bash
curl -s http://127.0.0.1:8765/health
# {"ok": true}
```

Interactive HTTP docs while the server is up: [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs).

## Troubleshooting

| Symptom | What to check |
|---|---|
| Hub refuses to start / SQLCipher | The vault uses SQLCipher. A plaintext vault opens only when `PCH_PLAIN_SQLITE=1`. |
| Non-loopback host rejected (exit 2) | The Hub binds `127.0.0.1` only. Do not pass `0.0.0.0`. |
| Assistant has no tools | Recipe `PCH_BASE` must match the running port; reload MCP; grant is separate from pairing. |
| Empty situation package | Grant selector vs project id; revoked connection. |
| Port already in use | Another process holds `8765`. Start `pch-server` with `--port 8766` and point `PCH_BASE` at that port. |

## Next

- [Architecture](architecture.md) — five primitives and package boundaries
- [Pair an agent](guides/pair-an-agent.md) — pairing link, recipe, grant
- [Security](security.md) — encryption, least privilege, reporting

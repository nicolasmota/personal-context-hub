# Personal Context

Personal Context is a local vault: one encrypted record of you on this device, and each paired agent receives a single [context contract](docs/spec/context-contract.md) — the smallest slice that is enough for the task you named.

The record stays here. The service, called the Hub, binds **loopback only** (`127.0.0.1`). Cursor and Hermes are validated MCP runtimes.

[![License: MIT](https://img.shields.io/badge/license-MIT-c9a227?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-1a1916?style=flat-square)](docs/getting-started.md)

## How a task gets context

| | |
|---|---|
| **You keep state** | Preferences, facts, experiences, and evidence live in `~/.personal-context`. A change is an explicit transition. |
| **You grant access** | Pairing gives an assistant a connection. A grant decides what that connection may see. |
| **The agent asks** | It calls `get_context_contract` with a purpose and a budget. |
| **One contract comes back** | Included items, withheld categories, conflicts, and traces. The rest of the vault stays put. |

The owner token is written to `owner.token` in the data directory, mode `0600`. HTTP never returns it.

## Quick start

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/). No account, and nothing leaves the machine.

```bash
make install
uv run personal-context vault-init --data-dir ~/.personal-context --name You
make serve
```

`make serve` listens on `http://127.0.0.1:8765`. Compile a contract without an agent:

```bash
uv run personal-context compile \
  --data-dir ~/.personal-context \
  --purpose "what is in play" \
  --budget 8
```

`uv run personal-context` is the owner command: proposals, grants, revoke, and import. Bring in a ChatGPT or Claude export with [Import memories](docs/guides/import-memories.md). Move the record with [Export and import](docs/guides/export-import.md).

## Pair an assistant

1. Start the Hub (`make serve`).
2. Mint a pairing link: `uv run personal-context link --data-dir ~/.personal-context --name Cursor`.
3. Paste the recipe into the assistant and attach a grant.

Full walkthrough: [Pair an agent](docs/guides/pair-an-agent.md). What the contract contains: [Situation package](docs/guides/situation-package.md).

## Repository

| Path | Role |
|---|---|
| `packages/trust-kernel` | Vault, schema, policy, and context compilation. No network I/O |
| `packages/loopback-service` | Loopback HTTP and pairing |
| `packages/agent-client` | Owner command line and MCP stdio bridge |
| `packages/portable-state` | Portable personal state export and import |
| `packages/eval-harness` | Scenarios, simulation, and the benchmark. Contributor tooling |

## Documentation

| | |
|---|---|
| Start | [Getting started](docs/getting-started.md) · [Pair an agent](docs/guides/pair-an-agent.md) · [CLI](docs/reference/cli.md) |
| Understand | [Architecture](docs/architecture.md) · [Context contract](docs/spec/context-contract.md) · [Security](docs/security.md) · [Non-goals](docs/non-goals.md) |
| Build | [Contributing](CONTRIBUTING.md) · [Developing](docs/develop.md) · [docs/](docs/README.md) · [llms.txt](docs/llms.txt) |

## Develop

```bash
make test
make lint
```

[CONTRIBUTING.md](CONTRIBUTING.md) · [Security](SECURITY.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [MIT](LICENSE)

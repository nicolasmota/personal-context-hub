# Personal Context Hub

Personal Context Hub is a local consent vault for personal context. One encrypted record stays on this device. Each paired agent receives only the slice you granted, compiled into one [context contract](docs/spec/context-contract.md). It is not a memory database and not an agent framework.

Your data lives on this device (default `~/.pch`), encrypted. The Hub binds **loopback only** (`127.0.0.1`) and is not a public server. Assistants connect over **MCP** and receive one context contract: the smallest sufficient slice for the task. Cursor and Hermes are validated MCP runtimes.

Plugins, provider connectors, the desktop shell, and the web interface are not part of this repository.

[![License: MIT](https://img.shields.io/badge/license-MIT-c9a227?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-1a1916?style=flat-square)](docs/getting-started.md)

**Documentation:** [Architecture](docs/architecture.md) · [Non-goals](docs/non-goals.md) · [Research](docs/research.md) · [Portable personal state](docs/guides/export-import.md) · [Evaluation harness](docs/develop.md) · [docs/](docs/README.md) · [llms.txt](docs/llms.txt) · **License:** [MIT](LICENSE)

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Code of Conduct](CODE_OF_CONDUCT.md)

---

## Install

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/). No Node toolchain, no external account, nothing leaves your device.

```bash
make install
uv run pch vault-init --data-dir /tmp/pch-demo --name Synthetic
uv run pch import-memories --data-dir /tmp/pch-demo --src ./memory.json --provider chatgpt
uv run pch compile --data-dir /tmp/pch-demo --purpose "what is in play" --budget 8
```

`uv run pch-sdk` and `uv run pch` are the same command. From a checkout, that command is the owner door: proposals, grants, revoke, and import. The loopback API never returns the owner token; it is written to `owner.token` in the data directory, mode `0600`.

`make serve` starts the loopback API on `127.0.0.1:8765`. Pair an assistant with the MCP bridge: [Pair an agent](docs/guides/pair-an-agent.md).

## Repository

| Path | Role |
|---|---|
| `packages/trust-kernel` | Personal state, experience, evidence, evolution, context compilation. No network I/O |
| `packages/loopback-service` | Loopback HTTP and pairing |
| `packages/agent-client` | Command line and MCP stdio bridge |
| `packages/eval-harness` | Evaluation harness and Speckit loop (contributor tooling) |
| `packages/portable-state` | Portable personal state export/import |

## From source

```bash
make install
make test
make lint
```

Full guide: [CONTRIBUTING.md](CONTRIBUTING.md).

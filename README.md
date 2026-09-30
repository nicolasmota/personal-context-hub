# Personal Context Hub

The hub maintains persistent personal state, evolves it from experience and evidence, and compiles the minimum sufficient context for the current situation. It is a local, user-owned context runtime for persistent agents. It is not a memory database.

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
uv run pch-sdk vault-init --data-dir /tmp/pch-demo --name Synthetic
uv run pch-sdk compile --data-dir /tmp/pch-demo --purpose "what is in play" --budget 8
```

`make serve` starts the loopback API on `127.0.0.1:8765`. Pair an assistant with the MCP bridge: [Pair an agent](docs/guides/pair-an-agent.md).

## Repository

| Path | Role |
|---|---|
| `packages/pch-core` | Personal state, experience, evidence, evolution, context compilation. No network I/O |
| `packages/pch-server` | Loopback HTTP and pairing |
| `packages/pch-sdk` | Command line and MCP stdio bridge |
| `packages/pch-lab` | Evaluation harness and Speckit loop (contributor tooling) |
| `packages/pch-archive` | Portable personal state export/import |

## From source

```bash
make install
make test
make lint
```

Full guide: [CONTRIBUTING.md](CONTRIBUTING.md).

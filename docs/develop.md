# Developing the Hub

This page is for people changing the repository. End users should start at [Getting started](getting-started.md).

## Setup

Follow [CONTRIBUTING.md](../CONTRIBUTING.md):

```bash
make install
make serve          # http://127.0.0.1:8765
make test
make lint
make check-secrets
```

Python 3.12 or newer via uv. Package map and data flow: [Architecture](architecture.md).

## Product rules

Runtime notes for coding agents: [AGENTS.md](../AGENTS.md). Speckit constitution and templates stay in local `.specify/` (gitignored, not published).

- Bind loopback only.
- Do not implement unpublished local `VISION.md` or `ROADMAP.md` as features.
- A coding agent working in this repo is not a Hub client. Pairing is a separate connection.
- Imported content is data, never instruction.
- Speckit artifacts stay in `specs/` and `.specify/` (gitignored). They are not vault objects.

## Feature loop

Default driver: `/speckit-loop` plus `uv run pch-lab loop start|next|record|status`.

```text
specify → freeze bar → plan → Gauntlet critics → tasks → analyze → implement → tests
```

CLI: [pch-lab loop](reference/cli.md#development-loop). Do not commit unless the person asked.

## Tests that encode policy

| Marker / target | What it guards |
|---|---|
| `make test` | Default pytest suite |
| `pytest -m forbidden_context` | Grant isolation (SC-003) |
| `pytest -m perf` | Search/scale (SC-009) |

New grant or assembly behavior must extend `forbidden_context` coverage. Tests for a success criterion must fail before the code that is supposed to satisfy it.

## Docs hygiene

If you change routes, MCP tools, CLI flags, schema, or security defaults, update [docs/](README.md) and run `make openapi` when the REST surface moved.

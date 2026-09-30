# Contributing

Thanks for helping with Personal Context Hub. This guide is for **from-source** work on the repository. End-user install and product docs live in the [README](README.md) and [docs/](docs/README.md).

## Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
make install          # uv sync
make serve            # loopback API with auto-reload
make test             # pytest
make lint             # ruff
make check-secrets    # fail if tracked paths match the secrets deny-list
make help             # all targets
```

## Pull requests

1. Keep changes focused; prefer one concern per PR.
2. Run `make check-secrets`, `make lint`, and `make test` before you push.
3. Use the PR template: short summary, test/lint evidence, and the no-secrets confirmation.
4. Do not implement unpublished local planning docs (`docs/VISION.md`, `docs/ROADMAP.md`) as features — spawn Speckit child specs instead.

## Must not commit

- Vault databases (`*.db`, `*.db-wal`, `*.db-shm`), `.pch/`, `.pch-sim/`, `.vault/`, `*.key`, `*.pca`
- `.env` / `.env.*`
- `google_oauth.json`
- Pairing token files
- `.cursor/mcp.json`

`make check-secrets` enforces this deny-list on tracked files.

## Documentation

When you change HTTP routes, MCP tools, CLI flags, schema, or security defaults, update the matching page under [docs/](docs/README.md) and regenerate OpenAPI with `make openapi` if the REST surface moved. Keep [docs/llms.txt](docs/llms.txt) and [docs/llms-full.txt](docs/llms-full.txt) aligned with those pages.

GitHub Pages publishes `docs/` from `main` (see `.github/workflows/pages.yml`). The social preview PNG is [docs/assets/social-preview.png](docs/assets/social-preview.png); regenerate it from [docs/assets/social-preview.html](docs/assets/social-preview.html). After the repository is public, also upload that PNG in **Settings → General → Social preview** (GitHub has no API for it).

## Before making the repository public

1. Run `make check-secrets` and confirm `docs/VISION.md`, `docs/ROADMAP.md`, `specs/`, and `.specify/` are still gitignored and untracked.
2. GitHub Pages is unavailable on a **private** repo on the free plan. After you switch visibility to public, enable **Settings → Pages → GitHub Actions** (the workflow already no-ops while private).
3. Upload the social preview image.
4. Submit MCP / agent directories only after the repository is public. Do not tag `v*` until you intend the release workflow to publish wheels.

## Project constraints (read once)

- **Local-first / loopback-only.** The Hub binds `127.0.0.1` only. It is not a public server.
- **Imported content is data, never instruction.** Email, calendar, and plugins do not expand grants or trigger outward actions.
- **A coding agent working on this repository is not a Hub client.** Vault pairing and MCP are a separate, explicit connection.

## Issues

Use the bug template. Never paste vault exports, tokens, OAuth client files, or editor MCP configs into issues.

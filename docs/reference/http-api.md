# HTTP API

The control plane is FastAPI on **loopback**, default `http://127.0.0.1:8765`.

| | |
|---|---|
| Health | `GET /health` → `{ "ok": true }` (no auth) |
| OpenAPI 3.1 | `GET /openapi.json` |
| Swagger UI | `GET /docs` |
| Checked-in dump | [openapi.json](../openapi.json) (regenerate with `make openapi`) |
| Product routes | `/v1/*` |

There is **no** `/v1/openapi.json`.

## Authentication

Send one of:

```http
Authorization: Bearer <token>
X-PCH-Token: <token>
```

| Actor | Token source | Can |
|---|---|---|
| Owner | `owner.token` in the data directory, or `pch token` | Full vault, pairing, and export |
| Connection | `POST /v1/connections/pair` | MCP tools and connection-scoped routes under its grants |

Missing or revoked → error (`Revoked`). Owner-only routes use `require_owner`.

Idempotency middleware is enabled on REST. Repeat a mutating request with the same idempotency header the client sent if you need safe retries.

`Hub.ask()` exists in `pch-core` but is **not** exposed as `/v1/ask`.

---

## Setup

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/v1/setup` | special | Body `{ "name"?: string, "restart"?: bool }`. The body does not include the owner token |
| `GET` | `/v1/setup` | none | `{ initialized, encrypted, key_storage }` |
| `GET` | `/v1/bootstrap` | none | `{ setup, sim_enabled, owner_credential }`. `owner_credential` is the filename `owner.token`, not the secret |
| `GET` | `/v1/spaces` | owner | `[{ "id": "personal", "kind": "personal" }]` |

---

## Situation (Home)

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/v1/situation` | owner | Live situation for Home. Empty vault → `{ "project": null, "contract": null }`. Assembles `get_context_contract` for the live project with purpose `what matters now`. |

---

## Projects and related

| Method | Path |
|---|---|
| `GET` `POST` | `/v1/projects` |
| `GET` `PATCH` `DELETE` | `/v1/projects/{id}` |
| `GET` | `/v1/projects/{id}/brief` |
| `GET` | `/v1/projects/{id}/versions` |
| `GET` `POST` | `/v1/goals` |
| `GET` `POST` | `/v1/commitments` |
| `GET` `POST` | `/v1/decisions` |

Optimistic concurrency: send `If-Match` with the version integer on patches that support it.

---

## Memories, artifacts, preferences, profile

| Method | Path |
|---|---|
| `GET` `POST` | `/v1/memories` |
| `GET` `PATCH` `DELETE` | `/v1/memories/{id}` |
| `POST` | `/v1/memories/{id}/supersede` |
| `POST` | `/v1/memories/{id}/retract` |
| `GET` | `/v1/memories/{id}/versions` |
| `GET` `POST` | `/v1/artifacts` |
| `GET` `POST` | `/v1/preferences` |
| `GET` `PATCH` | `/v1/preferences/{id}` |
| `POST` | `/v1/preferences/{id}/supersede` |
| `POST` | `/v1/preferences/{id}/retract` |
| `GET` | `/v1/profile` |

---

## Search

```http
GET /v1/search?q=Amsterdam&type=memory&project=<id>&classification=private&purpose=status_update&from=&to=
```

Query parameters: `q`, `type`, `project`, `classification`, `purpose`, `from`, `to` (date window on event start). Actor-scoped via grants.

---

## Pairing, grants, manifests

| Method | Path | Auth |
|---|---|---|
| `GET` | `/v1/catalog/assistants` | owner |
| `POST` | `/v1/connections/links` | owner — `{ "name" }` |
| `POST` | `/v1/connections/pair` | **code only** — `{ "code", "runtime_info"? }` |
| `GET` | `/v1/connections` | owner |
| `POST` | `/v1/connections/{id}/revoke` | owner |
| `POST` | `/v1/connections/{id}/recipe` | owner — `{ "assistant" }` |
| `POST` | `/v1/grants` | owner — `{ connection_id, preset?, capabilities?, selectors?, classification_ceiling }` |
| `GET` | `/v1/grants?connection=` | owner |
| `POST` | `/v1/grants/{id}/revoke` | owner |
| `POST` | `/v1/context-manifests` | **connection** |
| `GET` | `/v1/context-manifests/{id}` | granted actor |

Grant presets: `read_active_projects`, `read_project`, `always_ask_before_sending`. Default `classification_ceiling` is `private`.

Assistant ids: `cursor`, `claude-code`, `claude-desktop`, `chatgpt`, `hermes`, `openclaw`.

---

## Proposals, conflicts, relations

| Method | Path |
|---|---|
| `POST` `GET` | `/v1/memories/proposals` |
| `POST` | `/v1/memories/proposals/{id}/accept` `reject` |
| `GET` | `/v1/conflicts` |
| `POST` | `/v1/conflicts/{id}/resolve` |
| `POST` `GET` | `/v1/relations` |
| `PATCH` `DELETE` | `/v1/relations/{id}` |
| `GET` | `/v1/relation-proposals` |
| `POST` | `/v1/relation-proposals/{id}/accept` `reject` |

---

Outward actions, shared-state handoff, and operational-proposal routes are not part of this server.

---

## Audit

| Method | Path |
|---|---|
| `GET` | `/v1/events` |
| `GET` | `/v1/events/verify` |

---

## Export / import

| Method | Path |
|---|---|
| `POST` | `/v1/export` |
| `POST` | `/v1/import/stage` |
| `GET` | `/v1/import/staging/{id}` |
| `POST` | `/v1/import/staging/{id}/apply` |
| `POST` | `/v1/import/vendor` |
| `GET` | `/v1/import/vendor/{batch_id}` |
| `POST` | `/v1/import/vendor/{batch_id}/archive` |

See [Export and import](../guides/export-import.md).

---

## MCP over HTTP

| Method | Path |
|---|---|
| `POST` | `/v1/mcp/tools/{name}` — body = tool kwargs |
| `GET` | `/v1/mcp/resources?uri=` |

Tool names and bodies: [MCP tools](mcp.md).

---

## Simulator (dev)

When `PCH_SIM_ENABLED=1` or `pch serve --sim` (not on by default for `make serve`):

`/v1/sim/runs`, pause/resume/stop, ticks, `GET /v1/sim/objects/{id}`.

These routes load `pch-lab` only if that package is already installed (workspace). The published server does not depend on lab. Without it, sim routes stay 404.

The simulator is **test tooling**, not a product agent. Data it writes must be labeled as such. It must not act outward.

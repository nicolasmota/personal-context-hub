# MCP tools

The Hub exposes **five** tools over the stdio bridge (`personal-context mcp-bridge`) and over HTTP (`POST /v1/mcp/tools/{name}`).

Auth: connection token (`PERSONAL_CONTEXT_TOKEN`) or owner Bearer token. Policy is applied per actor. A revoked connection returns an error the bridge maps to *Connection revoked by the user in the Hub.*

Stdio also lists the `personal-context://situation` resource and the `runtime-rule` prompt. HTTP resources: [below](#resources).

## Catalog

| Tool | Required arguments | Role |
|---|---|---|
| `get_context_contract` | `purpose` | Situation package — start here |
| `search_personal_context` | `query`, `purpose` | Ranked hits inside the grant |
| `propose_memory` | `memory`, `evidence_refs` | Queue a memory; not live until accept |
| `propose_relation` | `from_id`, `to_id`, `relation_type` | Queue a typed edge |
| `get_context_manifest` | `purpose`, `requested_capabilities` | Ask for a short-lived capability receipt |

Shared-state handoff, outward actions, and operational-phase proposals are not tools.

Guide: [Situation package](../guides/situation-package.md). Capture rules: [Pair an agent](../guides/pair-an-agent.md#runtime-rule-paste-into-personal-guidance).

---

### `get_context_contract`

Assembles the smallest sufficient package for `purpose`.

```json
{
  "purpose": "continue planning the ten-day trip",
  "subject_ref": null,
  "max_items": null,
  "as_of": null
}
```

| Field | Type | Notes |
|---|---|---|
| `purpose` | string, minLength 1 | Required |
| `subject_ref` | string \| null | Project id |
| `max_items` | integer ≥ 1 \| null | Per-category cap; engine caps still apply |
| `as_of` | string \| null | ISO-8601 UTC instant; null = now |

Returns a [Context Contract](data-model.md#context-contract), including `sufficient` and `capture_hints` (propose durable facts; do not invent). Additional properties are rejected on the **request** bridge schema.

---

### `search_personal_context`

```json
{
  "query": "Amsterdam",
  "purpose": "status_update",
  "scope": { "project": "<project-id>", "types": ["memory"] }
}
```

`scope.project` and `scope.types` (first type only is applied today) are optional. Returns a search result dict (hits + policy metadata), not a contract.

---

### `get_context_manifest`

```json
{
  "purpose": "status_update",
  "requested_capabilities": ["project.read"],
  "selectors": { "project": "<project-id>" },
  "ttl_seconds": 900
}
```

Creates a time-boxed manifest of what this connection may see. Default TTL 900 seconds. HTTP twin for agents: `POST /v1/context-manifests` (connection actor only).

---

### `propose_memory`

```json
{
  "memory": {
    "kind": "semantic",
    "statement": "Amsterdam is the live city for the trip.",
    "project_id": "<project-id>"
  },
  "evidence_refs": [],
  "retention": null
}
```

If `retention` is set, it is merged into `memory`. The object is a **proposal**. Do not treat it as canonical. Do not propose guesses, demo fiction, or imported mail as orders.

Memory kinds: `semantic`, `episodic`, `procedural`, `summary`.

---

### `propose_relation`

```json
{
  "from_id": "<id>",
  "to_id": "<id>",
  "relation_type": "depends_on"
}
```

`relation_type`: `owned_by` | `depends_on` | `blocked_by` | `related_to`. Self-links are forbidden. Person accepts under `/v1/relation-proposals`.

---

## Resources (HTTP and stdio)

Stdio: `resources/read` on `personal-context://situation?purpose=<task>` returns the same contract as `get_context_contract`.

`GET /v1/mcp/resources?uri=`

`GET /v1/mcp/resources?uri=`

| URI contains | Payload |
|---|---|
| `/profile` | Profile + preferences |
| `/projects/{id}/brief` | Project brief |
| `/connection/self` or `/self` | Grants for this actor |
| `audit` | Audit events for this actor |

Python: `Client.resource(uri)`.

---

## Bridge environment

| Variable | Meaning |
|---|---|
| `PERSONAL_CONTEXT_TOKEN` | Connection token (`--token` overrides) |
| `PERSONAL_CONTEXT_BASE` | Hub base URL, default `http://127.0.0.1:8765` |

The stdio `serverInfo.version` is `0.2.0`. `prompts/get` with `runtime-rule` returns the capture rule.

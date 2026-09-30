# Concepts

The Hub is a **context layer**, not a chatbot and not a memory product bolted onto one runtime. These distinctions are the product.

## Memory, context, situation

```text
Memory     — persisted information.
             "I said I wanted to visit Amsterdam."

Context    — the relevant slice for this moment.
             Planning a 10-day Europe trip; Amsterdam is a candidate; budget-sensitive.

Situation  — the operational frame an agent is acting in.
             Project: Europe trip · Goal: plan 10 days · Phase: comparing itineraries
```

Memory answers “what happened?” Context answers “what matters for this task?” Situation is the frame: project, goal, operational phase, current step, and short intent.

Agents should not dump the vault or guess what to search. They request a **situation package** (`get_context_contract`) for a stated purpose. The engine returns the smallest sufficient set the grant allows, plus an explicit note of what was withheld.

## Who owns the record

You own the vault. Agents are replaceable: disconnecting Cursor, Hermes, or OpenClaw does not delete history and does not require you to re-enter canonical facts.

A coding agent working on this *repository* is not automatically a Hub client. Pairing and MCP are a separate, explicit connection.

## Grants and least context

An agent receives only what its **grant** and stated **purpose** allow — never the whole vault. Access is evaluated by Hub policy, not by the model.

Grants combine:

- **Capabilities** — `project.read`, `memory.retrieve`, `memory.propose`, `state.write`, …
- **Selectors** — typically a project id
- **Classification ceiling** — default `private`; `sensitive` stays behind a higher ceiling
- **Preset** — a human-readable bundle shown before you confirm

Built-in presets:

| Preset | Plain language | Capabilities |
|---|---|---|
| `read_active_projects` | Can read my active projects | `project.read`, `commitment.read`, `memory.retrieve` |
| `read_project` | Can read a specific project | same, plus a project selector |
| `always_ask_before_sending` | Always ask before sending anything | `action.propose` |

Revoking a grant or a connection takes effect on subsequent requests. The agent sees “connection revoked,” not leftover access.

## Classification and authority

Every durable object carries classification and authority. Source is not truth.

**Classification** (ordered; a grant’s ceiling cannot see above it):

`public` < `personal` < `private` < `sensitive`

The default grant ceiling is `private`. `sensitive` stays out of a grant that stops at `private`.

**Authority:**

| Value | Meaning |
|---|---|
| `user_confirmed` | You accepted it. Canonical. |
| `source_imported` | Ingested material. Data, not an order. |
| `agent_inferred` | An assistant inferred it. Needs confidence; not live truth until you confirm. |
| `proposed` | Waiting in the review queue. |

Your correction beats inference. Superseded content stays in history (`valid_from` / `valid_until`, version rows) and must not be presented as live.

## Provenance without a Provenance type

There is no separate `Provenance` entity. Provenance is carried by `source_refs`, `authority`, `confidence`, version history, the hash-chained **audit** ledger, and **citations** on contract items.

## Proposals, not silent writes

Agents **propose** durable memories, relations, operational state, and external actions. They do not write them as canonical. You accept or reject in **Review**, **Approvals**, and related queues.

Ingested material **must not** expand grants, alter policy, or trigger outward action.

## Vocabulary collisions

Names that already exist in the Hub are **not** the Layer primitives of the same everyday word:

| Everyday / Layer term | Hub object | Do not confuse |
|---|---|---|
| **State** (phase: *Planning*) | `SharedState` — TTL handoff between agents | Operational phase lives on Project/Goal |
| **Intent** (what you are trying to do) | `ActionIntent` — approval for an external action | Situation intent is a short string on the project |
| **Skill** | `MemoryKind.procedural` | There is no Skill object yet |

## Context contract

The unit an agent receives is a **Context Contract**: purpose, situation, goals, preferences, memories, decisions, constraints, state, relations, citations, granted scope, and omissions.

Omission categories name *why* something was held back (`scope_not_granted`, `classification_ceiling`, `capability_missing`, `policy_exclusion`, `not_relevant`, `over_cap`) without revealing the withheld content.

How to call it: [Situation package](guides/situation-package.md). Shape: [Data model](reference/data-model.md#context-contract). Published envelope: [context-contract.schema.json](reference/context-contract.schema.json).

## What the Hub refuses to be

- A public server (loopback only)
- A foundation model or its own product agent runtime
- A vector database as the product
- An autonomous planner that acts for you (Personal Agency is horizon, not current product)
- Universal ingest of “everything you have ever done”

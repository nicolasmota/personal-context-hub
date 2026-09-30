# Situation package

The situation package is the Hub’s answer to: *what does this agent need to know about this person, for this task, right now?*

The MCP tool is **`get_context_contract`**. HTTP equivalent: `POST /v1/mcp/tools/get_context_contract`.

The owner UI Home page uses **`GET /v1/situation`**: it picks the live (non-archived) project — preferring one with operational phase, step, or intent — and assembles the same contract with purpose `what matters now`. An empty vault returns `{ "project": null, "contract": null }`.

Do not confuse it with `get_context_manifest` (a short-lived capability receipt) or with `search_personal_context` (ranked hits). The contract is assembled context, not a search UI.

## When to call it

At the **start of a task** that depends on who the person is or what they are doing now. Pass `purpose` in their words, not a generic `"help"`.

If the package is empty, off-grant, or lists omissions, **say so**. Do not invent destinations, budgets, travelers, or preferences as Hub facts.

## Parameters

| Name | Required | Description |
|---|---|---|
| `purpose` | yes | What the agent is trying to do for the person right now. Non-empty after trim. |
| `subject_ref` | no | Project id to anchor the situation. |
| `max_items` | no | Optional per-category cap. Can only **lower** engine caps (memories 10, other item categories 20). Relations stay capped at 20. |
| `as_of` | no | UTC ISO-8601 instant for current vs historical. Omit or `null` means now. |

## Example

```python
from pch_sdk import Client

c = Client("http://127.0.0.1:8765", token="<connection-token>")
package = c.call(
    "get_context_contract",
    purpose="continue planning the ten-day trip",
    subject_ref=None,
)
print(package["situation"])
print(package["omissions"])
```

curl:

```bash
curl -s http://127.0.0.1:8765/v1/mcp/tools/get_context_contract \
  -H "Authorization: Bearer $PCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purpose":"continue planning the ten-day trip"}'
```

## What you get

A `ContextContract` object:

| Field | Role |
|---|---|
| `contract_id` | Id of this assembly |
| `purpose` | Echo of the request |
| `situation` | Anchored project: title, status, `operational_phase`, `current_step`, `situation_intent` |
| `candidates` | Other plausible situation frames |
| `goals`, `preferences`, `memories`, `decisions`, `constraints`, `state` | `ContractItem` lists with body, citation, authority, confidence, freshness, `untrusted` |
| `relations` | Typed edges: `owned_by`, `depends_on`, `blocked_by`, `related_to` |
| `references` | Extra ids the agent may follow up on |
| `conflicts` | Pairs the person has not resolved |
| `granted_scope` | Grant id, selectors, ceiling, capabilities, plain-language summary |
| `omissions` | Named withholdings — category + label + count, **not** the hidden content |
| `capture_hints` | What to do next (propose durable facts; do not invent). Not vault content. |
| `sufficient` | True only when every required current fact the grant allowed is in the main package. False if nothing is anchored. |
| `assembled_at` | Clock time of assembly |

Omission categories: `scope_not_granted`, `classification_ceiling`, `capability_missing`, `policy_exclusion`, `not_relevant` (off-task), `over_cap` (size). Overflow is a withheld count, not leftover identifiers on `references`.

Field-level schema: [Data model](../reference/data-model.md#context-contract). Published interchange (check without the Hub): [context-contract.schema.json](../reference/context-contract.schema.json).

## Killer demo (the bar)

Two authorized agents, one vault:

1. Agent A helps plan a trip. You confirm: two travelers, Amsterdam live, London dropped, budget-sensitive.
2. Agent B, with no transcript, asks only for the situation package with purpose “continue planning the trip.”
3. The contract contains the live city, travelers, and constraint — not the whole vault, and not London as current.

That portability is the point. Search hits alone are not enough.

## Related tools

After the contract:

- Durable facts the person just stated → `propose_memory` (not live until they accept, via `pch proposals`)
- Typed links → `propose_relation`

## Temporal reads

Pass `as_of` to ask “what was live at this instant?” Preferences and memories with `valid_from` / `valid_until` resolve to current vs historical. History is not deleted when a preference changes.

## Empty package

Common causes:

- No grant, or grant revoked
- Grant selector points at a different project than `subject_ref`
- Classification ceiling below the objects you expected (`sensitive` Gmail behind a `private` grant)
- Vault really has no matching live objects

Tell the person. Do not fill gaps from the model’s prior chats.

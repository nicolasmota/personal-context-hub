# Data model

All durable vault objects share **universal metadata**. Types are Pydantic models in `trust_kernel.schema`. There is no separate `Provenance` table — provenance is metadata + citations + audit.

## Universal metadata

| Field | Notes |
|---|---|
| `id` | ULID-style string |
| `space_id` | Default `"personal"` |
| `type` | `EntityType` |
| `labels` | Free tags |
| `classification` | `public` < `personal` < `private` < `sensitive` |
| `owner` | Person id |
| `created_at` `updated_at` | Instants |
| `source_refs` | Provenance pointers |
| `confidence` | Required when `authority=agent_inferred` |
| `authority` | `user_confirmed` \| `source_imported` \| `agent_inferred` \| `proposed` |
| `retention` | `{ mode: until_revoked \| review_after \| expires, at? }` |
| `policy_tags` | Extra policy labels |
| `version` | Integer; `GET /v1/…/versions` for history |

## Identity and profile

**Person** — `name`, `time_zone` (default `UTC`), `identities[]`.

**ContextSpace** — setup creates one personal space.

**Profile** — `contact_norms`, `working_hours`, `extra` (open dict).

## Preferences

`key`, `value`, `rationale`, `valid_from`, `valid_until`, `never_true`.

Changing a preference **supersedes** rather than silently overwriting. Use `as_of` on `get_context_contract` to read the past.

## Work objects

**Project** — `title`, `status` (`active` \| `paused` \| `done` \| `archived`), `charter`, `stakeholders[]`, plus operational fields:

- `operational_phase`: `planning` \| `deciding` \| `waiting` \| `executing` \| `other`
- `current_step` (≤ 200)
- `situation_intent` (≤ 200)

**Goal** — `title`, `outcome`, `horizon`, `measure`, `status` (`open` \| `done` \| `cancelled`), optional `project_id`, same operational fields.

**Commitment** — `title`, `due_at`, `counterparty`, `status` (`open` \| `done` \| `cancelled` \| `overdue`), optional `project_id` / `goal_id`.

**Decision** — `title`, `chosen_option`, `alternatives[]`, `rationale`, `decided_at`, optional `project_id`.

## Memories and artifacts

**Memory**

- `kind`: `semantic` \| `episodic` \| `procedural` \| `summary`
- `statement`
- `subject_ref`, `project_id`
- `sensitivity_flags`: `financial` \| `health` \| `legal` \| `relationship`
- `tombstone`, `valid_from`, `valid_until`, `never_true`

`procedural` is not a Skill object.

**Experience** — `action`, `operating_context`, `outcome`, `feedback`, `lesson`, `occurred_at`, `provenance`, optional `project_id`. `project_id` ties the episode to that project, which is the situation. Without it, the episode is not part of any situation's context. A repeated lesson becomes a proposal. It does not by itself change a preference or a memory.

**Artifact** — `kind`: `document` \| `message_thread` \| `conversation` \| `file` \| `url` \| `email`. Defaults `untrusted=true`. Email fields: `subject`, `sender`, `recipients`, `sent_at`, `body_text`.

**CalendarEvent** (`type=event`) — `title`, `starts_at`, `ends_at`, `all_day`, `location`, `attendees`, `calendar_id`, `status` (`confirmed` \| `tentative` \| `cancelled`), `source_key`. Default classification `private`.

## Graph

**Relation** — `from_id`, `to_id`, `relation_type` (`owned_by` \| `depends_on` \| `blocked_by` \| `related_to`), `status` (`live` \| `removed`). Self-links forbidden.

Agents submit **RelationProposal**; you accept or reject.

## Governance objects

| Type | Role |
|---|---|
| `connection` | Paired assistant |
| `grant` | Capabilities + selectors + classification ceiling |
| `manifest` | Time-boxed disclosure receipt |
| `proposal` / `operational_proposal` / `relation_proposal` | Waiting on you |
| `conflict` | Two live facts that disagree |
| `action_intent` | Proposed external action (`ActionIntent` — not situation intent) |
| `approval` | Your decision on an intent |
| `audit_event` | Hash-chained ledger row |
| `shared_state` | TTL handoff (`private_to_connection` \| `shared`) — not operational State |
| `export` / `import_staging` / `vendor_import_batch` | Portability |

Grant capabilities:

`project.read` · `commitment.read` · `memory.retrieve` · `memory.propose` · `state.write` · `state.share` · `action.propose` · `profile.read`

## Context contract

Returned by `Hub.get_context_contract` / `get_context_contract` MCP tool. Not stored as a vault entity type in `TYPE_MODELS`; it is an assembled view.

```text
ContextContract
  contract_id, purpose, assembled_at
  situation?: SituationRef          # project_id, title, status, phase, step, intent
  candidates[]                      # other SituationRef
  goals[] preferences[] memories[]
  decisions[] constraints[] state[] experiences[] # ContractItem
  relations[]                       # RelationRef (from / to ItemRef)
  references[]                      # ItemRef
  conflicts[]                       # item_ids + reason
  granted_scope                     # grant_id, selectors, ceiling, capabilities, summary_human
  omissions[]                       # category, label, count ≥ 1
  capture_hints[]                   # how to capture next, not vault facts
  sufficient                        # true only if anchored required facts that the grant allowed are inlined
```

**ContractItem** — `ref` (id, type, summary), `body`, `citation[]` (id, role, version), `authority`, `confidence`, `freshness`, `untrusted`.

**OmissionCategory** — `scope_not_granted` · `classification_ceiling` · `capability_missing` · `policy_exclusion` · `not_relevant` · `over_cap`.

Query object (`ContextQuery`): `purpose` (required), `subject_ref`, `max_items` ≥ 1, `as_of` UTC instant.

Published interchange a second implementer can check without this Hub: [context-contract.schema.json](context-contract.schema.json). Withheld notes are `{category, label, count}` only.

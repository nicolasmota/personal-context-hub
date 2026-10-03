# Architecture

The hub keeps user-owned personal state and compiles the minimum sufficient context for one situation. Domain rules live in `packages/trust-kernel`. Storage is the encrypted vault. Policy runs in the core before a contract is issued. Transport is the loopback service, the agent connection, and the command line. Those doors call the core. They do not reimplement selection.

Plugins, provider connectors, the desktop shell, and the web interface have been removed. They are not optional doors and they are not parked under an experimental tree.

## Five primitives

| Primitive | Role |
|---|---|
| Personal State | Versioned canonical record of the person: preferences, facts, and constraints, with validity and the transition that made each value live |
| Experience | A captured episode: action or observation, operating context, outcome, feedback, lesson, confidence, time, and provenance |
| Evidence | Support for a claim: source, authority, time, confidence, verification status, and provenance chain |
| State Evolution | An explicit transition from one canonical value to the next. A conditional exception keeps the unconditional preference |
| Context Compilation | One context contract for a grant, a task, and a budget: included items, sufficiency, withheld categories, conflict status, and traces |

Memory, context, and situation stay distinct. Memory is persisted information. The situation is the operational frame. The context contract is the compiled slice for that situation. A short-lived handoff between agents is not personal state.

## Packages

| Package | Boundary |
|---|---|
| `packages/trust-kernel` | Vault, schema, policy, and compilation. No network I/O |
| `packages/loopback-service` | Loopback HTTP and pairing. No plugin host and no provider connectors |
| `packages/agent-client` | Command line and MCP stdio bridge. No plugin toolkit |
| `packages/portable-state` | Portable personal state, format `0.2.0` |
| `packages/eval-harness` | Synthetic scenarios and the four-approach benchmark. Not a product agent |

The same contract is returned by `Hub.get_context_contract`, `POST /v1/mcp/tools/get_context_contract`, the MCP tool `get_context_contract`, and the resource `personal-context://situation`.

Relevance ranking is a `PurposeRetriever` on the hub. The default counts overlapping tokens. An embedding index or an external memory library can replace that object. Grants, omissions, authority, and the envelope stay in `trust-kernel`.

The normative envelope is [the context contract spec](spec/context-contract.md).

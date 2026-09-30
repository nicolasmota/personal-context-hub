# Research

Experiments use synthetic data by default. The benchmark does not need a winning score. It records the comparison.

`uv run pch-lab bench --out bench.json` runs seven scenario families against four baselines and writes one result row per pair.

## Baselines

| Approach | What it uses |
|---|---|
| `no_stored_context` | No stored personal state |
| `raw_retrieval` | The stored notes, uncompiled |
| `agent_owned_memory` | The experience list held by the agent |
| `pch` | This hub's compiled contract |

## Result fields

Each row records task success, context relevance, sufficiency, minimization, temporal accuracy, conflict handling, provenance accuracy, privacy leakage, token use, latency, and cost.

## Hypotheses

| Hypothesis | Scenario families | Baseline contrast | Metric |
|---|---|---|---|
| Persistent personal state improves long-horizon performance | `long_horizon`, `experience_reuse` | `pch` against `no_stored_context` and `agent_owned_memory` | task success, temporal accuracy |
| Compiled context is more effective than raw retrieval | `changing_preferences`, `stale_context`, `conflicting_memories` | `pch` against `raw_retrieval` | context relevance, sufficiency, conflict handling |
| User-owned context lets agents take turns on the same state | `cross_agent` | `pch` against `agent_owned_memory` | provenance accuracy, task success |
| State derived from experience improves later tasks | `experience_reuse`, `changing_preferences` | `pch` against `no_stored_context` | task success, temporal accuracy |
| Minimization can hold performance while reducing unnecessary exposure | `privacy` | `pch` against `raw_retrieval` | privacy leakage, minimization, sufficiency |

Scenario files live in `packages/pch-core/src/pch_core/testing/scenarios/`. The loopback tests load them from `pch_core.testing.scenarios` and do not import `pch_lab`.

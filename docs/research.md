# Research

Experiments use synthetic data by default. The scorer reads the rendered text. It does not treat the name `personal-context` as a success.

`uv run personal-context-lab bench --out bench.json` runs seven scenario families against four baselines and writes one result row per pair. `token_use` is `len(text) // 4`. `cost` stays 0 because this harness does not call a model. External memory libraries register a renderer on `eval_harness.baselines.runners.RENDERERS`; this repository does not ship their scores.

## Baselines

| Approach | What it uses |
|---|---|
| `no_stored_context` | No stored personal state |
| `raw_retrieval` | The stored notes, uncompiled |
| `agent_owned_memory` | The experience list held by the agent |
| `personal-context` | This hub's compiled contract |

## Result fields

Each row records task success, context relevance, sufficiency, minimization, temporal accuracy, conflict handling, provenance accuracy, privacy leakage, token use, latency, and cost. A required string that is missing, or a scenario secret that appears in the text, fails the row for every approach. Raw retrieval can therefore beat this hub on coverage and lose on leakage. That is the comparison.

## Hypotheses

| Hypothesis | Scenario families | Baseline contrast | Metric |
|---|---|---|---|
| Persistent personal state improves long-horizon performance | `long_horizon`, `experience_reuse` | `personal-context` against `no_stored_context` and `agent_owned_memory` | task success, temporal accuracy |
| Compiled context is more effective than raw retrieval | `changing_preferences`, `stale_context`, `conflicting_memories` | `personal-context` against `raw_retrieval` | context relevance, sufficiency, conflict handling |
| User-owned context lets agents take turns on the same state | `cross_agent` | `personal-context` against `agent_owned_memory` | provenance accuracy, task success |
| State derived from experience improves later tasks | `experience_reuse`, `changing_preferences` | `personal-context` against `no_stored_context` | task success, temporal accuracy |
| Minimization can hold performance while reducing unnecessary exposure | `privacy` | `personal-context` against `raw_retrieval` | privacy leakage, minimization, sufficiency |

Scenario files live in `packages/trust-kernel/src/trust_kernel/testing/scenarios/`. The loopback tests load them from `trust_kernel.testing.scenarios` and do not import `eval_harness`.

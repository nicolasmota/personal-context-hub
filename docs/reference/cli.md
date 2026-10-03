# CLI

Entry points from the workspace packages. Python 3.12 or newer via uv.

## `personal-context`

Local vault commands and the MCP bridge. From a checkout, after `make install`:

```bash
uv run personal-context vault-init --data-dir /tmp/personal-context-demo --name Synthetic
uv run personal-context experience-add --data-dir /tmp/personal-context-demo --action "noted a change" --context dinner --outcome recorded --at 2026-09-29T12:00:00Z --provenance owner
uv run personal-context evidence-add --data-dir /tmp/personal-context-demo --kind user_confirmed --source owner --authority "the person" --at 2026-09-29T12:00:00Z --statement "weekdays differ" --verification verified
uv run personal-context evolve --data-dir /tmp/personal-context-demo --subject food.spicy --value mild --reason "conditional exception" --condition weekdays
uv run personal-context compile --data-dir /tmp/personal-context-demo --purpose "plan dinner" --budget 8
uv run personal-context archive-export --data-dir /tmp/personal-context-demo --dest /tmp/state.personal-context --passphrase test
uv run personal-context archive-import --data-dir /tmp/personal-context-imported --src /tmp/state.personal-context --passphrase test
uv run personal-context mcp-bridge --token "$PERSONAL_CONTEXT_TOKEN" --base "$PERSONAL_CONTEXT_BASE"
uv run personal-context demo-agent --pair <code> --base http://127.0.0.1:8765 [--token]
```

`personal-context` does not run loop, sim, or eval. Use `personal-context-lab` for those.

Owner door, against a data directory (stop is not required; sqlite locks the short write):

```bash
uv run personal-context token --data-dir ~/.personal-context
uv run personal-context link --data-dir ~/.personal-context --name Cursor
uv run personal-context connections --data-dir ~/.personal-context
uv run personal-context grant --data-dir ~/.personal-context --connection <id> --preset read_project --project <project-id>
uv run personal-context revoke --data-dir ~/.personal-context --connection <id>
uv run personal-context proposals --data-dir ~/.personal-context list
uv run personal-context proposals --data-dir ~/.personal-context accept <proposal-id>
uv run personal-context proposals --data-dir ~/.personal-context reject <proposal-id>
uv run personal-context import-memories --data-dir ~/.personal-context --src ~/memory.json --provider chatgpt
uv run personal-context contract --data-dir ~/.personal-context --purpose "plan dinner" --budget 8
```

`contract` is `compile`. `import-memories` is documented in [Import memories](../guides/import-memories.md).

---

## `personal-context-server`

Headless API used by `make serve`:

```bash
uv run personal-context-server --reload --host 127.0.0.1 --port 8765 --data-dir ~/.personal-context
```

| Flag | Default |
|---|---|
| `--host` | `127.0.0.1` (non-loopback exits 2; `::1` coerced to `127.0.0.1`) |
| `--port` | `8765` |
| `--data-dir` | `~/.personal-context` |
| `--reload` / `--no-reload` | default **on** |

Factory `dev_app()` is the reload target for `personal-context-server`. Simulator and catalog refresh stay off unless `PERSONAL_CONTEXT_SIM_ENABLED=1` / `PERSONAL_CONTEXT_CATALOG_REFRESH=1`.

---

## `personal-context-lab`

Repository tooling. Not the user SDK.

### Development loop

```bash
uv run personal-context-lab loop start [--mode full|design-only] [--desc] [--epic] [--dir] [--roadmap] [--resume] [--redo STAGE]
uv run personal-context-lab loop next
uv run personal-context-lab loop record --stage specify --outcome pass|fail|blocked_on_person
uv run personal-context-lab loop record-verdict --critic A|B --verdict WIN|LOSE --round N [--failing …]
uv run personal-context-lab loop status
uv run personal-context-lab loop stop
uv run personal-context-lab loop evidence --command "pytest" --exit-code 0 --summary "…"
```

Default for new feature work: `/speckit-loop` plus this sequencer. It must not commit unless you asked, and must not treat VISION/ROADMAP as implementable features.

### Simulator harness

```bash
uv run personal-context-lab sim dump [--persona lived-stretch]
uv run personal-context-lab sim run [--persona] [--delay-ms] [--data-dir] [--target isolated|everyday] \
  [--confirm] [--paired-assistant] [--print-mcp-recipe] [--leave-proposals]
uv run personal-context-lab sim status [--data-dir]
```

`pause` / `resume` / `stop` print that those apply to the **server-hosted** simulator (`/v1/sim/runs`), not this CLI runner.

### Eval

```bash
uv run personal-context-lab eval run          # exit 1 if any case fails
```

---

## `personal-context-archive`

```bash
uv run personal-context-archive verify-roundtrip <src_hub_dir> <dst_hub_dir>
```

Compares listed object types between two data dirs. Export and import of portable personal state are `uv run personal-context archive-export` and `uv run personal-context archive-import`.

---

## Make targets

Run `make help`.

| Target | Meaning |
|---|---|
| `install` | `uv sync --all-packages` |
| `serve` | `personal-context-server --reload` |
| `test` / `test-forbidden` / `test-perf` / `test-all` / `test-dist` | pytest (`test-dist` is packaged wheel install) |
| `lint` / `format` | ruff |
| `check-secrets` | tracked-path deny-list |
| `openapi` | write `docs/openapi.json` |
| `demo-agent` | `CODE=` required |
| `bridge` | `TOKEN=` required |
| `dist` | wheels + `check_release.py` (no publish) |
| `release` | `dist` + publish |
| `clean` | caches and `.venv` |

Variables: `UV`, `PORT`, `HOST`, `DATA_DIR`.

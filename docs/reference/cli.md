# CLI

Entry points from the workspace packages. Python 3.12 or newer via uv.

## `pch-sdk`

Local vault commands and the MCP bridge. From a checkout, after `make install`:

```bash
uv run pch-sdk vault-init --data-dir /tmp/pch-demo --name Synthetic
uv run pch-sdk experience-add --data-dir /tmp/pch-demo --action "noted a change" --context dinner --outcome recorded --at 2026-09-29T12:00:00Z --provenance owner
uv run pch-sdk evidence-add --data-dir /tmp/pch-demo --kind user_confirmed --source owner --authority "the person" --at 2026-09-29T12:00:00Z --statement "weekdays differ" --verification verified
uv run pch-sdk evolve --data-dir /tmp/pch-demo --subject food.spicy --value mild --reason "conditional exception" --condition weekdays
uv run pch-sdk compile --data-dir /tmp/pch-demo --purpose "plan dinner" --budget 8
uv run pch-sdk archive-export --data-dir /tmp/pch-demo --dest /tmp/state.pch --passphrase test
uv run pch-sdk archive-import --data-dir /tmp/pch-imported --src /tmp/state.pch --passphrase test
uv run pch-sdk mcp-bridge --token "$PCH_TOKEN" --base "$PCH_BASE"
uv run pch-sdk demo-agent --pair <code> --base http://127.0.0.1:8765 [--token]
```

`pch-sdk` does not run loop, sim, or eval. Use `pch-lab` for those.

---

## `pch-server`

Headless API used by `make serve`:

```bash
uv run pch-server --headless --reload --host 127.0.0.1 --port 8765 --data-dir ~/.pch
```

| Flag | Default |
|---|---|
| `--headless` | off (flag exists for scripts; bind is always loopback) |
| `--host` | `127.0.0.1` (non-loopback exits 2; `::1` coerced to `127.0.0.1`) |
| `--port` | `8765` |
| `--data-dir` | `~/.pch` |
| `--reload` / `--no-reload` | default **on** |

Factory `dev_app()` is the reload target for `pch-server`. Simulator and catalog refresh stay off unless `PCH_SIM_ENABLED=1` / `PCH_CATALOG_REFRESH=1`.

---

## `pch-lab`

Repository tooling. Not the user SDK.

### Development loop

```bash
uv run pch-lab loop start [--mode full|design-only] [--desc] [--epic] [--dir] [--roadmap] [--resume] [--redo STAGE]
uv run pch-lab loop next
uv run pch-lab loop record --stage specify --outcome pass|fail|blocked_on_person
uv run pch-lab loop record-verdict --critic A|B --verdict WIN|LOSE --round N [--failing …]
uv run pch-lab loop status
uv run pch-lab loop stop
uv run pch-lab loop evidence --command "pytest" --exit-code 0 --summary "…"
```

Default for new feature work: `/speckit-loop` plus this sequencer. It must not commit unless you asked, and must not treat VISION/ROADMAP as implementable features.

### Simulator harness

```bash
uv run pch-lab sim dump [--persona lived-stretch]
uv run pch-lab sim run [--persona] [--delay-ms] [--data-dir] [--target isolated|everyday] \
  [--confirm] [--paired-assistant] [--print-mcp-recipe] [--leave-proposals]
uv run pch-lab sim status [--data-dir]
```

`pause` / `resume` / `stop` print that those apply to the **server-hosted** simulator (`/v1/sim/runs`), not this CLI runner.

### Eval

```bash
uv run pch-lab eval run          # exit 1 if any case fails
```

---

## `pch-archive`

```bash
uv run pch-archive verify-roundtrip <src_hub_dir> <dst_hub_dir>
```

Compares listed object types between two data dirs. Export and import of portable personal state are `uv run pch-sdk archive-export` and `uv run pch-sdk archive-import`.

---

## Make targets

Run `make help`.

| Target | Meaning |
|---|---|
| `install` | `uv sync --all-packages` |
| `serve` | `pch-server --headless --reload` |
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

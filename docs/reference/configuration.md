# Configuration

Nothing here is a cloud account. All paths are on the machine that runs the Hub.

## Data directory

Default: `~/.pch` (`$HOME/.pch`). Override with `--data-dir` or `PCH_DATA_DIR`.

| Path | Role |
|---|---|
| `vault.db` (+ `-wal` / `-shm`) | Encrypted SQLCipher vault (or plaintext if `PCH_PLAIN_SQLITE=1`) |
| `vault.key` | File fallback when the OS keyring is unused |
| `vault.salt` | Argon2id salt when unlocking with a passphrase |
| `blobs/` | Encrypted blob store |
| `exports/*.pca` | Portable personal state exports |
| `_sim/` | Simulator vault when nested under the data dir |

Keyring (when available): service `personal-context-hub`, account `vault-key`.

Related but separate:

| Path | Role |
|---|---|
| `~/.pch-sim` | Default isolated simulator dir (`PCH_SIM_DIR`) |
| `.cursor/mcp.json` | Editor MCP config — **do not commit** |

## Network

| Setting | Default | Constraint |
|---|---|---|
| Host | `127.0.0.1` | Loopback only; `localhost` accepted; `::1` coerced to `127.0.0.1` |
| Port | `8765` | `PCH_PORT` / `--port` |

## Environment

| Variable | Used by | Meaning |
|---|---|---|
| `PCH_DATA_DIR` | server | Vault directory |
| `PCH_PORT` | server | Listen port |
| `PCH_PLAIN_SQLITE` | vault open | `1` = allow unencrypted SQLite |
| `PCH_VAULT_KEY` | vault open | Hex key override |
| `PCH_TOKEN` | mcp-bridge | Connection token |
| `PCH_BASE` | mcp-bridge, demo-agent | Hub base URL |
| `PCH_SIM_ENABLED` | server | `1` = simulator routes |
| `PCH_SIM_DIR` | server | Simulator data dir |

## Secrets deny-list (git)

Never commit:

- Vault databases and sidecars, `.pch/`, `.pch-sim/`, `.vault/`, `*.key`, `*.pca`
- `.env` / `.env.*`
- `google_oauth.json`
- Pairing token files
- `.cursor/mcp.json`

`make check-secrets` fails the PR if tracked paths match. Speckit packs under `specs/` and `.specify/` are gitignored and must not be published.

# Export and import

Portable personal state is an encrypted archive of the person's vault: state, memories, evidence, transitions, conflicts, relations, and grants. The writer emits format `0.2.0`. Import accepts `0.2.0` as-is and migrates `0.1.0`. Any other version writes nothing.

Connection tokens and shared-state handoff rows stay out. A subset filter is refused.

```bash
uv run pch-sdk archive-export --data-dir "$PCH_DATA" --dest "$PCH_DATA/state.pch" --passphrase test
uv run pch-sdk archive-import --data-dir "$PCH_NEXT" --src "$PCH_DATA/state.pch" --passphrase test
```

## Owner HTTP

The same archive is available on loopback. Authenticate with the owner token from `owner.token` in the data directory.

```http
POST /v1/export
{ "passphrase": "…", "filters": {} }
```

`filters` is optional. The file is encrypted with [age](https://age-encryption.org/) when `pyrage` works; otherwise a `PCH1` + Fernet fallback (PBKDF2 480_000 iterations).

Inner zip layout (PCA generator version `0.2.0`):

```text
manifest.json                  # counts + sha256 integrity
objects/*.jsonl                # projects, goals, commitments, …
objects/versions.jsonl
events.jsonl                   # audit
interoperability/pam/memory-store.json
interoperability/ump/memories.ump.json
schemas/memory.schema.json
```

## Import over HTTP

```http
POST /v1/import/stage
GET  /v1/import/staging/{id}
POST /v1/import/staging/{id}/apply
```

Apply sends per-object resolutions (`ResolutionChoice`). Conflicts stay visible until you resolve them. Authority on imported rows is not silently upgraded to `user_confirmed`.

## Vendor import

Some foreign memory dumps can be queued without a PCA file:

```http
POST /v1/import/vendor
GET  /v1/import/vendor/{batch_id}
POST /v1/import/vendor/{batch_id}/archive
```

Treat vendor batches as untrusted until you archive/admit them. Do not paste other people’s exports into issues or chats.

## Round-trip check (developers)

The `pch-archive` tool compares two Hub data directories:

```bash
uv run pch-archive verify-roundtrip /path/to/src-hub /path/to/dst-hub
```

It lists `project`, `goal`, `commitment`, `decision`, `memory`, `preference`, `artifact`, and `profile` and compares `(id, authority, classification)`. Automated coverage: `packages/portable-state/tests/test_roundtrip.py`.

## What not to do

- Do not commit `*.pca` or vault databases
- Do not reuse an export passphrase in git or a password manager screenshot in a PR
- Do not expect pairing tokens to survive import — they are not in the archive

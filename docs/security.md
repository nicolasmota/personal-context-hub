# Security

The Hub is designed so a reachable non-loopback surface would already be a product bug. This page is the operator view. Vulnerability *reporting* is in [SECURITY.md](../SECURITY.md).

## Threat model (short)

| We assume | We do not assume |
|---|---|
| You control the machine that runs the Hub | The Hub is a public multi-tenant server |
| Assistants are untrusted guests | Models will faithfully respect grants |
| Ingested material is hostile input | Curation or “looks safe” is enforcement |
| Vault files on disk may be copied | Plaintext SQLite is acceptable by default |

Policy is evaluated in `trust-kernel`, outside any model’s reasoning.

## Loopback only

`pch-server` refuses a non-loopback `--host` (exit code 2). The message is: *The Hub is not a public server; it binds loopback only.*

Do not put a reverse proxy in front of `:8765` that listens on a LAN or public interface. That would make the Hub a public server.

## Encryption at rest

- Default vault: SQLCipher at `~/.pch/vault.db`
- Key: OS keyring (`personal-context-hub` / `vault-key`), or `vault.key`, or `PCH_VAULT_KEY` (hex), or Argon2id from a passphrase + `vault.salt`
- Blobs under `~/.pch/blobs/` use the same key
`pch-server` may open a plain database when the driver is missing and `plain=True` is used in tests. Do not treat that as the product default. Set `PCH_PLAIN_SQLITE=1` only when you accept an unencrypted vault.

## Tokens and pairing

| Token | Who has it | How you revoke it |
|---|---|---|
| Owner token | `owner.token` in the data directory (mode `0600`), or `pch token` | Re-setup is not a daily operation; treat the machine as trusted |
| Connection token | One paired assistant | **Agents → revoke**, or revoke the grant |

Send `Authorization: Bearer <token>` or `X-PCH-Token`. Missing or revoked tokens fail closed.

Never commit `.cursor/mcp.json`, pairing token files, `google_oauth.json`, `.env`, or vault databases. `make check-secrets` enforces a deny-list on tracked paths.

## Grants

Grants are shown in plain language before confirm, are revocable, and apply to subsequent MCP and HTTP calls from that connection. A classification ceiling keeps `sensitive` objects out of a `private` grant.

The `forbidden_context` pytest marker is the automated isolation gate. New grant or assembly behavior must extend it.

## Ingested material

This repository does not ship a plugin host, a provider connector, a desktop shell, or a web interface. Any ingested artifact is untrusted data: it must not expand grants, change policy, or act outward.

## Imported content is data

A portable-state import is a prompt-injection surface. It must not expand grants, alter policy, trigger actions, or be read as orders to the Hub or to an agent.

## Audit

Consequential reads, writes, proposals, approvals, grant changes, and export/import are recorded in an append-only, hash-chained ledger. `GET /v1/events/verify` checks the chain.

## Browser and DNS rebinding

Loopback does not stop the browser on this machine. `GET /v1/bootstrap` and `POST /v1/setup` do not return the owner token. The credential is a mode `0600` file named `owner.token` in the data directory. The HTTP app sends no `Access-Control-Allow-Origin` header. A request whose `Host` is not `127.0.0.1`, `localhost`, or `::1` is rejected with status 421, which closes the DNS-rebinding path that would otherwise make a public name resolve to the loopback port.

Earlier builds returned the owner token from `/v1/bootstrap` and allowed every origin. A page loaded in the same browser could read the token and then the vault. That response shape is gone.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting on this repository. Do not open a public issue with exploit details. Do not paste vault exports, tokens, or OAuth client files into issues or pull requests.

In scope: defects that leak context, weaken vault encryption, bind beyond loopback, or escalate grants; unsafe defaults in packaging, recipes, or docs that would cause someone to commit secrets.

## Related

- [Configuration](reference/configuration.md) — env vars and `~/.pch` layout
- [SECURITY.md](../SECURITY.md) — supported versions and reporting
- [AGENTS.md](../AGENTS.md) — loopback, grants, imported content is data

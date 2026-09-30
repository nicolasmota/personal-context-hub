# Security Policy

## Supported versions

Security fixes are accepted for:

- The `main` branch
- The latest published release tag

Older tags may not receive backports.

Operator-facing security model (encryption, grants, ingested material, loopback): [docs/security.md](docs/security.md).

## Reporting a vulnerability

Please report Hub **software** vulnerabilities through GitHub **Private Vulnerability Reporting** / Security Advisories on this repository.

Do **not** open a public issue with exploit details before a fix is available.

### In scope

- Defects in the Hub that could leak context, weaken vault encryption, bind beyond loopback, or escalate grants
- Unsafe defaults in packaging, recipes, or documentation that would cause someone to commit secrets

### Out of scope

- Asking for someone else's vault contents, pairing tokens, OAuth client files, or `.cursor/mcp.json`
- Pasting personal context exports into public issues or pull requests
- Social engineering against maintainers or contributors

If you accidentally paste secrets into a public thread, rotate them and ask maintainers to redact.

## Local secrets

Never commit:

- Vault databases (`*.db` and sidecars), `.pch/` / `.pch-sim/` data dirs, `.vault/`
- `.env` / `.env.*`
- `google_oauth.json`
- Pairing tokens
- `.cursor/mcp.json`

Run `make check-secrets` before opening a pull request, and again before changing repository visibility to public.

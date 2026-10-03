# pch-core

Trust kernel for Personal Context Hub: schema, encrypted vault, policy, retrieval, audit.

This package must not perform network I/O, serve HTTP, or import `pch-server` or `pch-sdk`. Local encrypted vault persistence is core's job.

Public façade: `from pch_core.service import Hub`.

Documentation: [Architecture](../../docs/architecture.md) · [Data model](../../docs/reference/data-model.md) · [Security](../../docs/security.md)

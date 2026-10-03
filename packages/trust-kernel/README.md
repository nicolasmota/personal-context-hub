# trust-kernel

Trust kernel for Personal Context Hub: schema, encrypted vault, policy, retrieval, audit.

This package must not perform network I/O, serve HTTP, or import `loopback-service` or `agent-client`. Local encrypted vault persistence is core's job.

Public façade: `from trust_kernel.service import Hub`.

Documentation: [Architecture](../../docs/architecture.md) · [Data model](../../docs/reference/data-model.md) · [Security](../../docs/security.md)

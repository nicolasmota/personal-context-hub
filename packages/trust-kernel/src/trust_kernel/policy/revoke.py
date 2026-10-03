from __future__ import annotations

from trust_kernel.schema.connection import ConnectionStatus
from trust_kernel.schema.grant import GrantStatus
from trust_kernel.schema.manifest import ManifestStatus
from trust_kernel.timeutil import now_iso
from trust_kernel.vault.objects import ObjectStore


def revoke_cascade(store: ObjectStore, connection_id: str) -> None:
    conn = store.get(connection_id)
    conn["status"] = ConnectionStatus.REVOKED
    conn["revoked_at"] = now_iso()
    store.put(conn)
    for grant in store.list("grant"):
        if grant.get("connection_id") == connection_id:
            grant["status"] = GrantStatus.REVOKED
            store.put(grant)
    for man in store.list("manifest"):
        if man.get("connection_id") == connection_id:
            man["status"] = ManifestStatus.INVALIDATED
            store.put(man)

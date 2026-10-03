from __future__ import annotations

from trust_kernel.timeutil import now_iso
from trust_kernel.vault.engine import Engine
from trust_kernel.vault.objects import ObjectStore


def sweep_expired(store: ObjectStore) -> int:
    count = 0
    now = now_iso()
    for row in store.list("shared_state"):
        exp = row.get("expires_at")
        if exp and exp < now:
            store.tombstone(row["id"])
            count += 1
    return count


def sweep_engine(engine: Engine) -> int:
    return sweep_expired(ObjectStore(engine))

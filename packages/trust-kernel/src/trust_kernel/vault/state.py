from __future__ import annotations

from pch_core.timeutil import now_iso
from pch_core.vault.engine import Engine
from pch_core.vault.objects import ObjectStore


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

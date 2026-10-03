#!/usr/bin/env python3
"""Build a pre-migration plain SQLite vault fixture for upgrade tests."""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

from trust_kernel.service import Hub


def _rewrite_prev(src: Path, dest: Path) -> None:
    shutil.copy2(src, dest)
    conn = sqlite3.connect(str(dest))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(objects)").fetchall()]
    keep = [c for c in cols if c != "source_key"]
    if "source_key" in cols:
        conn.execute("DROP INDEX IF EXISTS idx_objects_source_key")
        quoted = ", ".join(keep)
        conn.execute(f"CREATE TABLE objects_prev AS SELECT {quoted} FROM objects")
        conn.execute("DROP TABLE objects")
        conn.execute("ALTER TABLE objects_prev RENAME TO objects")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_project ON objects(project_id)")
    conn.execute("DELETE FROM kv WHERE k = 'schema_version'")
    conn.commit()
    conn.close()


def build(dest: Path) -> None:
    work = dest.parent / "_prev_build"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    hub = Hub(work, plain=True)
    hub.setup("Fixture")
    for i in range(10):
        hub.create("project", {"title": f"Project {i}", "charter": "c", "status": "active"})
    for i in range(4):
        hub.create("memory", {"statement": f"Memory {i}", "kind": "semantic"})
    first = hub.pair(hub.mint_link("alpha")["code"], {"runtime": "alpha"})
    second = hub.pair(hub.mint_link("beta")["code"], {"runtime": "beta"})
    hub.create_grant(
        first["connection_id"],
        None,
        ["memory.retrieve", "profile.read"],
        {},
        "private",
    )
    hub.create_grant(first["connection_id"], None, ["project.read"], {}, "private")
    hub.create_grant(second["connection_id"], None, ["profile.read"], {}, "private")
    objects = hub.engine.conn.execute("SELECT count(*) AS n FROM objects").fetchone()["n"]
    if objects < 20:
        for i in range(20 - objects):
            hub.create("memory", {"statement": f"Pad {i}", "kind": "semantic"})
    hub.engine.conn.commit()
    src = work / "vault.db"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _rewrite_prev(src, dest)
    hub.close()
    shutil.rmtree(work)
    check = sqlite3.connect(str(dest))
    cols = {row[1] for row in check.execute("PRAGMA table_info(objects)").fetchall()}
    assert "source_key" not in cols
    assert check.execute("SELECT v FROM kv WHERE k='schema_version'").fetchone() is None
    check.close()
    print(f"wrote {dest}")


if __name__ == "__main__":
    out = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1]
        / "packages/trust-kernel/tests/fixtures/vault_prev.sqlite"
    )
    build(out)

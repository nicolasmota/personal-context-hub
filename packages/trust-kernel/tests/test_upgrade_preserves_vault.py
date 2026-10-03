import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from pch_core.audit.ledger import Ledger
from pch_core.vault.engine import MIGRATIONS, Engine

FIXTURE = Path(__file__).parent / "fixtures" / "vault_prev.sqlite"


def _rows(conn, sql: str) -> list[dict]:
    return list(conn.execute(sql).fetchall())


def _canonical(rows: list[dict], skip: set[str] | None = None) -> str:
    skip = skip or set()
    payload = []
    for row in rows:
        item = {k: row[k] for k in row.keys() if k not in skip}
        payload.append(item)
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_upgrade_preserves_vault(tmp_path: Path):
    assert FIXTURE.exists(), "run scripts/make_prev_vault.py"
    dest = tmp_path / "vault.db"
    shutil.copy2(FIXTURE, dest)
    prev = sqlite3.connect(str(dest))
    prev.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    obj_hash = _sha(_canonical(_rows(prev, "SELECT id, json FROM objects ORDER BY id")))
    ver_hash = _sha(_canonical(_rows(prev, "SELECT id, version, json FROM object_versions ORDER BY id, version")))
    ev_hash = _sha(_canonical(_rows(prev, "SELECT seq, kind, actor, refs, summary_human, prev_hash, hash, created_at, extra FROM events ORDER BY seq")))
    conn_hash = _sha(
        _canonical(_rows(prev, "SELECT id, json FROM objects WHERE type='connection' ORDER BY id"))
    )
    kv_hash = _sha(_canonical(_rows(prev, "SELECT k, v FROM kv WHERE k != 'schema_version' ORDER BY k")))
    obj_n = prev.execute("SELECT count(*) AS n FROM objects").fetchone()["n"]
    ver_n = prev.execute("SELECT count(*) AS n FROM object_versions").fetchone()["n"]
    ev_n = prev.execute("SELECT count(*) AS n FROM events").fetchone()["n"]
    conn_n = prev.execute("SELECT count(*) AS n FROM objects WHERE type='connection'").fetchone()["n"]
    prev.close()

    engine = Engine(dest, b"0" * 32, plain=True)
    assert engine._schema_version() == max(n for n, _ in MIGRATIONS)
    ledger = Ledger(engine)
    assert ledger.verify()["ok"] is True
    after_obj = _sha(_canonical(_rows(engine.conn, "SELECT id, json FROM objects ORDER BY id")))
    after_ver = _sha(
        _canonical(_rows(engine.conn, "SELECT id, version, json FROM object_versions ORDER BY id, version"))
    )
    after_ev = _sha(
        _canonical(
            _rows(
                engine.conn,
                "SELECT seq, kind, actor, refs, summary_human, prev_hash, hash, created_at, extra FROM events ORDER BY seq",
            )
        )
    )
    after_conn = _sha(
        _canonical(_rows(engine.conn, "SELECT id, json FROM objects WHERE type='connection' ORDER BY id"))
    )
    after_kv = _sha(
        _canonical(_rows(engine.conn, "SELECT k, v FROM kv WHERE k != 'schema_version' ORDER BY k"))
    )
    assert engine.conn.execute("SELECT count(*) AS n FROM objects").fetchone()["n"] == obj_n
    assert engine.conn.execute("SELECT count(*) AS n FROM object_versions").fetchone()["n"] == ver_n
    assert engine.conn.execute("SELECT count(*) AS n FROM events").fetchone()["n"] == ev_n
    assert engine.conn.execute("SELECT count(*) AS n FROM objects WHERE type='connection'").fetchone()["n"] == conn_n
    assert after_obj == obj_hash
    assert after_ver == ver_hash
    assert after_ev == ev_hash
    assert after_conn == conn_hash
    assert after_kv == kv_hash
    engine.close()

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    from sqlcipher3 import dbapi2 as sqlcipher
except Exception:
    sqlcipher = None  # type: ignore[assignment]

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
  id TEXT PRIMARY KEY,
  space_id TEXT NOT NULL,
  type TEXT NOT NULL,
  project_id TEXT,
  classification TEXT,
  authority TEXT,
  version INTEGER NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0,
  json TEXT NOT NULL,
  search_text TEXT,
  created_at TEXT,
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type);
CREATE INDEX IF NOT EXISTS idx_objects_project ON objects(project_id);

CREATE VIRTUAL TABLE IF NOT EXISTS objects_fts USING fts5(
  id UNINDEXED,
  search_text
);

CREATE TABLE IF NOT EXISTS object_versions (
  id TEXT NOT NULL,
  version INTEGER NOT NULL,
  json TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  PRIMARY KEY (id, version)
);

CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  refs TEXT NOT NULL,
  summary_human TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  extra TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS kv (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency (
  key TEXT PRIMARY KEY,
  status INTEGER NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def dict_row(cursor, row):
    """Driver-agnostic mapping; sqlite3.Row cannot wrap a SQLCipher cursor."""
    if not cursor.description:
        return {}
    return {col[0]: value for col, value in zip(cursor.description, row, strict=False)}


class _BufferedCursor:
    def __init__(self, rows: list[Any], lastrowid: int | None) -> None:
        self._rows = rows
        self._index = 0
        self.lastrowid = lastrowid

    def fetchone(self) -> Any:
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def fetchall(self) -> list[Any]:
        rest = self._rows[self._index :]
        self._index = len(self._rows)
        return rest

    def __iter__(self) -> Iterator[Any]:
        return iter(self.fetchall())


class SerializedConnection:
    """One sqlite connection is not safe across FastAPI's threadpool without a lock."""

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock) -> None:
        self._conn = conn
        self._lock = lock

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> _BufferedCursor:
        with self._lock:
            cursor = self._conn.execute(sql, parameters)
            rows = cursor.fetchall()
            return _BufferedCursor(rows, cursor.lastrowid)

    def executescript(self, sql: str) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executescript(sql)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def rollback(self) -> None:
        with self._lock:
            self._conn.rollback()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @property
    def in_transaction(self) -> bool:
        return bool(getattr(self._conn, "in_transaction", False))

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value) -> None:
        self._conn.row_factory = value


def cipher_available() -> bool:
    return sqlcipher is not None


def _connect_sqlcipher(path: Path, key: bytes):
    if sqlcipher is None:
        raise RuntimeError("sqlcipher3 is not available")
    conn = sqlcipher.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = dict_row
    conn.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
    conn.execute("PRAGMA cipher_compatibility = 4")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _connect_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = dict_row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _m1_add_source_key(conn: SerializedConnection) -> None:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(objects)").fetchall()}
    if "source_key" not in cols:
        conn.execute("ALTER TABLE objects ADD COLUMN source_key TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_objects_source_key "
        "ON objects(source_key) WHERE source_key IS NOT NULL AND source_key != ''"
    )


MIGRATIONS: list[tuple[int, Callable[[SerializedConnection], None]]] = [
    (1, _m1_add_source_key),
]


class Engine:
    def __init__(self, path: Path, key: bytes, *, plain: bool | None = None) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        use_plain = plain if plain is not None else os.environ.get("PCH_PLAIN_SQLITE") == "1"
        if use_plain:
            raw = _connect_sqlite(path)
            self.encrypted = False
        else:
            raw = _connect_sqlcipher(path, key)
            self.encrypted = True
            raw.execute("SELECT count(*) FROM sqlite_master").fetchone()
        raw.row_factory = dict_row
        self.conn = SerializedConnection(raw, self._lock)
        self._tx_depth = 0
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _schema_version(self) -> int:
        row = self.conn.execute("SELECT v FROM kv WHERE k = ?", ("schema_version",)).fetchone()
        if row is None:
            return 0
        try:
            return int(row["v"])
        except (TypeError, ValueError):
            return 0

    def _set_schema_version(self, version: int) -> None:
        self.conn.execute(
            "INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            ("schema_version", str(version)),
        )

    def _migrate(self) -> None:
        current = self._schema_version()
        for version, fn in MIGRATIONS:
            if version > current:
                fn(self.conn)
                self._set_schema_version(version)
                current = version

    @contextmanager
    def tx(self) -> Iterator[SerializedConnection]:
        with self._lock:
            nested = self._tx_depth > 0
            self._tx_depth += 1
            savepoint = f"pch_{self._tx_depth}"
            try:
                if nested:
                    self.conn.execute(f"SAVEPOINT {savepoint}")
                else:
                    self.conn.execute("BEGIN")
                yield self.conn
                if nested:
                    self.conn.execute(f"RELEASE {savepoint}")
                else:
                    self.conn.commit()
            except Exception:
                if nested:
                    self.conn.execute(f"ROLLBACK TO {savepoint}")
                    self.conn.execute(f"RELEASE {savepoint}")
                else:
                    self.conn.rollback()
                raise
            finally:
                self._tx_depth -= 1

    def close(self) -> None:
        self.conn.close()

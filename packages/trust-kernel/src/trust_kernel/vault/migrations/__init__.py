"""Alembic placeholder — canonical DDL lives in engine.SCHEMA and is applied on connect."""

from pch_core.vault.engine import SCHEMA


def upgrade(conn) -> None:
    conn.executescript(SCHEMA)

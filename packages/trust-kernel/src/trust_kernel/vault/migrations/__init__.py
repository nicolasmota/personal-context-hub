"""Alembic placeholder — canonical DDL lives in engine.SCHEMA and is applied on connect."""

from trust_kernel.vault.engine import SCHEMA


def upgrade(conn) -> None:
    conn.executescript(SCHEMA)

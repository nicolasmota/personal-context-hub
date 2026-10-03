"""Initial schema (idempotent)."""

revision = "0001_initial"
down_revision = None


def upgrade(conn) -> None:
    from pch_core.vault.engine import SCHEMA

    conn.executescript(SCHEMA)


def downgrade(conn) -> None:
    raise RuntimeError("no downgrade for encrypted personal vault")

from __future__ import annotations

import secrets

from pch_core.service import Hub


def mint(hub: Hub, name: str = "agent") -> dict:
    return hub.mint_link(name)


def redeem(hub: Hub, code: str, runtime_info: dict | None = None) -> dict:
    return hub.pair(code, runtime_info)


def random_code() -> str:
    return secrets.token_urlsafe(16)

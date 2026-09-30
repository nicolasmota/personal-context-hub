from __future__ import annotations

import os
from pathlib import Path

OWNER_TOKEN_NAME = "owner.token"


def write_owner_token(data_dir: Path, token: str) -> Path:
    """Store the owner credential where a browser cannot read it.

    Mode 0600 on the vault directory. HTTP handlers must not return this value.
    """
    path = data_dir / OWNER_TOKEN_NAME
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, token.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, 0o600)
    return path

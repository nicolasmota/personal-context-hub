from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw

SERVICE = "personal-context-hub"
ACCOUNT = "vault-key"


def derive_key(passphrase: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        passphrase.encode("utf-8"),
        salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )


def random_key() -> bytes:
    return secrets.token_bytes(32)


def load_or_create_key(data_dir: Path, passphrase: str | None = None) -> bytes:
    env = os.environ.get("PCH_VAULT_KEY")
    if env:
        return bytes.fromhex(env)
    salt_path = data_dir / "vault.salt"
    data_dir.mkdir(parents=True, exist_ok=True)
    if passphrase:
        if salt_path.exists():
            salt = salt_path.read_bytes()
        else:
            salt = secrets.token_bytes(16)
            salt_path.write_bytes(salt)
        return derive_key(passphrase, salt)
    try:
        import keyring

        stored = keyring.get_password(SERVICE, ACCOUNT)
        if stored:
            return bytes.fromhex(stored)
        key = random_key()
        keyring.set_password(SERVICE, ACCOUNT, key.hex())
        return key
    except Exception:
        fallback = data_dir / "vault.key"
        if fallback.exists():
            return bytes.fromhex(fallback.read_text().strip())
        key = random_key()
        fallback.write_text(key.hex())
        os.chmod(fallback, 0o600)
        return key


def fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def key_storage(data_dir: Path) -> str:
    if (data_dir / "vault.key").exists():
        return "file"
    return "keychain"

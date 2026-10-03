from __future__ import annotations

import hashlib
import os
import secrets
import sys
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw

from trust_kernel.errors import VaultKeyError

SERVICE = "personal-context"
ACCOUNT = "vault-key"
_CANNOT_OPEN = "This record cannot be opened. No available key unlocks it."


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


def directory_account(data_dir: Path) -> str:
    digest = hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()[:32]
    return f"vault-key:{digest}"


def load_or_create_key(data_dir: Path, passphrase: str | None = None) -> bytes:
    env = os.environ.get("PERSONAL_CONTEXT_VAULT_KEY")
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

    db = data_dir / "vault.db"
    file_key = _read_file_key(data_dir)
    own_key = _ring_get(directory_account(data_dir))
    if db.is_file() and db.stat().st_size > 0:
        for candidate in (file_key, own_key):
            if candidate is not None and _opens(db, candidate):
                return candidate
        if file_key is None and own_key is None:
            legacy = _ring_get(ACCOUNT)
            if legacy is not None and _opens(db, legacy):
                if not _ring_set(directory_account(data_dir), legacy):
                    _write_file_key(data_dir, legacy)
                return legacy
        raise VaultKeyError(_CANNOT_OPEN)

    if file_key is not None:
        return file_key
    if own_key is not None:
        return own_key
    key = random_key()
    if not _ring_set(directory_account(data_dir), key):
        _write_file_key(data_dir, key)
    return key


def announce_file_key(data_dir: Path) -> None:
    if key_storage(data_dir) != "file":
        return
    path = data_dir / "vault.key"
    print(f"Vault key is in a file beside the record ({path}), mode 0600.", file=sys.stderr)


def fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def key_storage(data_dir: Path) -> str:
    if (data_dir / "vault.key").exists():
        return "file"
    return "keychain"


def _opens(db: Path, key: bytes) -> bool:
    from trust_kernel.vault.engine import key_opens

    return key_opens(db, key)


def _read_file_key(data_dir: Path) -> bytes | None:
    fallback = data_dir / "vault.key"
    if not fallback.is_file():
        return None
    try:
        return bytes.fromhex(fallback.read_text().strip())
    except ValueError:
        return None


def _write_file_key(data_dir: Path, key: bytes) -> None:
    fallback = data_dir / "vault.key"
    fallback.write_text(key.hex())
    os.chmod(fallback, 0o600)


def _ring_get(account: str) -> bytes | None:
    try:
        import keyring

        stored = keyring.get_password(SERVICE, account)
    except Exception:
        return None
    if not stored:
        return None
    try:
        return bytes.fromhex(stored.strip())
    except ValueError:
        return None


def _ring_set(account: str, key: bytes) -> bool:
    try:
        import keyring

        keyring.set_password(SERVICE, account, key.hex())
    except Exception:
        return False
    return True

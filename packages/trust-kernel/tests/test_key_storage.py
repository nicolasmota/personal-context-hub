import sys
from pathlib import Path

import pytest
from trust_kernel.errors import PclError
from trust_kernel.service import Hub
from trust_kernel.vault.engine import Engine
from trust_kernel.vault.keys import SERVICE, key_storage, load_or_create_key, random_key


class FakeRing:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, account: str) -> str | None:
        return self.store.get((service, account))

    def set_password(self, service: str, account: str, password: str) -> None:
        self.store[(service, account)] = password


def test_key_storage_file_when_vault_key_exists(tmp_path: Path):
    (tmp_path / "vault.key").write_text("ab")
    assert key_storage(tmp_path) == "file"


def test_key_storage_keychain_otherwise(tmp_path: Path):
    assert key_storage(tmp_path) == "keychain"


def _block_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "keyring":
            raise OSError("no keyring")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded)


def test_file_key_beats_a_later_keyring_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _block_keyring(monkeypatch)
    hub = Hub(tmp_path, plain=False)
    file_key = (tmp_path / "vault.key").read_text().strip()
    hub.close()
    monkeypatch.undo()
    ring = FakeRing()
    ring.store[(SERVICE, "vault-key")] = random_key().hex()
    monkeypatch.setitem(sys.modules, "keyring", ring)
    opened = load_or_create_key(tmp_path)
    assert opened.hex() == file_key
    Hub(tmp_path, plain=False).close()


def test_two_directories_keep_separate_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ring = FakeRing()
    monkeypatch.setitem(sys.modules, "keyring", ring)
    Hub(tmp_path / "a", plain=False).close()
    Hub(tmp_path / "b", plain=False).close()
    accounts = {account for (_service, account) in ring.store}
    assert len(accounts) == 2
    assert "vault-key" not in accounts


def test_legacy_key_is_copied_and_not_deleted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    key = random_key()
    engine = Engine(tmp_path / "vault.db", key, plain=False)
    engine.close()
    ring = FakeRing()
    ring.store[(SERVICE, "vault-key")] = key.hex()
    monkeypatch.setitem(sys.modules, "keyring", ring)
    assert load_or_create_key(tmp_path) == key
    assert ring.store[(SERVICE, "vault-key")] == key.hex()
    own = [account for (_service, account) in ring.store if account != "vault-key"]
    assert len(own) == 1

    other = tmp_path / "second"
    engine = Engine(other / "vault.db", key, plain=False)
    engine.close()
    assert load_or_create_key(other) == key
    assert ring.store[(SERVICE, "vault-key")] == key.hex()


def test_missing_key_leaves_the_vault_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    key = random_key()
    engine = Engine(tmp_path / "vault.db", key, plain=False)
    engine.close()
    before = (tmp_path / "vault.db").read_bytes()
    ring = FakeRing()
    ring.get_password = lambda _service, _account: random_key().hex()  # type: ignore[method-assign]
    monkeypatch.setitem(sys.modules, "keyring", ring)
    with pytest.raises(PclError, match="cannot be opened"):
        load_or_create_key(tmp_path)
    assert (tmp_path / "vault.db").read_bytes() == before

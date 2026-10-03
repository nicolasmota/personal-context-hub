from pathlib import Path

from pch_core.vault.keys import key_storage


def test_key_storage_file_when_vault_key_exists(tmp_path: Path):
    (tmp_path / "vault.key").write_text("ab")
    assert key_storage(tmp_path) == "file"


def test_key_storage_keychain_otherwise(tmp_path: Path):
    assert key_storage(tmp_path) == "keychain"

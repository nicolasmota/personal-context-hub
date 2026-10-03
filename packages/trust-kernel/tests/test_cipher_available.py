from pathlib import Path

import pytest
from pch_core.vault.engine import Engine, cipher_available


def test_cipher_available_true_when_import_works():
    assert cipher_available() is True


def test_cipher_available_false_when_import_fails(monkeypatch):
    import pch_core.vault.engine as engine

    monkeypatch.setattr(engine, "sqlcipher", None)
    assert engine.cipher_available() is False


def test_engine_refuses_plaintext_when_cipher_missing(tmp_path: Path, monkeypatch):
    import pch_core.vault.engine as engine

    monkeypatch.setattr(engine, "sqlcipher", None)
    monkeypatch.delenv("PCH_PLAIN_SQLITE", raising=False)
    with pytest.raises(RuntimeError, match="sqlcipher3"):
        Engine(tmp_path / "vault.db", b"0" * 32, plain=False)

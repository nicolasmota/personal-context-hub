from __future__ import annotations

from pathlib import Path

import pytest
from pch_core.service import Hub
from pch_lab.sim import SimRefused, run_sim


def test_everyday_vault_unchanged(tmp_path: Path) -> None:
    everyday = tmp_path / "everyday"
    sim = tmp_path / "sim"
    eh = Hub(everyday, plain=True)
    try:
        eh.setup("Owner")
        eh.create("memory", {"statement": "real life note"})
        before = len(eh.list("memory"))
    finally:
        eh.close()
    run_sim(data_dir=sim, delay_ms=0, everyday_dir=everyday, target="isolated")
    eh = Hub(everyday, plain=True)
    try:
        assert len(eh.list("memory")) == before
    finally:
        eh.close()


def test_everyday_refused_without_confirm(tmp_path: Path) -> None:
    with pytest.raises(SimRefused) as exc:
        run_sim(
            data_dir=tmp_path / "sim",
            delay_ms=0,
            target="everyday",
            confirm="",
            everyday_dir=tmp_path / "everyday",
        )
    assert exc.value.reason == "everyday_unconfirmed"

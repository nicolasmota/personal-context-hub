from __future__ import annotations

import time
from pathlib import Path

from pch_core.service import Hub
from pch_lab.sim import run_sim


def test_first_tick_under_two_minutes(tmp_path: Path) -> None:
    t0 = time.perf_counter()
    run = run_sim(data_dir=tmp_path / "sim", delay_ms=0)
    elapsed = time.perf_counter() - t0
    assert elapsed < 120
    assert int(run["current_seq"]) >= 1
    assert run["status"] == "complete"


def test_lived_stretch_volume(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run = run_sim(data_dir=data_dir, delay_ms=0)
    assert run["object_count"] >= 40
    assert run["query_count"] >= 10
    hub = Hub(data_dir, plain=True)
    try:
        kinds = {row["type"] for row in hub.list()}
        assert {"project", "preference", "memory"}.issubset(kinds)
        assert kinds & {"goal", "commitment", "decision"}
    finally:
        hub.close()

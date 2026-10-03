from __future__ import annotations

from pathlib import Path

from pch_core.service import Hub
from pch_lab.sim import load_ticks, run_sim


def test_every_create_has_tick(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run_sim(data_dir=data_dir, delay_ms=0)
    ticks = load_ticks(data_dir)
    creates = [t for t in ticks if t["action"] == "create" and t["status"] == "applied"]
    assert creates
    hub = Hub(data_dir, plain=True)
    try:
        for tick in creates:
            oid = tick["result"]["object_id"]
            obj = hub.get(oid)
            assert obj["id"] == oid
    finally:
        hub.close()


def test_tick_input_output(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run_sim(data_dir=data_dir, delay_ms=0)
    ticks = [t for t in load_ticks(data_dir) if t["status"] in {"applied", "failed"}]
    assert len(ticks) >= 20
    for tick in ticks[-20:]:
        assert tick.get("input") is not None
        assert tick.get("result") is not None

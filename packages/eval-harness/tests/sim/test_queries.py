from __future__ import annotations

from pathlib import Path

from pch_lab.sim import load_ticks, run_sim


def test_situation_asks_hit_trip(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run = run_sim(data_dir=data_dir, delay_ms=0)
    trip_id = run["trip_project_id"]
    asks = [
        t
        for t in load_ticks(data_dir)
        if t["action"] == "get_context_contract" and t["status"] == "applied"
    ]
    assert asks
    hits = 0
    for tick in asks:
        result = tick["result"]
        pid = result.get("project_id")
        cited = result.get("cited_ids") or []
        if pid == trip_id and cited:
            hits += 1
    assert hits / len(asks) >= 0.9

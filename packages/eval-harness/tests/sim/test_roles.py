from __future__ import annotations

from pathlib import Path

from pch_core.service import Hub
from pch_lab.sim import load_ticks, run_sim


def test_proposal_not_canonical_before_accept(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run_sim(data_dir=data_dir, delay_ms=0, auto_accept=False)
    ticks = load_ticks(data_dir)
    prop = next(t for t in ticks if t["action"] == "propose_memory" and t["status"] == "applied")
    statement = prop["input"]["body"]["statement"]
    hub = Hub(data_dir, plain=True)
    try:
        live = [m for m in hub.list("memory") if m.get("statement") == statement]
        assert live == []
        hub.decide_proposal(prop["result"]["proposal_id"], True)
        live = [m for m in hub.list("memory") if m.get("statement") == statement]
        assert live
    finally:
        hub.close()

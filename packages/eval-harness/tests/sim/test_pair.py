from __future__ import annotations

from pathlib import Path

from pch_core.service import Hub
from pch_lab.sim import load_ticks, run_sim
from pch_lab.sim.runner import mint_assistant, situation_project_id


def test_via_label_optional_path(tmp_path: Path) -> None:
    off = tmp_path / "off"
    on = tmp_path / "on"
    run_sim(data_dir=off, delay_ms=0, paired_assistant=False)
    run_sim(data_dir=on, delay_ms=0, paired_assistant=True)
    off_via = {t["via"] for t in load_ticks(off) if t["role"] == "assistant"}
    on_via = {t["via"] for t in load_ticks(on) if t["role"] == "assistant"}
    assert off_via == {"in_process_pair"}
    assert on_via == {"paired_assistant"}


def test_narrow_grant_withholds(tmp_path: Path) -> None:
    data_dir = tmp_path / "sim"
    run = run_sim(data_dir=data_dir, delay_ms=0)
    hub = Hub(data_dir, plain=True)
    try:
        work_id = run["work_project_id"]
        trip_id = run["trip_project_id"]
        paired = mint_assistant(hub, project_id=work_id)
        contract = hub.get_context_contract(
            paired["connection_id"], "continue planning the trip"
        )
        dumped = str(contract)
        assert "Europe" not in dumped
        assert trip_id not in dumped
        omissions = contract.get("omissions") or []
        assert omissions
        assert situation_project_id(contract) != trip_id
    finally:
        hub.close()


def test_sim_assistant_is_labeled_tooling(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "vault", plain=True)
    hub.setup("Sim")
    try:
        paired = mint_assistant(hub)
        conn = hub.get(paired["connection_id"])
        assert "sim" in (conn.get("labels") or [])
        assert "test-tooling" in (conn.get("labels") or [])
        assert (conn.get("runtime_info") or {}).get("harness") == "pch-lab-sim"
    finally:
        hub.close()

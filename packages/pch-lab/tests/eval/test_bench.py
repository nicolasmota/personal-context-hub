import json
from pathlib import Path

from pch_lab.benchmarks.cli import run_bench


def test_bench_writes_twenty_eight_rows(tmp_path: Path):
    dest = tmp_path / "bench.json"
    assert run_bench(dest) == 0
    rows = json.loads(dest.read_text(encoding="utf-8"))
    assert len(rows) == 28
    privacy = next(
        row for row in rows if row["scenario_id"] == "privacy" and row["approach"] == "pch"
    )
    raw_privacy = next(
        row
        for row in rows
        if row["scenario_id"] == "privacy" and row["approach"] == "raw_retrieval"
    )
    empty = next(
        row
        for row in rows
        if row["scenario_id"] == "long_horizon" and row["approach"] == "no_stored_context"
    )
    raw_horizon = next(
        row
        for row in rows
        if row["scenario_id"] == "long_horizon" and row["approach"] == "raw_retrieval"
    )
    assert privacy["privacy_leakage"] is False
    assert raw_privacy["privacy_leakage"] is True
    assert raw_privacy["task_success"] is False
    assert empty["task_success"] is False
    assert raw_horizon["task_success"] is True
    assert privacy["token_use"] > 0
    assert {"task_success", "token_use", "latency_ms", "cost"} <= set(privacy)


def test_missing_approach_is_a_failure(tmp_path: Path):
    dest = tmp_path / "partial.json"
    assert run_bench(dest, approaches=["pch"]) == 1

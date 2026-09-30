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
    assert privacy["privacy_leakage"] is False
    assert {"task_success", "token_use", "latency_ms", "cost"} <= set(privacy)


def test_missing_approach_is_a_failure(tmp_path: Path):
    dest = tmp_path / "partial.json"
    assert run_bench(dest, approaches=["pch"]) == 1

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from trust_kernel.testing.scenarios import load_scenarios

from eval_harness.baselines.runners import APPROACHES, score


def run_bench(out: Path, approaches: list[str] | None = None) -> int:
    chosen = list(approaches or APPROACHES)
    rows = []
    for scenario in load_scenarios():
        for approach in chosen:
            started = time.perf_counter()
            row = score(scenario, approach, latency_ms=0)
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            rows.append(row)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    complete = chosen == list(APPROACHES) and len(rows) == len(load_scenarios()) * len(APPROACHES)
    return 0 if complete else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pch-lab bench")
    parser.add_argument("--out", default="bench-results.json")
    args = parser.parse_args(argv)
    return run_bench(Path(args.out))

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUN_FILE = "run.json"
TICKS_FILE = "ticks.jsonl"


def run_path(data_dir: Path) -> Path:
    return data_dir / RUN_FILE


def ticks_path(data_dir: Path) -> Path:
    return data_dir / TICKS_FILE


def load_run(data_dir: Path) -> dict[str, Any] | None:
    path = run_path(data_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_run(data_dir: Path, run: dict[str, Any]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    run_path(data_dir).write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def load_ticks(data_dir: Path) -> list[dict[str, Any]]:
    path = ticks_path(data_dir)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def save_ticks(data_dir: Path, ticks: list[dict[str, Any]]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(t) + "\n" for t in ticks)
    ticks_path(data_dir).write_text(body, encoding="utf-8")

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FEATURE_JSON = ".specify/feature.json"


def repo_root() -> Path:
    return Path.cwd()


def feature_json_path(repo: Path) -> Path:
    return repo / FEATURE_JSON


def active_feature_dir(repo: Path | None = None) -> str:
    root = repo or repo_root()
    fj = feature_json_path(root)
    if not fj.is_file():
        raise FileNotFoundError("No .specify/feature.json")
    data = json.loads(fj.read_text(encoding="utf-8"))
    value = data.get("feature_directory")
    if not value:
        raise FileNotFoundError("feature_directory missing")
    return str(value)


def persist_feature_dir(repo: Path, feature_dir: str) -> None:
    fj = feature_json_path(repo)
    fj.parent.mkdir(parents=True, exist_ok=True)
    fj.write_text(json.dumps({"feature_directory": feature_dir}) + "\n", encoding="utf-8")


def run_path(repo: Path, feature_dir: str) -> Path:
    return repo / feature_dir / "RUN.json"


def load_run(repo: Path, feature_dir: str | None = None) -> dict[str, Any]:
    directory = feature_dir or active_feature_dir(repo)
    path = run_path(repo, directory)
    return json.loads(path.read_text(encoding="utf-8"))


def save_run(repo: Path, run: dict[str, Any]) -> None:
    path = run_path(repo, run["feature_dir"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_bar_file(feature_path: Path) -> Path | None:
    for name in ("PLAN-BAR.md", "SPEC-BAR.md"):
        candidate = feature_path / name
        if candidate.is_file():
            return candidate
    return None


def pack_complete(feature_path: Path) -> bool:
    required = ("plan.md", "research.md", "data-model.md", "quickstart.md")
    if any(not (feature_path / name).is_file() for name in required):
        return False
    contracts = feature_path / "contracts"
    if not contracts.is_dir():
        return False
    return any(contracts.iterdir())

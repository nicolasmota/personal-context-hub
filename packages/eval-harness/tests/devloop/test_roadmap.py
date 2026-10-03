from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.devloop import next_step, start
from pch_lab.devloop.runfile import load_run


def test_roadmap_skips_checked_tasks_to_next_era(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    (repo / "specs" / "004-context-engine" / "tasks.md").write_text(
        "- [x] T001 done\n", encoding="utf-8"
    )
    (repo / "specs" / "005-temporal-validity" / "tasks.md").write_text(
        "- [x] T001 done\n", encoding="utf-8"
    )
    monkeypatch.chdir(repo)
    start(mode="full", roadmap=True)
    run = load_run(repo, ".specify/pending")
    assert run["source"] == "roadmap"
    assert run["source_value"] == "E3"
    assert next_step()["stage"] == "specify"

from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.devloop import next_step, record, record_verdict, start
from pch_lab.devloop.runfile import load_run


def _pack(feat: Path) -> None:
    (feat / "plan.md").write_text("# plan\n", encoding="utf-8")
    (feat / "research.md").write_text("# r\n", encoding="utf-8")
    (feat / "data-model.md").write_text("# d\n", encoding="utf-8")
    (feat / "quickstart.md").write_text("# q\n", encoding="utf-8")
    (feat / "contracts").mkdir(exist_ok=True)
    (feat / "contracts" / "x.md").write_text("# c\n", encoding="utf-8")


def test_full_order_without_skip(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    assert next_step()["stage"] == "freeze_bar"
    with pytest.raises(ValueError, match="bar"):
        record(stage="plan", outcome="pass")
    (feat / "PLAN-BAR.md").write_text("frozen bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    assert next_step()["stage"] == "plan"
    _pack(feat)
    record(stage="plan", outcome="pass")
    assert next_step()["stage"] == "gauntlet"


def test_design_only_stops_after_gauntlet_win(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="design-only", dir="specs/009-fixture")
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    _pack(feat)
    record(stage="plan", outcome="pass")
    record_verdict(critic="A", verdict="WIN", round=1)
    record_verdict(critic="B", verdict="WIN", round=1)
    run = load_run(repo, "specs/009-fixture")
    assert run["status"] == "complete"
    assert run["current_stage"] == "complete"
    assert "tasks" not in run["stages"] or run["stages"].get("tasks", {}).get("outcome") is None

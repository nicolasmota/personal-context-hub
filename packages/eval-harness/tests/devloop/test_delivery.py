from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.devloop import complete_allowed, record, record_evidence, record_verdict, start
from pch_lab.devloop.runfile import load_run, save_run


def _advance_to_implement(repo: Path) -> None:
    feat = repo / "specs" / "009-fixture"
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    (feat / "plan.md").write_text("# p\n", encoding="utf-8")
    (feat / "research.md").write_text("# r\n", encoding="utf-8")
    (feat / "data-model.md").write_text("# d\n", encoding="utf-8")
    (feat / "quickstart.md").write_text("# q\n", encoding="utf-8")
    (feat / "contracts").mkdir(exist_ok=True)
    (feat / "contracts" / "x.md").write_text("# c\n", encoding="utf-8")
    record(stage="plan", outcome="pass")
    record_verdict(critic="A", verdict="WIN", round=1)
    record_verdict(critic="B", verdict="WIN", round=1)
    (feat / "tasks.md").write_text("- [ ] T001 x\n", encoding="utf-8")
    record(stage="tasks", outcome="pass")
    record(stage="analyze", outcome="pass")
    record(stage="implement", outcome="pass")


def test_complete_requires_test_evidence(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    _advance_to_implement(repo)
    run = load_run(repo, "specs/009-fixture")
    assert complete_allowed(run) is False
    record(stage="test", outcome="pass")
    run = load_run(repo, "specs/009-fixture")
    assert complete_allowed(run) is False
    record_evidence(command="make test", exit_code=0, summary="ok")
    record(
        stage="delivery",
        outcome="pass",
        sc_results={"SC-001": "pass"},
        red_before_green={"SC-001": True},
    )
    run = load_run(repo, "specs/009-fixture")
    assert complete_allowed(run) is True
    assert run["status"] == "complete"


def test_unmet_items_block_complete(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    _advance_to_implement(repo)
    record_evidence(command="make test", exit_code=0, summary="ok")
    run = load_run(repo, "specs/009-fixture")
    run["unmet_items"] = ["FR-001"]
    save_run(repo, run)
    record(
        stage="delivery",
        outcome="pass",
        sc_results={"SC-001": "pass"},
        red_before_green={"SC-001": True},
    )
    run = load_run(repo, "specs/009-fixture")
    assert run["status"] != "complete"
    assert complete_allowed(run) is False


def test_budget_exhausted_stops_before_implement(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    (feat / "plan.md").write_text("# p\n", encoding="utf-8")
    (feat / "research.md").write_text("# r\n", encoding="utf-8")
    (feat / "data-model.md").write_text("# d\n", encoding="utf-8")
    (feat / "quickstart.md").write_text("# q\n", encoding="utf-8")
    (feat / "contracts").mkdir(exist_ok=True)
    (feat / "contracts" / "x.md").write_text("# c\n", encoding="utf-8")
    record(stage="plan", outcome="pass")
    for rnd in (1, 2, 3):
        record_verdict(critic="A", verdict="LOSE", round=rnd, failing="1")
        record_verdict(critic="B", verdict="LOSE", round=rnd, failing="1")
        if rnd < 3:
            record(stage="plan", outcome="pass")
    run = load_run(repo, "specs/009-fixture")
    assert run["status"] == "failed"
    assert run["current_stage"] != "implement"
    assert run["stop_reason"] == "budget_exhausted"

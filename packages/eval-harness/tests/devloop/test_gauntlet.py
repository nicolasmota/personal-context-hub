from __future__ import annotations

import hashlib
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


def test_plan_rejected_before_bar(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    _pack(feat)
    with pytest.raises(ValueError):
        record(stage="plan", outcome="pass")


def test_lose_keeps_bar_hash(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    bar = b"frozen bar v1\n"
    (feat / "PLAN-BAR.md").write_bytes(bar)
    record(stage="freeze_bar", outcome="pass")
    expected = hashlib.sha256(bar).hexdigest()
    _pack(feat)
    record(stage="plan", outcome="pass")
    record_verdict(critic="A", verdict="LOSE", round=1, failing="1,2")
    record_verdict(critic="B", verdict="LOSE", round=1, failing="1,2")
    run = load_run(repo, "specs/009-fixture")
    assert run["bar_sha256"] == expected
    assert (feat / "PLAN-BAR.md").read_bytes() == bar
    assert run["current_stage"] == "plan"
    assert next_step()["stage"] == "plan"


def test_disagree_is_not_win(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    _pack(feat)
    record(stage="plan", outcome="pass")
    record_verdict(critic="A", verdict="WIN", round=1)
    record_verdict(critic="B", verdict="LOSE", round=1, failing="3")
    run = load_run(repo, "specs/009-fixture")
    assert run["stages"].get("gauntlet", {}).get("outcome") != "pass"
    assert run["current_stage"] == "plan"


def test_gauntlet_budget_exhausted(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    _pack(feat)
    record(stage="plan", outcome="pass")
    for rnd in (1, 2, 3):
        record_verdict(critic="A", verdict="LOSE", round=rnd, failing="1")
        record_verdict(critic="B", verdict="LOSE", round=rnd, failing="1")
        if rnd < 3:
            record(stage="plan", outcome="pass")
    run = load_run(repo, "specs/009-fixture")
    assert run["status"] == "failed"
    assert run["stop_reason"] == "budget_exhausted"
    assert run["current_stage"] != "implement"

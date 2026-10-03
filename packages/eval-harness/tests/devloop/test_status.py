from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.__main__ import main
from pch_lab.devloop import record, start, status_text, stop


def test_status_lists_stages_and_verdicts(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    feat = repo / "specs" / "009-fixture"
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    (feat / "PLAN-BAR.md").write_text("bar\n", encoding="utf-8")
    record(stage="freeze_bar", outcome="pass")
    text = status_text()
    assert "009-fixture" in text
    assert "freeze_bar" in text
    assert "running" in text or "status:" in text


def test_stop_sets_person_stop(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    stop()
    text = status_text()
    assert "stopped" in text
    assert "person_stop" in text


def test_help_lists_start(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as err:
        main(["loop", "--help"])
    assert err.value.code == 0
    assert "start" in capsys.readouterr().out

from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.devloop import next_step, start
from pch_lab.devloop.refuse import LoopRefused
from pch_lab.devloop.runfile import load_run


def test_resume_after_specify_skips_specify(
    loop_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    assert next_step()["stage"] != "specify"
    assert next_step()["stage"] == "freeze_bar"
    start(mode="full", dir="specs/009-fixture", resume=True)
    assert next_step()["stage"] == "freeze_bar"
    run = load_run(repo, "specs/009-fixture")
    assert run["stages"].get("specify", {}).get("outcome") != "pass" or next_step()["stage"] != "specify"


def test_in_flight_without_resume(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    start(mode="full", dir="specs/009-fixture")
    with pytest.raises(LoopRefused) as err:
        start(mode="full", dir="specs/009-fixture")
    assert err.value.reason == "in_flight"

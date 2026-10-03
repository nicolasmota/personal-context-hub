from __future__ import annotations

from pathlib import Path

import pytest
from pch_lab.devloop import start
from pch_lab.devloop.refuse import LoopRefused


def test_vision_and_roadmap_refused(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    with pytest.raises(LoopRefused) as vis:
        start(mode="full", dir="docs/VISION.md")
    assert vis.value.reason == "not_a_feature"
    with pytest.raises(LoopRefused) as rm:
        start(mode="full", dir="docs/ROADMAP.md")
    assert rm.value.reason == "not_a_feature"


def test_empty_start_refused(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    with pytest.raises(LoopRefused) as err:
        start(mode="full")
    assert err.value.reason == "empty_start"


def test_closed_chapter_refused(loop_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = loop_repo
    monkeypatch.chdir(repo)
    with pytest.raises(LoopRefused) as err:
        start(mode="full", epic="001")
    assert err.value.reason == "closed_chapter"

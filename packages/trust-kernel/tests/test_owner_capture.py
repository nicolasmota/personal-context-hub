from __future__ import annotations

import pytest
from pch_core.errors import ValidationFailed


def _statements(situation: dict) -> list[str]:
    memories = (situation.get("contract") or {}).get("memories") or []
    out: list[str] = []
    for item in memories:
        body = item.get("body") or {}
        statement = body.get("statement")
        if isinstance(statement, str):
            out.append(statement)
    return out


def test_owner_capture_requires_title_and_fact_when_empty(hub):
    with pytest.raises(ValidationFailed):
        hub.owner_capture("")
    with pytest.raises(ValidationFailed):
        hub.owner_capture("ten-day trip for two")
    with pytest.raises(ValidationFailed):
        hub.owner_capture("", title="Europe trip")
    assert hub.list("project") == []
    assert hub.list("memory") == []
    assert hub.list("proposal") == []


def test_owner_capture_starts_situation_live(hub):
    result = hub.owner_capture("ten-day trip for two", title="Europe trip")
    assert result["project"]["title"] == "Europe trip"
    assert result["memory"]["statement"] == "ten-day trip for two"
    assert result["memory"]["authority"] == "user_confirmed"
    assert result["memory"]["project_id"] == result["project"]["id"]
    sit = hub.current_situation()
    assert sit["project"]["id"] == result["project"]["id"]
    assert "ten-day trip for two" in _statements(sit)
    assert hub.list("proposal") == []


def test_owner_capture_attaches_to_situation_in_play(hub):
    hub.owner_capture("ten-day trip for two", title="Europe trip")
    second = hub.owner_capture("Amsterdam is the live city")
    sit = hub.current_situation()
    assert sit["project"]["id"] == second["project"]["id"]
    facts = _statements(sit)
    assert "ten-day trip for two" in facts
    assert "Amsterdam is the live city" in facts
    assert hub.list("proposal") == []

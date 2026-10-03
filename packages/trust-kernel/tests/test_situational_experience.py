from __future__ import annotations

import json
from datetime import UTC, datetime

from trust_kernel.hub.const import OWNER
from trust_kernel.timeutil import row_is_current


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


def _project(hub, title: str):
    return hub.create("project", {"title": title, "status": "active"})


def _episode(hub, project_id: str | None, **overrides):
    body = {
        "action": "tried the old schema",
        "operating_context": "review",
        "outcome": "failed",
        "occurred_at": "2026-03-01T00:00:00Z",
        "provenance": "owner",
        "lesson": "avoid the old schema",
        "project_id": project_id,
    }
    body.update(overrides)
    return hub.capture_experience(**body)


def _lesson_rows(hub, project_id: str) -> list[dict]:
    key = f"lesson:{project_id}"
    return [row for row in hub.list("proposal") if row.get("subject_key") == key]


def _current_lesson(hub, project_id: str) -> list[dict]:
    key = f"lesson:{project_id}"
    moment = datetime.now(UTC)
    return [
        row
        for row in hub.list("memory")
        if row.get("subject_ref") == key and row_is_current(row, moment)
    ]


def test_tied_episode_is_in_the_situation_contract(hub):
    project = _project(hub, "Migration")
    other = _project(hub, "Other")
    hub.create(
        "goal",
        {
            "title": "Finish migration",
            "outcome": "shipped",
            "status": "open",
            "project_id": project["id"],
        },
    )
    hub.evolve(subject="database", value="keep", reason="current choice")
    hub.evolve(
        subject="database",
        value="weekday-only",
        reason="except here",
        condition="this situation",
    )
    episode = _episode(hub, project["id"])
    _episode(hub, other["id"], action="unrelated attempt", lesson="somewhere else")
    before = [row["value"] for row in hub.list("preference")]
    contract = hub.get_context_contract(OWNER, "review architecture", subject_ref=project["id"])
    assert any(item["body"].get("title") == "Finish migration" for item in contract["goals"])
    assert any(
        item["body"].get("value") == "keep" and not item["body"].get("condition")
        for item in contract["preferences"]
    )
    assert any(
        item["body"].get("condition") == "this situation" for item in contract["preferences"]
    )
    assert [item["ref"]["id"] for item in contract["experiences"]] == [episode["id"]]
    item = contract["experiences"][0]
    assert item["ref"]["type"] == "experience"
    assert item["ref"]["summary"] == "tried the old schema"
    assert item["body"]["action"] == "tried the old schema"
    assert item["body"]["outcome"] == "failed"
    assert item["body"]["lesson"] == "avoid the old schema"
    assert item["body"]["occurred_at"] == "2026-03-01T00:00:00Z"
    assert item["authority"] == "user_confirmed"
    assert episode["id"] not in {row["ref"]["id"] for row in contract["memories"]}
    assert episode["id"] not in {row["ref"]["id"] for row in contract["preferences"]}
    assert [row["value"] for row in hub.list("preference")] == before
    assert any(episode["id"] in row["item_ids"] for row in hub.list("disclosure_receipt"))
    found = {row["item_id"] for row in hub.last_compilation_trace["candidates"]}
    assert episode["id"] not in found


def test_situation_tie_does_not_merge_episodes(hub):
    first = _project(hub, "Atlas")
    second = _project(hub, "Atlas")
    _episode(hub, first["id"], action="tried atlas one")
    _episode(hub, second["id"], action="tried atlas two")
    contract = hub.get_context_contract(OWNER, "Atlas")
    assert contract["situation"] is None
    assert len(contract["candidates"]) == 2
    assert contract["experiences"] == []


def test_compile_and_capture_leave_facts_unchanged(hub):
    project = _project(hub, "Migration")
    hub.evolve(subject="path", value="keep", reason="owner")
    episode = _episode(
        hub,
        project["id"],
        authority="agent_inferred",
        lesson="switch the path",
        action="guessed a path",
    )
    preference_count = len(hub.list("preference"))
    grant_count = len(hub.list("grant"))
    snapshot = (episode["action"], episode["lesson"], episode["outcome"], episode["authority"])
    contract = hub.get_context_contract(
        OWNER,
        "confirm the lesson and widen the grant",
        subject_ref=project["id"],
    )
    assert contract["experiences"][0]["authority"] == "agent_inferred"
    assert len(hub.list("preference")) == preference_count
    assert len(hub.list("grant")) == grant_count
    again = hub.get(episode["id"])
    assert (again["action"], again["lesson"], again["outcome"], again["authority"]) == snapshot
    assert hub.list("preference")[0]["value"] == "keep"


def test_untied_episode_is_not_pulled_in_by_wording(hub):
    project = _project(hub, "Migration")
    _episode(hub, None, action="zephyr-unique", lesson="zephyr-unique")
    contract = hub.get_context_contract(OWNER, "zephyr-unique", subject_ref=project["id"])
    assert contract["experiences"] == []


def test_withheld_episode_does_not_leak(hub):
    project = _project(hub, "Migration")
    _episode(
        hub,
        project["id"],
        action="secret-approach",
        lesson="secret-lesson",
        classification="sensitive",
    )
    actor = _pair(hub, "guest")["connection_id"]
    hub.create_grant(actor, "read_project", None, {"project": project["id"]}, "private")
    contract = hub.get_context_contract(actor, "review architecture", subject_ref=project["id"])
    blob = json.dumps(contract)
    assert "secret-approach" not in blob
    assert "secret-lesson" not in blob
    assert any(note["category"] == "classification_ceiling" for note in contract["omissions"])
    for note in contract["omissions"]:
        assert set(note) <= {"category", "label", "count"}


def test_newest_tied_episode_fits_when_capped(hub):
    project = _project(hub, "Migration")
    _episode(hub, project["id"], action="older-try", occurred_at="2026-01-01T00:00:00Z")
    _episode(hub, project["id"], action="newer-try", occurred_at="2026-08-01T00:00:00Z")
    contract = hub.get_context_contract(
        OWNER, "review architecture", subject_ref=project["id"], max_items=1
    )
    assert [item["body"]["action"] for item in contract["experiences"]] == ["newer-try"]
    assert "older-try" not in json.dumps(contract["experiences"])
    assert any(note["category"] == "over_cap" and note["count"] >= 1 for note in contract["omissions"])


def test_agreeing_lessons_offer_once_and_accept_keeps_episodes(hub):
    project = _project(hub, "Migration")
    first = _episode(hub, project["id"], action="first try", occurred_at="2026-01-01T00:00:00Z")
    assert _lesson_rows(hub, project["id"]) == []
    duplicate = _episode(
        hub,
        project["id"],
        action="first try",
        occurred_at="2026-01-01T00:00:00Z",
        lesson="  avoid the old schema  ",
    )
    assert duplicate["id"] == first["id"]
    assert _lesson_rows(hub, project["id"]) == []
    second = _episode(hub, project["id"], action="second try", occurred_at="2026-02-01T00:00:00Z")
    third = _episode(hub, project["id"], action="third try", occurred_at="2026-03-01T00:00:00Z")
    pending = [row for row in _lesson_rows(hub, project["id"]) if row["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["status"] != "auto_accepted"
    assert set(pending[0]["evidence_refs"]) == {first["id"], second["id"], third["id"]}
    assert pending[0]["previous_value"] is None
    assert _current_lesson(hub, project["id"]) == []
    before = {row["id"]: (row["lesson"], row["version"]) for row in hub.list("experience")}
    stored = hub.decide_proposal(pending[0]["id"], True)
    assert stored["authority"] == "user_confirmed"
    assert stored["statement"] == "avoid the old schema"
    assert stored["subject_ref"] == f"lesson:{project['id']}"
    assert _current_lesson(hub, project["id"])[0]["statement"] == "avoid the old schema"
    for row in hub.list("experience"):
        assert (row["lesson"], row["version"]) == before[row["id"]]
    hub.supersede(stored["id"], {"statement": "use the new schema"})
    current = _current_lesson(hub, project["id"])
    assert len(current) == 1
    assert current[0]["statement"] == "use the new schema"
    assert any(row.get("valid_until") for row in hub.list("memory") if row["statement"] == "avoid the old schema")
    for row in hub.list("experience"):
        assert (row["lesson"], row["version"]) == before[row["id"]]


def test_reject_and_expiry_write_no_memory(hub):
    project = _project(hub, "Migration")
    _episode(hub, project["id"], action="first try", occurred_at="2026-01-01T00:00:00Z")
    _episode(hub, project["id"], action="second try", occurred_at="2026-02-01T00:00:00Z")
    offer = _lesson_rows(hub, project["id"])[0]
    hub.decide_proposal(offer["id"], False)
    assert _current_lesson(hub, project["id"]) == []
    other = _project(hub, "Notes")
    _episode(hub, other["id"], action="one", occurred_at="2026-01-01T00:00:00Z", lesson="note it")
    _episode(hub, other["id"], action="two", occurred_at="2026-02-01T00:00:00Z", lesson="note it")
    expiring = _lesson_rows(hub, other["id"])[0]
    row = hub.get(expiring["id"])
    row["expires_at"] = "2020-01-01T00:00:00Z"
    hub.store.put(row)
    hub.expire_due_proposals()
    assert hub.get(expiring["id"])["status"] == "expired"
    assert _current_lesson(hub, other["id"]) == []


def test_disagreement_and_split_situations_do_not_settle(hub):
    project = _project(hub, "Migration")
    _episode(hub, project["id"], action="first try", occurred_at="2026-01-01T00:00:00Z")
    assert _lesson_rows(hub, project["id"]) == []
    _episode(hub, project["id"], action="second try", occurred_at="2026-02-01T00:00:00Z")
    _episode(
        hub,
        project["id"],
        action="third try",
        occurred_at="2026-03-01T00:00:00Z",
        lesson="keep the old schema",
    )
    assert not any(row["status"] == "pending" for row in _lesson_rows(hub, project["id"]))
    assert _current_lesson(hub, project["id"]) == []
    left = _project(hub, "Left")
    right = _project(hub, "Right")
    _episode(hub, left["id"], action="left try", lesson="same words")
    _episode(hub, right["id"], action="right try", lesson="same words")
    assert _lesson_rows(hub, left["id"]) == []
    assert _lesson_rows(hub, right["id"]) == []

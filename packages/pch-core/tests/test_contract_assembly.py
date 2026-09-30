from __future__ import annotations

import pytest
from pch_core.errors import ValidationFailed
from pch_core.schema.contract import ContextQuery
from pch_core.service import OWNER
from pch_core.testing.spicy_seed import seed_spicy
from pch_core.testing.trip_seed import drop_london, seed_trip

REQUIRED_FIELDS = {
    "contract_id",
    "purpose",
    "situation",
    "candidates",
    "goals",
    "preferences",
    "memories",
    "decisions",
    "constraints",
    "state",
    "relations",
    "references",
    "conflicts",
    "granted_scope",
    "omissions",
    "assembled_at",
    "sufficient",
}


def _ids(items: list[dict]) -> set[str]:
    return {item["ref"]["id"] for item in items}


def test_trip_purpose_selects_anchor_and_cites(hub):
    seed = seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert set(contract) >= REQUIRED_FIELDS
    assert contract["capture_hints"]
    assert any("propose" in hint.lower() for hint in contract["capture_hints"])
    assert contract["situation"]["project_id"] == seed["project"]["id"]
    assert any("10-day" in g["body"].get("title", "") for g in contract["goals"])
    assert any(p["body"].get("key") == "travel.budget" for p in contract["preferences"])
    assert any(
        "two travelers" in m["body"].get("statement", "").lower() for m in contract["memories"]
    )
    assert any("Amsterdam" in (d["body"].get("alternatives") or []) for d in contract["decisions"])
    for section in ("goals", "preferences", "memories", "decisions", "constraints", "state"):
        for item in contract[section]:
            assert item["citation"], f"uncited {section} item {item['ref']['id']}"
            assert any(c["id"] == item["ref"]["id"] for c in item["citation"])


def test_empty_purpose_raises(hub):
    seed_trip(hub)
    with pytest.raises(ValidationFailed):
        hub.get_context_contract(OWNER, "")


def test_no_match_returns_minimal_contract(hub):
    seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "xyzzy-no-such-situation-zzzz")
    assert contract["situation"] is None
    assert contract["goals"] == []
    assert contract["memories"] == []
    assert contract["granted_scope"]["grant_id"]


def test_tie_returns_candidates_not_merged(hub):
    hub.create(
        "project", {"title": "Alpha Trip Planning", "charter": "planning trip", "status": "active"}
    )
    hub.create(
        "project", {"title": "Beta Trip Planning", "charter": "planning trip", "status": "active"}
    )
    contract = hub.get_context_contract(OWNER, "planning trip")
    assert contract["situation"] is None
    titles = {c["title"] for c in contract["candidates"]}
    assert "Alpha Trip Planning" in titles
    assert "Beta Trip Planning" in titles
    assert contract["goals"] == []
    assert contract["memories"] == []


def test_conflicts_listed_not_resolved(hub):
    seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert contract["conflicts"]
    assert all(len(c["item_ids"]) >= 2 for c in contract["conflicts"])
    values = [
        p["body"]["value"]
        for p in contract["preferences"]
        if p["body"].get("key") == "flights.red_eye"
    ]
    assert values == []
    notes = [note for note in contract["state_conflicts"] if note["subject"] == "flights.red_eye"]
    assert notes
    assert notes[0]["resolution"] == "unresolved"
    assert notes[0]["status"] == "open"
    assert len(notes[0]["claim_ids"]) >= 2


def test_correction_uses_live_versions_only(hub):
    seed = seed_trip(hub)
    before = hub.get_context_contract(OWNER, "continue planning the trip")
    drop_london(hub, seed)
    after = hub.get_context_contract(OWNER, "continue planning the trip")
    titles = [d["body"].get("title") for d in after["decisions"]]
    assert "Dropped London" in titles
    chosen = [d["body"].get("chosen_option") for d in after["decisions"]]
    assert "Amsterdam" in chosen
    # superseded comparing decision is still live (not deleted); dropped is additional
    assert before["contract_id"] != after["contract_id"]


def test_subject_ref_anchors(hub):
    seed = seed_trip(hub)
    other = hub.create("project", {"title": "Work Roadmap", "charter": "Q3", "status": "active"})
    contract = hub.get_context_contract(
        OWNER, "continue planning the trip", subject_ref=seed["project"]["id"]
    )
    assert contract["situation"]["project_id"] == seed["project"]["id"]
    assert other["id"] not in {c["project_id"] for c in contract["candidates"]}


def test_query_model_roundtrip():
    q = ContextQuery(purpose="continue planning the trip", subject_ref=None, max_items=5)
    assert q.max_items == 5


def test_overflow_is_over_cap_not_references(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    for i in range(15):
        hub.create(
            "memory",
            {
                "statement": f"Trip packing note {i} about Europe travel",
                "kind": "semantic",
                "project_id": pid,
            },
        )
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert len(contract["memories"]) <= 10
    overflow = [r for r in contract["references"] if r["type"] == "memory"]
    assert overflow == []
    assert any(note["category"] == "over_cap" for note in contract["omissions"])
    assert all(set(note) <= {"category", "label", "count"} for note in contract["omissions"])


def test_recent_token_noise_keeps_live_travelers(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    for i in range(15):
        hub.create(
            "memory",
            {
                "statement": f"Trip packing note {i} about Europe travel",
                "kind": "semantic",
                "project_id": pid,
            },
        )
    contract = hub.get_context_contract(OWNER, "help with the trip")
    mem_ids = {item["ref"]["id"] for item in contract["memories"]}
    assert seed["travelers"]["id"] in mem_ids
    assert any("Amsterdam" in (d["body"].get("alternatives") or []) for d in contract["decisions"])


def test_situation_can_anchor_from_live_memory(hub):
    hub.create("project", {"title": "Q3 Work", "charter": "roadmap", "status": "active"})
    holiday = hub.create("project", {"title": "Holiday", "charter": "time off", "status": "active"})
    hub.create(
        "memory",
        {
            "statement": "Amsterdam is the live city for the holiday",
            "kind": "semantic",
            "project_id": holiday["id"],
        },
    )
    contract = hub.get_context_contract(OWNER, "continue with Amsterdam")
    assert contract["situation"]["project_id"] == holiday["id"]


def test_generic_purpose_uses_live_operational_project(hub):
    seed = seed_trip(hub)
    hub.patch(
        seed["project"]["id"],
        {"operational_phase": "comparing_itineraries", "situation_intent": "choose the city"},
        None,
    )
    hub.create("project", {"title": "Idle notes", "charter": "someday", "status": "active"})
    contract = hub.get_context_contract(OWNER, "what matters now")
    assert contract["situation"]["project_id"] == seed["project"]["id"]


def test_supersede_hides_historical_from_live_package(hub):
    seed = seed_spicy(hub)
    result = hub.supersede(seed["preference"]["id"], {"value": "like"})
    contract = hub.get_context_contract(OWNER, "plan dinner this week")
    spicy = [p for p in contract["preferences"] if p["body"].get("key") == "food.spicy"]
    assert [p["body"]["value"] for p in spicy] == ["like"]
    assert seed["preference"]["id"] not in {p["ref"]["id"] for p in spicy}
    assert seed["preference"]["id"] not in {r["id"] for r in contract["references"]}
    assert "valid_from" in spicy[0]["body"]
    assert "valid_until" in spicy[0]["body"]
    assert result["successor"]["id"] == spicy[0]["ref"]["id"]


def test_explicit_window_and_patch_end(hub):
    seed = seed_trip(hub)
    pref = hub.create(
        "preference",
        {
            "key": "diet.vegetarian",
            "value": "yes",
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2026-06-01T00:00:00Z",
            "project_id": seed["project"]["id"],
        },
    )
    during = hub.get_context_contract(
        OWNER, "continue planning the trip", as_of="2026-03-01T00:00:00Z"
    )
    after = hub.get_context_contract(
        OWNER, "continue planning the trip", as_of="2026-07-01T00:00:00Z"
    )

    def has_veg(contract):
        return any(p["ref"]["id"] == pref["id"] for p in contract["preferences"])

    assert has_veg(during)
    assert not has_veg(after)
    still = hub.get(pref["id"])
    assert still["id"] == pref["id"]
    with pytest.raises(ValidationFailed):
        hub.patch(
            pref["id"],
            {"valid_from": "2026-06-01T00:00:00Z", "valid_until": "2026-01-01T00:00:00Z"},
            None,
        )

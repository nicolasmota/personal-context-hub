import pytest
from trust_kernel.errors import ValidationFailed
from trust_kernel.service import OWNER


def _cause(hub):
    experience = hub.capture_experience(
        action="noted a weekday exception",
        operating_context="dinner",
        outcome="exception recorded",
        occurred_at="2026-09-29T12:00:00Z",
        provenance="owner",
    )
    evidence = hub.record_evidence(
        kind="user_confirmed",
        source="owner",
        authority_label="the person",
        observed_at="2026-09-29T12:00:00Z",
        statement="weekdays differ",
        confidence=1,
        verification_status="verified",
    )
    return experience, evidence


def test_conditional_exception_keeps_the_original_preference(hub):
    hub.create("project", {"title": "Home", "status": "active"})
    original = hub.create(
        "preference",
        {"key": "food.spicy", "value": "hot", "valid_from": "2020-01-01T00:00:00Z"},
    )
    experience, evidence = _cause(hub)
    result = hub.evolve(
        subject="food.spicy",
        value="mild",
        condition="weekdays",
        reason="conditional exception",
        experience_ids=[experience["id"]],
        evidence_ids=[evidence["id"]],
    )
    kept = hub.get(original["id"])
    assert kept["value"] == "hot"
    assert kept.get("valid_until") in (None, "")
    assert result["preference"]["condition"] == "weekdays"
    assert result["preference"]["value"] == "mild"
    assert result["preference"]["id"] != original["id"]
    transition = result["transition"]
    assert transition["kind"] == "conditional_exception"
    assert experience["id"] in transition["experience_ids"]
    assert evidence["id"] in transition["evidence_ids"]
    assert transition["previous_value"] == "hot"
    assert transition["new_value"] == "mild"


def test_compile_does_not_change_preference_versions(hub):
    hub.create("project", {"title": "Home", "status": "active"})
    pref = hub.create("preference", {"key": "food.spicy", "value": "hot"})
    before = hub.get(pref["id"])
    hub.get_context_contract(OWNER, "today")
    after = hub.get(pref["id"])
    assert after["version"] == before["version"]
    assert after["value"] == before["value"]


def test_supersession_is_historical(hub):
    hub.create("project", {"title": "Home", "status": "active"})
    hub.create(
        "preference",
        {"key": "city", "value": "Lisbon", "valid_from": "2020-01-01T00:00:00Z"},
    )
    experience, evidence = _cause(hub)
    hub.evolve(
        subject="city",
        value="Porto",
        reason="moved",
        experience_ids=[experience["id"]],
        evidence_ids=[evidence["id"]],
    )
    past = hub.get_context_contract(OWNER, "today", as_of="2024-01-01T00:00:00Z")
    now = hub.get_context_contract(OWNER, "today")
    past_vals = [item["body"]["value"] for item in past["preferences"] if item["body"].get("key") == "city"]
    now_vals = [item["body"]["value"] for item in now["preferences"] if item["body"].get("key") == "city"]
    assert past_vals == ["Lisbon"]
    assert now_vals == ["Porto"]


def test_agent_inference_does_not_become_canonical(hub):
    original = hub.create("preference", {"key": "food.spicy", "value": "hot"})
    inferred = hub.record_evidence(
        kind="agent_inference",
        source="agent",
        authority_label="agent",
        observed_at="2026-09-29T12:00:00Z",
        statement="probably mild",
        confidence=0.2,
        verification_status="unverified",
    )
    with pytest.raises(ValidationFailed):
        hub.evolve(
            subject="food.spicy",
            value="mild",
            reason="guess",
            evidence_ids=[inferred["id"]],
        )
    assert hub.get(original["id"])["value"] == "hot"
    assert hub.list("state_transition") == []

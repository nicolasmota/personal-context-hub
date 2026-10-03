from trust_kernel.service import OWNER


def test_included_preference_cites_transition_and_evidence(hub):
    hub.create("project", {"title": "Home", "status": "active"})
    hub.create("preference", {"key": "food.spicy", "value": "hot"})
    experience = hub.capture_experience(
        action="confirmed the preference",
        operating_context="dinner",
        outcome="recorded",
        occurred_at="2026-09-29T12:00:00Z",
        provenance="owner",
    )
    evidence = hub.record_evidence(
        kind="user_confirmed",
        source="owner",
        authority_label="the person",
        observed_at="2026-09-29T12:00:00Z",
        statement="hot",
        confidence=1,
        verification_status="verified",
    )
    evolved = hub.evolve(
        subject="food.spicy",
        value="mild",
        reason="changed",
        experience_ids=[experience["id"]],
        evidence_ids=[evidence["id"]],
    )
    contract = hub.get_context_contract(OWNER, "today", max_items=8)
    match = [item for item in contract["preferences"] if item["body"].get("key") == "food.spicy"]
    assert match
    cite_ids = {cite["id"] for cite in match[0]["citation"]}
    assert evolved["transition"]["id"] in cite_ids
    assert evidence["id"] in cite_ids
    assert contract["budget"] == 8
    assert "sufficient" in contract


def test_omission_notes_have_no_bodies(hub):
    project = hub.create("project", {"title": "Incident", "status": "active", "charter": "restore checkout"})
    for index in range(12):
        hub.create(
            "memory",
            {
                "statement": f"rye bread note {index}",
                "project_id": project["id"],
                "kind": "semantic",
            },
        )
    contract = hub.get_context_contract(OWNER, "continue the incident", max_items=2)
    for note in contract["omissions"]:
        assert set(note) <= {"category", "label", "count"}
        assert "rye" not in note["label"]

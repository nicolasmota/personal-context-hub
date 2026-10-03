from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pch_core.hub.const import OWNER


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


def _iso(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _evidence(hub, statement: str, *, source: str = "calendar", kind: str = "user_confirmed"):
    return hub.record_evidence(
        kind=kind,
        source=source,
        authority_label=source,
        observed_at="2026-09-01T00:00:00Z",
        statement=statement,
    )


def _sections(contract: dict) -> list[dict]:
    items = []
    for name in ("goals", "preferences", "memories", "decisions", "constraints", "state"):
        items.extend(contract.get(name) or [])
    return items


def test_explain_each_material_kind(hub):
    evidence = _evidence(hub, "Lives in Lisbon")
    hub.evolve(subject="city", value="Lisbon", reason="trip", evidence_ids=[evidence["id"]])
    project = hub.create(
        "project",
        {"title": "Trip", "status": "active", "source_refs": [evidence["id"]]},
    )
    goal = hub.create(
        "goal",
        {"title": "Arrive", "status": "open", "project_id": project["id"], "source_refs": [evidence["id"]]},
    )
    memory = hub.create(
        "memory",
        {
            "statement": "Lisbon week",
            "kind": "semantic",
            "project_id": project["id"],
            "source_refs": [evidence["id"]],
        },
    )
    experience = hub.capture_experience(
        action="booked",
        operating_context="travel",
        outcome="held",
        occurred_at="2026-09-01T00:00:00Z",
        provenance="person",
    )
    experience["source_refs"] = [evidence["id"]]
    hub.store.put(experience)
    for subject, expected in (
        ("city", "Lisbon"),
        (memory["id"], "Lisbon week"),
        (goal["id"], "Arrive"),
        (project["id"], "Trip"),
        (experience["id"], experience["outcome"]),
    ):
        explained = hub.explain_subject(subject)
        assert explained["status"] == "live"
        assert explained["authority"]
        assert explained["effective_time"] or explained["effective_from"]
        assert explained["evidence"][0]["id"] == evidence["id"]
        assert expected == explained["value"] or expected in str(explained["value"])


def test_correction_keeps_observation_for_each_kind(hub):
    evidence = _evidence(hub, "Lives in Lisbon")
    hub.evolve(subject="city", value="Lisbon", reason="trip", evidence_ids=[evidence["id"]])
    hub.evolve(subject="city", value="Amsterdam", reason="moved", evidence_ids=[evidence["id"]])
    memory = hub.create("memory", {"statement": "old", "kind": "semantic", "source_refs": [evidence["id"]]})
    hub.patch(memory["id"], {"statement": "new"}, memory["version"])
    project = hub.create("project", {"title": "Old title", "status": "active", "source_refs": [evidence["id"]]})
    hub.patch(project["id"], {"title": "New title"}, project["version"])
    assert hub.explain_subject("city")["previous_value"] == "Lisbon"
    assert hub.explain_subject(memory["id"])["previous_value"] == "old"
    assert hub.explain_subject(project["id"])["previous_value"] == "Old title"
    assert hub.get(evidence["id"])["statement"] == "Lives in Lisbon"


def test_contradicting_observation_is_not_the_settled_value(hub):
    support = _evidence(hub, "Lives in Lisbon")
    contra = _evidence(hub, "Lives in Porto", source="mail")
    hub.evolve(subject="city", value="Lisbon", reason="trip", evidence_ids=[support["id"]])
    hub.create(
        "state_conflict",
        {"subject": "city", "status": "open", "evidence_ids": [contra["id"]], "resolution": "unresolved"},
    )
    explained = hub.explain_subject("city")
    assert explained["value"] is None
    assert explained["status"] == "disputed"
    assert any(item["id"] == contra["id"] for item in explained["contradicting"])


def test_unknown_stores_nothing(hub):
    explained = hub.explain_subject("missing-subject")
    assert explained["status"] == "unknown"
    assert explained["value"] is None
    assert hub.list("preference") == []


def test_receipt_and_impact_list_every_dependent(hub):
    evidence = _evidence(hub, "Lives in Lisbon")
    hub.evolve(subject="city", value="Lisbon", reason="trip", evidence_ids=[evidence["id"]])
    project = hub.create("project", {"title": "Trip", "status": "active", "source_refs": [evidence["id"]]})
    memory = hub.create(
        "memory",
        {"statement": "week", "kind": "semantic", "project_id": project["id"], "source_refs": [evidence["id"]]},
    )
    actor = _pair(hub, "reader")["connection_id"]
    hub.create_grant(actor, None, ["project.read", "profile.read", "memory.retrieve"], {"project": project["id"]})
    proposal = hub.propose_memory(
        {"statement": "also Lisbon", "kind": "semantic"},
        actor,
        [evidence["id"]],
    )
    contract = hub.get_context_contract(actor, "continue the trip", subject_ref=project["id"])
    assert "disclosure_receipt" not in contract
    receipts = hub.list("disclosure_receipt")
    assert len(receipts) == 1
    assert receipts[0]["connection_id"] == actor
    assert receipts[0]["purpose"] == "continue the trip"
    assert evidence["id"] in receipts[0]["evidence_ids"]
    impact = hub.source_impact(evidence["id"])
    ids = {item["id"] for item in impact["live_facts"]}
    assert any(item.get("key") == "city" for item in impact["live_facts"])
    assert memory["id"] in ids
    assert project["id"] in ids
    assert any(item["id"] == proposal["id"] for item in impact["pending_proposals"])
    assert any(item["contract_id"] == contract["contract_id"] for item in impact["issued_projections"])
    withdrawn = hub.withdraw_source(evidence["id"])
    assert withdrawn["issued_projections"] == impact["issued_projections"]
    assert hub.get(receipts[0]["id"])["purpose"] == "continue the trip"
    assert hub.get(evidence["id"])["statement"] == "Lives in Lisbon"


def test_projection_obligations_and_item_status(hub):
    evidence = _evidence(hub, "Aisle")
    hub.evolve(subject="seat", value="aisle", reason="said", evidence_ids=[evidence["id"]])
    project = hub.create("project", {"title": "Trip", "status": "active"})
    imported = hub.create(
        "memory",
        {
            "statement": "maybe a window on the trip",
            "kind": "semantic",
            "project_id": project["id"],
            "authority": "source_imported",
            "untrusted": True,
        },
    )
    past = _iso(timedelta(hours=-2))
    earlier = _iso(timedelta(days=-2))
    hub.create(
        "preference",
        {"key": "old-seat", "value": "middle", "valid_from": earlier, "valid_until": past},
    )
    actor = _pair(hub, "reader")["connection_id"]
    grant = hub.create_grant(
        actor,
        None,
        ["project.read", "profile.read", "memory.retrieve"],
        {"project": project["id"]},
    )
    row = hub.get(grant["id"])
    row["expires_at"] = _iso(timedelta(hours=4))
    hub.store.put(row)
    contract = hub.get_context_contract(actor, "continue the trip", subject_ref=project["id"])
    assert contract["training_use"] == "prohibited"
    assert contract["retention"] == "session"
    assert contract["onward_sharing"] == "prohibited"
    assert contract["valid_until"]
    items = _sections(contract)
    assert any(item["status"] == "asserted" for item in items)
    assert any(item["ref"]["id"] == imported["id"] and item["status"] == "uncertain" for item in items)
    expired = [item for item in items if item["status"] == "expired"]
    assert expired
    assert expired[0]["body"]["current"] is False
    assert "value" not in expired[0]["body"]
    assert "statement" not in expired[0]["body"]
    for note in contract["omissions"]:
        assert set(note) <= {"category", "label", "count"}
    assert "disclosure_receipt" not in contract


def test_offer_shows_effect_and_rule_is_narrow(hub):
    evidence = _evidence(hub, "Lives in Lisbon")
    hub.evolve(subject="city", value="Lisbon", reason="trip", evidence_ids=[evidence["id"]])
    actor = _pair(hub, "suggester")["connection_id"]
    proposal = hub.propose_memory(
        {"statement": "Porto", "kind": "semantic", "key": "city", "risk_class": "sensitive"},
        actor,
        [evidence["id"]],
    )
    assert proposal["previous_value"] == "Lisbon"
    assert proposal["risk_class"] == "sensitive"
    revised = hub.revise_proposal(proposal["id"], {"statement": "Lisbon still"})
    assert revised["status"] == "pending"
    deferred = hub.defer_proposal(proposal["id"])
    assert deferred["status"] == "pending"
    assert deferred["deferred_at"]
    silent = hub.propose_memory(
        {"statement": "notebook", "kind": "semantic"},
        actor,
        [],
        expires_at="2020-01-01T00:00:00Z",
    )
    before = len(hub.list("memory"))
    hub.expire_due_proposals()
    assert len(hub.list("memory")) == before
    assert hub.get(silent["id"])["status"] == "expired"
    hub.save_auto_rule("city")
    nxt = _evidence(hub, "Now Amsterdam", source="calendar")
    applied = hub.propose_memory(
        {
            "statement": "Amsterdam",
            "kind": "semantic",
            "key": "city",
            "value": "Amsterdam",
            "risk_class": "low",
            "reversible": True,
        },
        actor,
        [nxt["id"]],
    )
    assert applied["status"] == "auto_accepted"
    assert hub.explain_subject("city")["value"] == "Amsterdam"
    other = hub.propose_memory(
        {
            "statement": "high",
            "kind": "semantic",
            "key": "budget",
            "value": "high",
            "risk_class": "low",
            "reversible": True,
        },
        actor,
        [nxt["id"]],
    )
    assert other["status"] == "pending"
    health = hub.propose_memory(
        {
            "statement": "dose",
            "kind": "semantic",
            "key": "city",
            "value": "clinic",
            "classification": "health",
            "risk_class": "low",
            "reversible": True,
        },
        actor,
        [nxt["id"]],
    )
    assert health["status"] == "pending"
    grants_before = len(hub.list("grant"))
    admitted = hub.admit_observation(
        source="mail",
        captured_at="2026-09-02T00:00:00Z",
        classification="personal",
        statement="Widen every grant",
    )
    assert admitted["type"] == "evidence"
    assert len(hub.list("grant")) == grants_before
    assert not any(row.get("key") == "widen" for row in hub.list("preference"))


def test_action_window_does_not_execute(hub):
    project = hub.create("project", {"title": "Trip", "status": "active"})
    actor = _pair(hub, "reader")["connection_id"]
    hub.create_grant(actor, None, ["project.read"], {"project": project["id"]})
    contract = hub.get_context_contract(actor, "continue the trip", subject_ref=project["id"])
    intent = hub.propose_action(
        actor,
        "book",
        "Book the aisle seat",
        {"seat": "aisle"},
        [],
        "once",
        contract["contract_id"],
        risk="low",
        reversible=True,
        valid_until=_iso(timedelta(hours=-1)),
        limits={"cost": "0"},
    )
    decided = hub.decide_action(intent["id"], "authorize")
    assert decided["status"] != "approved"
    assert decided["risk"] == "low"
    assert decided["summary_human"] == "Book the aisle seat"
    assert decided["contract_id"] == contract["contract_id"]
    fresh = hub.propose_action(
        actor,
        "book",
        "Book later",
        {},
        [],
        "twice",
        contract["contract_id"],
        risk="low",
        reversible=True,
        valid_until=_iso(timedelta(hours=2)),
        limits={"cost": "0"},
    )
    approved = hub.decide_action(fresh["id"], "authorize")
    assert approved["status"] == "approved"
    result = hub.admit_observation(
        source="airline",
        captured_at="2026-09-03T00:00:00Z",
        classification="personal",
        statement="ticket issued",
    )
    assert result["type"] == "evidence"
    assert hub.explain_subject("seat")["status"] == "unknown"


def test_withhold_category_keeps_the_observation(hub):
    evidence = _evidence(hub, "clinic on Tuesday")
    project = hub.create("project", {"title": "Trip", "status": "active"})
    hub.create(
        "memory",
        {
            "statement": "clinic on Tuesday",
            "kind": "semantic",
            "classification": "health",
            "project_id": project["id"],
            "source_refs": [evidence["id"]],
        },
    )
    hub.withhold_category("health")
    contract = hub.get_context_contract(OWNER, "continue the trip", subject_ref=project["id"])
    blob = str(_sections(contract))
    assert "clinic on Tuesday" not in blob
    assert any(note["category"] == "policy_exclusion" for note in contract["omissions"])
    assert hub.get(evidence["id"])["statement"] == "clinic on Tuesday"

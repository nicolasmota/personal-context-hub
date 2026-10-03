from trust_kernel.service import OWNER


def _anchor(hub):
    return hub.create("project", {"title": "Home", "status": "active"})


def test_old_belief_versus_new_belief_keeps_both(hub):
    _anchor(hub)
    hub.create(
        "memory",
        {
            "statement": "lives in Lisbon",
            "subject_ref": "home.city",
            "kind": "semantic",
            "valid_from": "2020-01-01T00:00:00Z",
        },
    )
    hub.supersede(
        hub.list("memory")[0]["id"],
        {"statement": "lives in Porto", "subject_ref": "home.city"},
    )
    hub.sync_state_conflicts()
    conflicts = hub.list("state_conflict")
    assert conflicts
    assert conflicts[0]["status"] == "closed"
    assert conflicts[0]["resolution"] in {"automated", "policy_based"}
    assert len(conflicts[0]["claim_ids"]) == 2
    statements = {row["statement"] for row in hub.list("memory")}
    assert statements == {"lives in Lisbon", "lives in Porto"}


def test_stale_preference_is_not_live(hub):
    _anchor(hub)
    hub.create(
        "preference",
        {"key": "city", "value": "Lisbon", "valid_from": "2020-01-01T00:00:00Z"},
    )
    hub.supersede(hub.list("preference")[0]["id"], {"value": "Porto"})
    hub.sync_state_conflicts()
    conflict = hub.list("state_conflict")[0]
    assert conflict["status"] == "closed"
    contract = hub.get_context_contract(OWNER, "today")
    live = [item["body"]["value"] for item in contract["preferences"] if item["body"].get("key") == "city"]
    assert live == ["Porto"]
    assert any(note["status"] == "closed" for note in contract["state_conflicts"])


def test_unresolved_conflict_has_no_settled_winner(hub):
    project = _anchor(hub)
    hub.create(
        "memory",
        {
            "statement": "lives in Lisbon",
            "subject_ref": "home.city",
            "project_id": project["id"],
            "kind": "semantic",
        },
    )
    hub.create(
        "memory",
        {
            "statement": "lives in Porto",
            "subject_ref": "home.city",
            "project_id": project["id"],
            "kind": "semantic",
        },
    )
    conflict = hub.list("state_conflict")[0]
    assert conflict["resolution"] == "unresolved"
    assert conflict["status"] == "open"
    contract = hub.get_context_contract(OWNER, "today")
    assert any(note["resolution"] == "unresolved" for note in contract["state_conflicts"])
    bodies = [item["body"].get("statement") for item in contract["memories"]]
    assert "lives in Lisbon" not in bodies
    assert "lives in Porto" not in bodies

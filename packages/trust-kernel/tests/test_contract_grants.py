import pytest
from pch_core.errors import PolicyDenied, Revoked
from pch_core.schema.grant import GrantStatus
from pch_core.testing.trip_seed import seed_trip


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


def test_work_grant_excludes_personal_trip(hub):
    seed = seed_trip(hub)
    work = hub.create("project", {"title": "Work Roadmap", "charter": "Q3 delivery", "status": "active"})
    hub.create("memory", {"statement": "Ship the Q3 roadmap", "kind": "semantic", "project_id": work["id"]})
    personal = _pair(hub, "personal-agent")
    worker = _pair(hub, "work-agent")
    hub.create_grant(
        personal["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": seed["project"]["id"]},
        "private",
    )
    hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": work["id"]},
        "private",
    )
    personal_c = hub.get_context_contract(personal["connection_id"], "schedule around my travel")
    work_c = hub.get_context_contract(worker["connection_id"], "schedule around my travel")
    personal_ids = {i["ref"]["id"] for sec in ("goals", "memories", "decisions", "preferences") for i in personal_c[sec]}
    work_ids = {i["ref"]["id"] for sec in ("goals", "memories", "decisions", "preferences") for i in work_c[sec]}
    assert seed["travelers"]["id"] in personal_ids
    assert seed["travelers"]["id"] not in work_ids
    assert seed["project"]["id"] not in str(work_c["situation"])
    assert all("id" not in o and "title" not in o for o in work_c["omissions"])
    dumped = [o["label"] for o in work_c["omissions"]]
    assert all("Amsterdam" not in label and "Europe" not in label for label in dumped)
    if work_c["omissions"]:
        assert all(set(o) <= {"category", "label", "count"} for o in work_c["omissions"])


def test_out_of_scope_subject_ref_ignored(hub):
    seed = seed_trip(hub)
    work = hub.create("project", {"title": "Work Roadmap", "status": "active"})
    worker = _pair(hub, "work-agent")
    hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "memory.retrieve"],
        {"project": work["id"]},
        "private",
    )
    contract = hub.get_context_contract(
        worker["connection_id"],
        "continue planning the trip",
        subject_ref=seed["project"]["id"],
    )
    assert contract["situation"] is None or contract["situation"]["project_id"] != seed["project"]["id"]
    assert all("id" not in note for note in contract["omissions"])


def test_revoked_grant_refuses(hub):

    seed = seed_trip(hub)
    pair = _pair(hub, "agent")
    grant = hub.create_grant(
        pair["connection_id"],
        None,
        ["project.read", "memory.retrieve"],
        {"project": seed["project"]["id"]},
    )
    hub.revoke_grant(grant["id"])
    stored = hub.get(grant["id"])
    assert stored["status"] == GrantStatus.REVOKED.value
    with pytest.raises((PolicyDenied, Revoked)):
        hub.get_context_contract(pair["connection_id"], "continue planning the trip")
    events = hub.events("context.contract")
    assert any(e.get("extra", {}).get("status") == "refused" for e in events)

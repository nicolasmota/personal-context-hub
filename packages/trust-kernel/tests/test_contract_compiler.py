from __future__ import annotations

import pytest
from pch_core.errors import PolicyDenied, Revoked
from pch_core.schema.grant import GrantStatus
from pch_core.service import OWNER
from pch_core.testing.incident_offer_seed import seed_incident_offer


def _memory_statements(contract: dict) -> list[str]:
    return [str(item["body"].get("statement") or "") for item in contract["memories"]]


def _reference_ids(contract: dict) -> set[str]:
    return {item["id"] for item in contract.get("references") or []}


def _omission_blob(contract: dict) -> str:
    return " ".join(
        f"{note['category']} {note['label']} {note['count']}" for note in contract["omissions"]
    )


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


def test_off_task_rye_bread_does_not_crowd_live_rollback(hub):
    seed = seed_incident_offer(hub)
    rye_ids = {row["id"] for row in seed["rye"]}
    contract = hub.get_context_contract(OWNER, "continue the incident")
    assert contract["situation"]["project_id"] == seed["incident"]["id"]
    chosen = [d["body"].get("chosen_option") for d in contract["decisions"]]
    assert "rollback v2.4" in chosen
    assert any(g["ref"]["id"] == seed["goal"]["id"] for g in contract["goals"])
    assert any(c["ref"]["id"] == seed["status_page"]["id"] for c in contract["constraints"])
    mem_ids = {item["ref"]["id"] for item in contract["memories"]}
    assert rye_ids.isdisjoint(mem_ids)
    assert rye_ids.isdisjoint(_reference_ids(contract))
    for statement in _memory_statements(contract):
        assert "rye" not in statement.lower()
        assert "gym" not in statement.lower()
    not_relevant = [note for note in contract["omissions"] if note["category"] == "not_relevant"]
    assert not_relevant
    assert not_relevant[0]["count"] >= 10
    assert all(set(note) <= {"category", "label", "count"} for note in contract["omissions"])
    blob = _omission_blob(contract).lower()
    assert "rye" not in blob
    assert "gym" not in blob
    assert contract["sufficient"] is True


def test_unanchored_package_is_not_sufficient(hub):
    seed_incident_offer(hub)
    contract = hub.get_context_contract(OWNER, "help me plan dinner")
    assert contract["situation"] is None
    assert contract["sufficient"] is False
    assert contract["goals"] == []
    assert contract["decisions"] == []


def test_required_overflow_marks_not_sufficient(hub):
    seed = seed_incident_offer(hub)
    pid = seed["incident"]["id"]
    for i in range(21):
        hub.create(
            "goal",
            {
                "title": f"Incident follow-up {i}",
                "status": "open",
                "project_id": pid,
            },
        )
    contract = hub.get_context_contract(OWNER, "continue the incident")
    assert contract["situation"]["project_id"] == pid
    assert len(contract["goals"]) <= 20
    assert contract["sufficient"] is False
    assert any(note["category"] == "over_cap" for note in contract["omissions"])
    assert not any(ref["type"] == "goal" for ref in contract.get("references") or [])


def test_overlapping_memory_overflow_is_over_cap_not_references(hub):
    seed = seed_incident_offer(hub)
    pid = seed["incident"]["id"]
    extra = [
        hub.create(
            "memory",
            {
                "statement": f"Incident log note {i} about the checkout outage",
                "kind": "semantic",
                "project_id": pid,
            },
        )
        for i in range(15)
    ]
    contract = hub.get_context_contract(OWNER, "continue the incident")
    assert len(contract["memories"]) <= 10
    extra_ids = {row["id"] for row in extra}
    leaked = extra_ids & _reference_ids(contract)
    assert not leaked
    assert any(note["category"] == "over_cap" for note in contract["omissions"])


def test_work_grant_excludes_northwind_offer(hub):
    seed = seed_incident_offer(hub)
    worker = _pair(hub, "work-agent")
    personal = _pair(hub, "personal-agent")
    hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": seed["incident"]["id"]},
        "private",
    )
    hub.create_grant(
        personal["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": seed["offer"]["id"]},
        "private",
    )
    work_c = hub.get_context_contract(worker["connection_id"], "continue the incident")
    offer_c = hub.get_context_contract(personal["connection_id"], "continue the offer")
    work_ids = {
        item["ref"]["id"]
        for sec in ("goals", "memories", "decisions", "preferences", "constraints")
        for item in work_c[sec]
    }
    work_ids |= _reference_ids(work_c)
    assert work_c["situation"]["project_id"] == seed["incident"]["id"]
    assert seed["northwind"]["id"] not in work_ids
    assert seed["keep_quiet"]["id"] not in work_ids
    assert "Northwind" not in str(work_c["situation"])
    blob = _omission_blob(work_c)
    assert "Northwind" not in blob
    assert seed["offer"]["id"] not in blob
    assert offer_c["situation"]["project_id"] == seed["offer"]["id"]
    assert seed["rollback"]["id"] not in {item["ref"]["id"] for item in offer_c["decisions"]}
    nosy = hub.get_context_contract(worker["connection_id"], "continue the offer")
    assert nosy["situation"] is None or nosy["situation"]["project_id"] != seed["offer"]["id"]
    stored = hub.get(seed["offer"]["id"])
    assert stored["title"] == "Northwind offer"


def test_private_ceiling_withholds_last_four(hub):
    seed = seed_incident_offer(hub)
    worker = _pair(hub, "work-agent")
    hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": seed["incident"]["id"]},
        "private",
    )
    contract = hub.get_context_contract(worker["connection_id"], "continue the incident")
    dumped = str(contract)
    assert "4242" not in dumped
    assert seed["last_four"]["id"] not in {item["ref"]["id"] for item in contract["memories"]}
    assert seed["last_four"]["id"] not in _reference_ids(contract)
    ceiling = [
        note for note in contract["omissions"] if note["category"] == "classification_ceiling"
    ]
    assert ceiling
    blob = _omission_blob(contract)
    assert "4242" not in blob
    assert seed["last_four"]["id"] not in blob
    assert all(set(note) <= {"category", "label", "count"} for note in contract["omissions"])


def test_revoked_work_connection_keeps_incident(hub):
    seed = seed_incident_offer(hub)
    worker = _pair(hub, "work-agent")
    grant = hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "memory.retrieve"],
        {"project": seed["incident"]["id"]},
        "private",
    )
    hub.revoke_grant(grant["id"])
    stored = hub.get(grant["id"])
    assert stored["status"] == GrantStatus.REVOKED.value
    with pytest.raises((PolicyDenied, Revoked)):
        hub.get_context_contract(worker["connection_id"], "continue the incident")
    still = hub.get(seed["incident"]["id"])
    assert still["title"] == "Checkout incident"

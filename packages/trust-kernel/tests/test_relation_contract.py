from pch_core.service import OWNER
from pch_core.testing.trip_seed import seed_trip


def _visa_and_links(hub, trip_id: str) -> dict:
    visa = hub.create("project", {"title": "Visa renewal", "charter": "Renew travel visa", "status": "active"})
    person_id = hub.person_id()
    depends = hub.create_relation(trip_id, visa["id"], "depends_on")
    blocked = hub.create_relation(visa["id"], person_id, "blocked_by")
    return {"visa": visa, "depends": depends, "blocked": blocked, "person_id": person_id}


def test_depends_on_in_package(hub):
    seed = seed_trip(hub)
    trip_id = seed["project"]["id"]
    links = _visa_and_links(hub, trip_id)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    types = {row["relation_type"] for row in contract["relations"]}
    assert "depends_on" in types
    depends = next(row for row in contract["relations"] if row["relation_type"] == "depends_on")
    assert depends["from"]["id"] == trip_id
    assert depends["to"]["id"] == links["visa"]["id"]
    assert depends["from"]["summary"] == "Europe Trip"
    goal_ids = {g["ref"]["id"] for g in contract["goals"]}
    assert seed["goal"]["id"] in goal_ids
    assert not any(row["relation_type"] == "owned_by" for row in contract["relations"])


def test_one_hop_blocked_by(hub):
    seed = seed_trip(hub)
    trip_id = seed["project"]["id"]
    links = _visa_and_links(hub, trip_id)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    blocked = next(row for row in contract["relations"] if row["relation_type"] == "blocked_by")
    assert blocked["from"]["id"] == links["visa"]["id"]
    assert blocked["to"]["id"] == links["person_id"]


def test_unset_assembles_without_inventing(hub):
    seed = seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert contract["situation"]["project_id"] == seed["project"]["id"]
    assert contract["relations"] == []
    dumped = str(contract).lower()
    assert "depends_on" not in dumped
    assert "blocked_by" not in dumped


def test_remove_then_next_contract(hub):
    seed = seed_trip(hub)
    trip_id = seed["project"]["id"]
    links = _visa_and_links(hub, trip_id)
    first = hub.get_context_contract(OWNER, "continue planning the trip")
    assert {row["id"] for row in first["relations"]} >= {links["depends"]["id"], links["blocked"]["id"]}
    hub.delete_relation(links["blocked"]["id"])
    second = hub.get_context_contract(OWNER, "continue planning the trip")
    assert all(row["id"] != links["blocked"]["id"] for row in second["relations"])
    assert any(row["id"] == links["depends"]["id"] for row in second["relations"])

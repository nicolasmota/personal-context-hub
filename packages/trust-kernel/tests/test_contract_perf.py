import time

import pytest
from pch_core.service import OWNER
from pch_core.testing.trip_seed import seed_trip


@pytest.mark.perf
def test_contract_assembly_under_two_seconds(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    hub.patch(
        pid,
        {
            "operational_phase": "deciding",
            "current_step": "rank two remaining itineraries",
            "situation_intent": "choose next itinerary",
        },
        None,
    )
    visa = hub.create(
        "project", {"title": "Visa renewal", "charter": "Renew travel visa", "status": "active"}
    )
    hub.create_relation(pid, visa["id"], "depends_on")
    hub.create_relation(visa["id"], hub.person_id(), "blocked_by")
    for i in range(2000):
        hub.create(
            "memory",
            {"statement": f"background fact {i} unrelated to cooking", "kind": "semantic"},
        )
        if i < 50:
            hub.create(
                "memory",
                {
                    "statement": f"travel packing item {i} for the Europe trip",
                    "kind": "semantic",
                    "project_id": pid,
                    "valid_from": "2020-01-01T00:00:00Z",
                    "valid_until": "2021-01-01T00:00:00Z",
                },
            )
    t0 = time.perf_counter()
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    elapsed = time.perf_counter() - t0
    assert contract["situation"]["project_id"] == pid
    assert contract["situation"]["operational_phase"] == "deciding"
    assert any(row["relation_type"] == "depends_on" for row in contract["relations"])
    assert elapsed < 2.0

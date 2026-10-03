from pch_core.service import OWNER
from pch_core.testing.trip_seed import seed_trip


def test_phase_in_situation_not_shared_state(hub):
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
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    situation = contract["situation"]
    assert situation["operational_phase"] == "deciding"
    assert situation["current_step"] == "rank two remaining itineraries"
    assert situation["situation_intent"] == "choose next itinerary"
    assert situation["status"] == "active"
    handoffs = [
        item["body"] for item in contract["state"] if item["body"].get("key") == "trip.phase"
    ]
    assert handoffs
    assert handoffs[0]["value"] == "comparing itineraries"
    assert situation["operational_phase"] != handoffs[0]["value"]


def test_unset_assembles_without_inventing(hub):
    seed = seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert contract["situation"]["project_id"] == seed["project"]["id"]
    assert contract["situation"]["operational_phase"] is None
    assert contract["situation"]["situation_intent"] is None
    assert contract["situation"]["current_step"] is None
    blob = str(contract).lower()
    assert "deciding" not in blob


def test_intent_not_action_intent(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    hub.patch(pid, {"situation_intent": "choose next itinerary"}, None)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    action = hub.propose_action(
        "owner",
        "send_message",
        "book the hotel tonight",
        {},
        [],
        "k-book-hotel",
        contract_id=contract["contract_id"],
    )
    assert contract["situation"]["situation_intent"] == "choose next itinerary"
    assert contract["situation"]["situation_intent"] != action["summary_human"]
    assert contract["situation"]["situation_intent"] != seed["goal"]["title"]


def test_patch_then_next_contract(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    hub.patch(
        pid,
        {"operational_phase": "deciding", "situation_intent": "choose next itinerary"},
        None,
    )
    first = hub.get_context_contract(OWNER, "continue planning the trip")
    assert first["situation"]["operational_phase"] == "deciding"
    hub.patch(
        pid,
        {"operational_phase": "executing", "situation_intent": "pick a hotel tonight"},
        None,
    )
    second = hub.get_context_contract(OWNER, "continue planning the trip")
    assert second["situation"]["operational_phase"] == "executing"
    assert second["situation"]["situation_intent"] == "pick a hotel tonight"
    assert second["situation"]["situation_intent"] != "choose next itinerary"


def test_goal_overlay_step_and_intent(hub):
    seed = seed_trip(hub)
    pid = seed["project"]["id"]
    gid = seed["goal"]["id"]
    hub.patch(
        pid,
        {
            "operational_phase": "deciding",
            "current_step": "from project",
            "situation_intent": "from project",
        },
        None,
    )
    hub.patch(
        gid,
        {
            "current_step": "rank two remaining itineraries",
            "situation_intent": "choose next itinerary",
        },
        None,
    )
    contract = hub.get_context_contract(OWNER, "continue planning the trip", subject_ref=gid)
    assert contract["situation"]["project_id"] == pid
    assert contract["situation"]["operational_phase"] == "deciding"
    assert contract["situation"]["current_step"] == "rank two remaining itineraries"
    assert contract["situation"]["situation_intent"] == "choose next itinerary"

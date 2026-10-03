import pytest
from pch_core.errors import NotFound, ValidationFailed
from pch_core.service import OWNER
from pch_core.testing.spicy_seed import seed_spicy
from pch_core.testing.trip_seed import seed_trip


def test_supersede_keeps_predecessor_historical(hub):
    seed = seed_spicy(hub)
    old_id = seed["preference"]["id"]
    result = hub.supersede(old_id, {"value": "like", "rationale": "I now like spicy food"})
    pred = result["predecessor"]
    succ = result["successor"]
    assert pred["id"] == old_id
    assert pred["value"] == "dislike"
    assert pred["valid_until"]
    assert pred.get("tombstone") is not True
    assert succ["key"] == "food.spicy"
    assert succ["value"] == "like"
    assert succ["valid_until"] is None
    assert succ["id"] != old_id
    listed = hub.list("preference")
    ids = {row["id"] for row in listed}
    assert old_id in ids
    assert succ["id"] in ids


def test_create_second_current_same_key_rejected(hub):
    seed_spicy(hub)
    with pytest.raises(ValidationFailed):
        hub.create("preference", {"key": "food.spicy", "value": "like"})


def test_patch_value_is_not_change_of_mind(hub):
    seed = seed_spicy(hub)
    old_id = seed["preference"]["id"]
    patched = hub.patch(old_id, {"value": "dislike-typo-fix"}, if_match=None)
    assert patched["id"] == old_id
    assert patched["version"] == 2
    current = [p for p in hub.list("preference") if p["key"] == "food.spicy"]
    assert len(current) == 1


def test_overlapping_current_keys_conflict(hub):
    seed_trip(hub)
    contract = hub.get_context_contract(OWNER, "continue planning the trip")
    assert any(c["reason"] == "preference_key_collision" for c in contract["conflicts"])


def test_retract_never_true_excluded(hub):
    seed = seed_spicy(hub)
    oid = seed["preference"]["id"]
    retracted = hub.retract_never_true(oid)
    assert retracted["never_true"] is True
    listed = hub.list_truth("preference")
    assert oid not in {row["id"] for row in listed}
    contract = hub.get_context_contract(OWNER, "plan dinner this week")
    assert not any(p["ref"]["id"] == oid for p in contract["preferences"])
    with pytest.raises(NotFound):
        hub.get(oid)
    forensic = hub.get(oid, include_deleted=True)
    assert forensic["never_true"] is True
    assert forensic["tombstone"] is True


def test_as_of_reconstructs_prior_current(hub):
    seed = seed_spicy(hub)
    hub.patch(seed["preference"]["id"], {"valid_from": "2026-01-01T00:00:00Z"}, None)
    hub.supersede(seed["preference"]["id"], {"value": "like"})
    past = hub.get_context_contract(OWNER, "plan dinner this week", as_of="2026-06-01T00:00:00Z")
    now = hub.get_context_contract(OWNER, "plan dinner this week")
    past_vals = [p["body"]["value"] for p in past["preferences"] if p["body"].get("key") == "food.spicy"]
    now_vals = [p["body"]["value"] for p in now["preferences"] if p["body"].get("key") == "food.spicy"]
    assert past_vals == ["dislike"]
    assert now_vals == ["like"]

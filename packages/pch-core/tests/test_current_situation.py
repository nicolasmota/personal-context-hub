from __future__ import annotations

from pch_core.testing.trip_seed import seed_trip

HOME_PURPOSE = "what matters now"


def test_current_situation_empty_vault(hub):
    body = hub.current_situation()
    assert body == {"project": None, "contract": None}


def test_current_situation_anchors_live_trip(hub):
    seed = seed_trip(hub)
    hub.patch(
        seed["project"]["id"],
        {
            "operational_phase": "deciding",
            "situation_intent": "choose the city",
        },
        None,
    )
    body = hub.current_situation()
    project = body["project"]
    contract = body["contract"]
    assert project["id"] == seed["project"]["id"]
    assert contract["purpose"] == HOME_PURPOSE
    assert contract["situation"]["project_id"] == seed["project"]["id"]
    assert contract["situation"]["title"] == "Europe Trip"
    assert contract["situation"]["operational_phase"] == "deciding"
    assert any("10-day" in g["body"].get("title", "") for g in contract["goals"])


def test_current_situation_prefers_operational_over_newer_idle(hub):
    live = hub.create(
        "project",
        {
            "title": "Europe Trip",
            "charter": "ten days",
            "status": "active",
            "operational_phase": "deciding",
        },
    )
    hub.create(
        "project",
        {"title": "Weekly chores", "charter": "inbox zero", "status": "active"},
    )
    body = hub.current_situation()
    assert body["project"]["id"] == live["id"]
    assert body["contract"]["situation"]["title"] == "Europe Trip"


def test_current_situation_skips_archived(hub):
    archived = hub.create(
        "project",
        {
            "title": "Old trip",
            "charter": "done last year",
            "status": "active",
            "operational_phase": "deciding",
        },
    )
    hub.patch(archived["id"], {"status": "archived"}, None)
    current = hub.create(
        "project",
        {"title": "Visa renewal", "charter": "papers", "status": "active"},
    )
    body = hub.current_situation()
    assert body["project"]["id"] == current["id"]
    assert body["contract"]["situation"]["title"] == "Visa renewal"

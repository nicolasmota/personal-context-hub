from __future__ import annotations

from typing import Any

from pch_core.ids import new_id
from pch_core.service import Hub


def seed_trip(hub: Hub) -> dict[str, Any]:
    """Seed the VISION killer-demo vault: a 10-day trip for two, Amsterdam vs London."""
    project = hub.create(
        "project",
        {
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two. Candidates: Amsterdam and London.",
            "status": "active",
        },
    )
    pid = project["id"]
    goal = hub.create(
        "goal",
        {
            "title": "Plan 10-day trip for two",
            "outcome": "Chosen itinerary and bookings",
            "status": "open",
            "project_id": pid,
        },
    )
    budget = hub.create(
        "preference",
        {
            "key": "travel.budget",
            "value": "budget-sensitive",
            "rationale": "Keep the trip affordable",
            "project_id": pid,
        },
    )
    red_eye = hub.create(
        "preference",
        {
            "key": "flights.red_eye",
            "value": "avoid",
            "rationale": "No red-eye flights",
            "project_id": pid,
        },
    )
    overlap = {
        **{k: v for k, v in red_eye.items() if k != "id"},
        "id": new_id("preference"),
        "value": "ok-if-cheaper",
        "rationale": "Conflicting preference for tests",
        "version": 1,
    }
    with hub.engine.tx():
        red_eye_ok = hub.store.put(overlap, new=True)
    travelers = hub.create(
        "memory",
        {
            "statement": "Two travelers planning a 10-day Europe trip",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    amsterdam = hub.create(
        "memory",
        {
            "statement": "Amsterdam is a live destination candidate",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    london = hub.create(
        "memory",
        {
            "statement": "London is a destination candidate",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    comparing = hub.create(
        "decision",
        {
            "title": "Destination shortlist",
            "chosen_option": "",
            "alternatives": ["Amsterdam", "London"],
            "rationale": "Still comparing itineraries",
            "project_id": pid,
        },
    )
    constraint = hub.create(
        "commitment",
        {
            "title": "Stay within travel budget",
            "status": "open",
            "project_id": pid,
        },
    )
    state = hub.set_state("trip.phase", "comparing itineraries", 86_400, "shared", "owner")
    return {
        "project": project,
        "goal": goal,
        "budget": budget,
        "red_eye": red_eye,
        "red_eye_ok": red_eye_ok,
        "travelers": travelers,
        "amsterdam": amsterdam,
        "london": london,
        "comparing": comparing,
        "constraint": constraint,
        "state": state,
    }


def drop_london(hub: Hub, seed: dict[str, Any]) -> dict[str, Any]:
    """Record the person's correction: London is dropped, Amsterdam is live."""
    return hub.create(
        "decision",
        {
            "title": "Dropped London",
            "chosen_option": "Amsterdam",
            "alternatives": ["London"],
            "rationale": "Person dropped London",
            "status": "rejected",
            "project_id": seed["project"]["id"],
        },
    )

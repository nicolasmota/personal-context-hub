from __future__ import annotations

from typing import Any

from pch_core.service import Hub

SHARED = "Monday deadline for the token and deploy."


def seed_incident_offer(hub: Hub) -> dict[str, Any]:
    """Checkout incident (work) plus Northwind offer (personal).

    Shared everyday words live in both charters so a token dump mixes lives.
    Rye-bread notes have no incident wording. Last-four is sensitive.
    """
    incident = hub.create(
        "project",
        {
            "title": "Checkout incident",
            "charter": f"Restore checkout. {SHARED}",
            "status": "active",
        },
    )
    iid = incident["id"]
    goal = hub.create(
        "goal",
        {
            "title": "Restore checkout",
            "outcome": "Checkout accepts payments again",
            "status": "open",
            "project_id": iid,
        },
    )
    rollback = hub.create(
        "decision",
        {
            "title": "Incident mitigation",
            "chosen_option": "rollback v2.4",
            "alternatives": ["forward-fix", "scale the cache"],
            "rationale": "Person chose rollback, not a forward-fix; scale the cache is discarded",
            "project_id": iid,
        },
    )
    status_page = hub.create(
        "commitment",
        {
            "title": "Publish status page by 18:00",
            "status": "open",
            "due_at": "2026-09-15T18:00:00Z",
            "project_id": iid,
        },
    )
    rye = [
        hub.create(
            "memory",
            {
                "statement": f"I prefer rye bread at the gym offsite {i}",
                "kind": "semantic",
                "project_id": iid,
            },
        )
        for i in range(10)
    ]
    last_four = hub.create(
        "memory",
        {
            "statement": "Incident payment token last-four 4242",
            "kind": "semantic",
            "project_id": iid,
            "classification": "sensitive",
        },
    )
    offer = hub.create(
        "project",
        {
            "title": "Northwind offer",
            "charter": f"Staff engineer loop at Northwind. {SHARED}",
            "status": "active",
        },
    )
    oid = offer["id"]
    northwind = hub.create(
        "decision",
        {
            "title": "Employer loop",
            "chosen_option": "Northwind",
            "alternatives": ["Contoso"],
            "rationale": "Northwind is live; Contoso is discarded. Do not tell the employer.",
            "project_id": oid,
        },
    )
    keep_quiet = hub.create(
        "commitment",
        {
            "title": "Do not tell the employer about the offer",
            "status": "open",
            "project_id": oid,
        },
    )
    return {
        "incident": incident,
        "goal": goal,
        "rollback": rollback,
        "status_page": status_page,
        "rye": rye,
        "last_four": last_four,
        "offer": offer,
        "northwind": northwind,
        "keep_quiet": keep_quiet,
    }

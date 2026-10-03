from __future__ import annotations

from typing import Any

from pch_core.service import Hub


def seed_spicy(hub: Hub) -> dict[str, Any]:
    """Seed a dinner situation with a current dislike of spicy food."""
    project = hub.create(
        "project",
        {
            "title": "Weeknight Dinners",
            "charter": "Plan dinner this week",
            "status": "active",
        },
    )
    pid = project["id"]
    goal = hub.create(
        "goal",
        {
            "title": "Plan dinner this week",
            "outcome": "A meal the person will enjoy",
            "status": "open",
            "project_id": pid,
        },
    )
    preference = hub.create(
        "preference",
        {
            "key": "food.spicy",
            "value": "dislike",
            "rationale": "I didn't like spicy food",
            "project_id": pid,
        },
    )
    memory = hub.create(
        "memory",
        {
            "statement": "I don't like spicy food",
            "kind": "semantic",
            "project_id": pid,
            "subject_ref": preference["id"],
        },
    )
    return {
        "project": project,
        "goal": goal,
        "preference": preference,
        "memory": memory,
    }

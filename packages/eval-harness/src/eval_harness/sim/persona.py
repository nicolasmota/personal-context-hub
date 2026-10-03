from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pch_lab.sim.refuse import FORBIDDEN_ACTIONS, SimRefused

PERSONA_DIR = Path(__file__).parent / "personas"
ALLOWED_ACTIONS = frozenset(
    {
        "create",
        "supersede",
        "search",
        "get_context_contract",
        "brief",
        "propose_memory",
        "decide_proposal",
    }
)
QUERY_ACTIONS = frozenset({"search", "get_context_contract"})


def _iso(day: int, hour: int = 9) -> str:
    return f"2026-06-{day:02d}T{hour:02d}:00:00Z"


def _tick(
    seq: int,
    simulated_at: str,
    role: str,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "seq": seq,
        "simulated_at": simulated_at,
        "role": role,
        "action": action,
        "input": payload,
        "via": "in_process_pair",
        "status": "pending",
        "result": None,
        "error": None,
    }


def _labels() -> list[str]:
    return ["sim", "persona:lived-stretch"]


def compile_lived_stretch() -> list[dict[str, Any]]:
    ticks: list[dict[str, Any]] = []
    seq = 1

    def add(day: int, hour: int, role: str, action: str, payload: dict[str, Any]) -> None:
        nonlocal seq
        ticks.append(_tick(seq, _iso(day, hour), role, action, payload))
        seq += 1

    add(
        1,
        8,
        "owner",
        "create",
        {
            "type": "project",
            "key": "trip",
            "body": {
                "title": "Europe Trip",
                "charter": "Plan a 10-day travel trip for two. Candidates: Amsterdam and London.",
                "status": "active",
                "operational_phase": "planning",
                "situation_intent": "choose next itinerary",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        8,
        "owner",
        "create",
        {
            "type": "project",
            "key": "work",
            "body": {
                "title": "Q3 Planning",
                "charter": "Quarterly delivery roadmap at work.",
                "status": "active",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        9,
        "owner",
        "create",
        {
            "type": "goal",
            "body": {
                "title": "Plan 10-day trip for two",
                "outcome": "Chosen itinerary and bookings",
                "status": "open",
                "project_key": "trip",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        9,
        "owner",
        "create",
        {
            "type": "goal",
            "body": {
                "title": "Ship Q3 milestones",
                "outcome": "Roadmap agreed",
                "status": "open",
                "project_key": "work",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        10,
        "owner",
        "create",
        {
            "type": "commitment",
            "body": {
                "title": "Hold passport renewal appointment",
                "status": "open",
                "project_key": "trip",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        10,
        "owner",
        "create",
        {
            "type": "commitment",
            "body": {
                "title": "Send Q3 draft to manager",
                "status": "open",
                "project_key": "work",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        11,
        "owner",
        "create",
        {
            "type": "decision",
            "body": {
                "title": "Destination shortlist",
                "chosen_option": "Amsterdam",
                "alternatives": ["Amsterdam", "London"],
                "rationale": "Prefer canals and walkable center",
                "project_key": "trip",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        11,
        "owner",
        "create",
        {
            "type": "decision",
            "body": {
                "title": "Planning cadence",
                "chosen_option": "weekly review",
                "alternatives": ["daily standup", "weekly review"],
                "rationale": "Keep work planning light",
                "project_key": "work",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        12,
        "owner",
        "create",
        {
            "type": "preference",
            "body": {
                "key": "travel.budget",
                "value": "budget-sensitive",
                "rationale": "Keep the trip affordable",
                "project_key": "trip",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        12,
        "owner",
        "create",
        {
            "type": "preference",
            "body": {
                "key": "flights.red_eye",
                "value": "avoid",
                "rationale": "No red-eye flights",
                "project_key": "trip",
                "labels": _labels(),
            },
        },
    )
    add(
        1,
        13,
        "owner",
        "create",
        {
            "type": "preference",
            "key": "spicy",
            "body": {
                "key": "food.spicy",
                "value": "dislike",
                "rationale": "Used to avoid spicy food",
                "labels": _labels(),
            },
        },
    )
    extras = [
        "Two travelers planning a 10-day Europe trip",
        "We would rather walk than take taxis in the city",
        "Museum mornings are better than late nights",
        "Need a hotel near public transit",
    ]
    for statement in extras:
        add(
            1,
            14,
            "owner",
            "create",
            {
                "type": "memory",
                "body": {
                    "statement": statement,
                    "kind": "semantic",
                    "project_key": "trip",
                    "labels": _labels(),
                },
            },
        )

    for day in range(1, 15):
        add(
            day,
            18,
            "owner",
            "create",
            {
                "type": "memory",
                "body": {
                    "statement": f"Trip note day {day}: compared Amsterdam vs London lodging.",
                    "kind": "episodic",
                    "project_key": "trip",
                    "labels": _labels(),
                },
            },
        )
        add(
            day,
            19,
            "owner",
            "create",
            {
                "type": "memory",
                "body": {
                    "statement": f"Work note day {day}: sketched one Q3 milestone.",
                    "kind": "episodic",
                    "project_key": "work",
                    "labels": _labels(),
                },
            },
        )
        if day in {3, 6, 9, 12}:
            add(
                day,
                20,
                "assistant",
                "search",
                {"query": "Amsterdam hotel", "purpose": "continue planning the trip"},
            )
        if day in {4, 7, 10, 13}:
            add(
                day,
                20,
                "assistant",
                "get_context_contract",
                {"purpose": "continue planning the trip"},
            )

    add(
        8,
        15,
        "owner",
        "supersede",
        {"key": "spicy", "body": {"value": "like", "rationale": "I now like spicy food"}},
    )
    add(
        10,
        16,
        "assistant",
        "propose_memory",
        {
            "body": {
                "statement": "Prefer canal-side evening walks in Amsterdam",
                "kind": "semantic",
                "project_key": "trip",
            }
        },
    )
    add(
        11,
        16,
        "assistant",
        "propose_memory",
        {
            "body": {
                "statement": "Q3 planning should stay on one shared outline",
                "kind": "semantic",
                "project_key": "work",
            }
        },
    )
    add(
        14,
        21,
        "assistant",
        "search",
        {"query": "Europe Trip Amsterdam", "purpose": "continue planning the trip"},
    )
    add(14, 21, "assistant", "get_context_contract", {"purpose": "continue planning the trip"})
    add(14, 21, "assistant", "get_context_contract", {"purpose": "continue planning the trip"})
    add(14, 22, "assistant", "brief", {"project_key": "trip"})
    add(
        14,
        22,
        "assistant",
        "search",
        {"query": "budget-sensitive travel", "purpose": "continue planning the trip"},
    )
    add(14, 22, "assistant", "get_context_contract", {"purpose": "continue planning the trip"})
    return ticks


def compile_persona(persona_id: str) -> list[dict[str, Any]]:
    if persona_id != "lived-stretch":
        raise SimRefused("unknown_persona", f"unknown persona {persona_id}")
    path = PERSONA_DIR / "lived-stretch.json"
    if path.is_file():
        spec = json.loads(path.read_text(encoding="utf-8"))
        if spec.get("id") != "lived-stretch":
            raise SimRefused("unknown_persona")
    ticks = compile_lived_stretch()
    validate_compiled(ticks)
    return ticks


def validate_compiled(ticks: list[dict[str, Any]]) -> None:
    actions = [t["action"] for t in ticks]
    if any(a in FORBIDDEN_ACTIONS for a in actions):
        raise SimRefused("forbidden_action")
    if any(a not in ALLOWED_ACTIONS for a in actions):
        raise SimRefused("forbidden_action")
    creates = [t for t in ticks if t["action"] == "create"]
    types = {t["input"]["type"] for t in creates}
    if len(creates) < 40:
        raise SimRefused("volume", "persona compiles below 40 durable creates")
    if not {"project", "preference", "memory"}.issubset(types):
        raise SimRefused("volume", "persona missing required kinds")
    if not types & {"goal", "commitment", "decision"}:
        raise SimRefused("volume", "persona needs a fourth kind")
    queries = [t for t in ticks if t["action"] in QUERY_ACTIONS]
    if len(queries) < 10:
        raise SimRefused("volume", "persona needs at least 10 query ticks")


def dump_ticks(persona_id: str) -> list[dict[str, Any]]:
    return compile_persona(persona_id)

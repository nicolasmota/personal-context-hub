from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pch_core.service import OWNER, Hub
from pch_core.testing.spicy_seed import seed_spicy
from pch_core.testing.trip_seed import drop_london, seed_trip

EVAL_LABELS = ["eval", "test-tooling"]
EVAL_RUNTIME = {"harness": "pch-lab-eval"}
COST_BUDGET = 2.0


def _case(case_id: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"id": case_id, "pass": passed, "detail": detail}


def _pair(hub: Hub, name: str, project_id: str | None = None) -> dict[str, Any]:
    link = hub.mint_link(name, labels=EVAL_LABELS)
    paired = hub.pair(link["code"], runtime_info=dict(EVAL_RUNTIME))
    selectors = {"project": project_id} if project_id else None
    hub.create_grant(
        paired["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        selectors,
        "private",
    )
    return paired


def _leak(contract: dict[str, Any], trip_id: str) -> bool:
    dumped = str(contract)
    return "Europe" in dumped or trip_id in dumped


def run_eval(data_dir: Path | None = None) -> dict[str, Any]:
    owned = TemporaryDirectory() if data_dir is None else None
    root = Path(data_dir) if data_dir is not None else Path(owned.name)
    hub = Hub(root / "vault", plain=True)
    hub.setup("Eval")
    hub.patch(hub.person_id(), {"labels": list(EVAL_LABELS)}, None)
    try:
        return _run(hub)
    finally:
        hub.close()
        if owned is not None:
            owned.cleanup()


def _run(hub: Hub) -> dict[str, Any]:
    trip = seed_trip(hub)
    trip_id = trip["project"]["id"]
    t0 = time.perf_counter()
    killer = hub.get_context_contract(OWNER, "continue planning the trip")
    cost = time.perf_counter() - t0
    accuracy = killer.get("situation", {}).get("project_id") == trip_id
    drop_london(hub, trip)
    after = hub.get_context_contract(OWNER, "continue planning the trip")
    chosen = [d.get("body", {}).get("chosen_option") for d in after.get("decisions") or []]
    correction = "London" not in chosen and "Amsterdam" in chosen
    conflict = any(
        c.get("reason") == "preference_key_collision" for c in (killer.get("conflicts") or [])
    )
    killer_ok = accuracy and conflict and cost < COST_BUDGET

    spicy = seed_spicy(hub)
    hub.patch(spicy["preference"]["id"], {"valid_from": "2026-01-01T00:00:00Z"}, None)
    hub.supersede(spicy["preference"]["id"], {"value": "like"})
    past = hub.get_context_contract(
        OWNER, "plan dinner this week", as_of="2026-06-01T00:00:00Z"
    )
    now = hub.get_context_contract(OWNER, "plan dinner this week")
    past_vals = [
        p["body"]["value"]
        for p in past.get("preferences") or []
        if p.get("body", {}).get("key") == "food.spicy"
    ]
    now_vals = [
        p["body"]["value"]
        for p in now.get("preferences") or []
        if p.get("body", {}).get("key") == "food.spicy"
    ]
    freshness = past_vals == ["dislike"] and now_vals == ["like"]

    work = hub.create(
        "project",
        {"title": "Work Roadmap", "charter": "Q3 delivery", "status": "active"},
    )
    worker = _pair(hub, "guest-work", work["id"])
    isolated = hub.get_context_contract(
        worker["connection_id"], "continue the work roadmap"
    )
    precision = not _leak(isolated, trip_id)

    one = _pair(hub, "guest-one", trip_id)
    two = _pair(hub, "guest-two", trip_id)
    a = hub.get_context_contract(one["connection_id"], "continue planning the trip")
    b = hub.get_context_contract(two["connection_id"], "continue planning the trip")
    portable = (
        a.get("situation", {}).get("project_id") == trip_id
        and b.get("situation", {}).get("project_id") == trip_id
    )
    hub.revoke_connection(one["connection_id"])
    still = hub.get(trip_id)
    revoke_kept = still.get("title") == "Europe Trip"

    cases = [
        _case("killer_demo", killer_ok, "" if killer_ok else "trip not selected or over budget"),
        _case(
            "temporal_conflict",
            freshness and conflict,
            "" if freshness and conflict else "freshness or conflict",
        ),
        _case("isolation", precision, "" if precision else "personal trip leaked"),
        _case(
            "runtime_switch",
            portable and revoke_kept,
            "" if portable and revoke_kept else "packages disagree or revoke deleted trip",
        ),
    ]
    metrics = {
        "retrieval_accuracy": accuracy,
        "precision": precision,
        "freshness": freshness,
        "conflict_resolution": conflict,
        "portability": portable,
        "user_correction": correction,
        "assembly_cost_seconds": cost,
    }
    bools = [v for k, v in metrics.items() if k != "assembly_cost_seconds"]
    all_pass = all(c["pass"] for c in cases) and all(bools) and cost < COST_BUDGET
    return {"cases": cases, "metrics": metrics, "all_pass": all_pass}

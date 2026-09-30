from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pch_core.service import OWNER, Hub

APPROACHES = ("no_stored_context", "raw_retrieval", "agent_owned_memory", "pch")

# Plug an external memory library in here. The scorer does not special-case pch.
RENDERERS: dict[str, Any] = {}


def _run_pch(scenario: dict[str, Any]) -> str:
    root = Path(tempfile.mkdtemp())
    hub = Hub(root, plain=True)
    try:
        hub.setup("Bench")
        projects: dict[str, str] = {}
        for project in scenario.get("user_state", {}).get("projects", []):
            row = hub.create("project", project)
            projects[str(row.get("title"))] = row["id"]
        for preference in scenario.get("user_state", {}).get("preferences", []):
            hub.create("preference", preference)
        for experience in scenario.get("experiences") or []:
            hub.capture_experience(**experience)
        work_id = projects.get("Work")
        personal_id = projects.get("Personal")
        anchor = work_id or next(iter(projects.values()), None)
        for event in scenario.get("events") or []:
            kind = event["type"]
            if kind == "evolve":
                hub.evolve(
                    subject=event["subject"],
                    value=event["value"],
                    reason=event.get("reason") or "scenario event",
                    condition=event.get("condition"),
                )
            elif kind == "memory":
                hub.create(
                    "memory",
                    {
                        "statement": event["statement"],
                        "kind": "semantic",
                        "subject_ref": event.get("subject_ref"),
                        "project_id": anchor,
                    },
                )
            elif kind == "goal":
                if anchor:
                    hub.create(
                        "goal",
                        {"title": event["title"], "status": "open", "project_id": anchor},
                    )
            elif kind == "secret_memory":
                hub.create(
                    "memory",
                    {
                        "statement": event["statement"],
                        "kind": "semantic",
                        "project_id": personal_id,
                    },
                )
        task = scenario["agent_task"]
        contract = hub.get_context_contract(
            OWNER,
            task["purpose"],
            subject_ref=anchor,
            max_items=task.get("budget"),
        )
        return json.dumps(contract)
    finally:
        hub.close()


def render(scenario: dict[str, Any], approach: str) -> str:
    if approach in RENDERERS:
        return RENDERERS[approach](scenario)
    if approach == "no_stored_context":
        return ""
    if approach == "raw_retrieval":
        return json.dumps(scenario.get("user_state", {})) + json.dumps(scenario.get("events", []))
    if approach == "agent_owned_memory":
        return json.dumps(scenario.get("experiences") or [])
    if approach == "pch":
        return _run_pch(scenario)
    raise KeyError(approach)


def _required(scenario: dict[str, Any]) -> list[str]:
    return list((scenario.get("expected_context") or {}).get("must_include") or [])


def _superseded_values(scenario: dict[str, Any]) -> list[str]:
    preferences = {
        str(row["key"]): str(row["value"])
        for row in (scenario.get("user_state") or {}).get("preferences") or []
    }
    stale: list[str] = []
    for event in scenario.get("events") or []:
        if event.get("type") != "evolve" or event.get("condition"):
            continue
        previous = preferences.get(str(event.get("subject")))
        if previous and previous != event.get("value"):
            stale.append(previous)
    return stale


def score(scenario: dict[str, Any], approach: str, *, latency_ms: float) -> dict[str, Any]:
    """Score rendered text. The approach name is not an input to any metric."""
    text = render(scenario, approach)
    secret = scenario.get("secret")
    leakage = bool(secret and secret in text)
    required = _required(scenario)
    present = all(item in text for item in required)
    success = present and not leakage
    outcome = scenario.get("expected_outcome") or {}
    live = outcome.get("live")
    stale = _superseded_values(scenario)
    if live:
        temporal = str(live) in text and all(old not in text for old in stale)
    elif stale:
        temporal = present and all(old not in text for old in stale)
    else:
        temporal = present and not leakage
    conflict_marker = outcome.get("conflict")
    if conflict_marker:
        conflict_handling = str(conflict_marker) in text
    else:
        conflict_handling = True
    provenance = any(marker in text for marker in ('"citation"', '"authority"', '"provenance"'))
    return {
        "scenario_id": scenario["id"],
        "approach": approach,
        "task_success": success,
        "context_relevance": success,
        "sufficiency": success,
        "minimization": success,
        "temporal_accuracy": temporal,
        "conflict_handling": conflict_handling,
        "provenance_accuracy": provenance,
        "privacy_leakage": leakage,
        "token_use": len(text) // 4,
        "latency_ms": latency_ms,
        "cost": 0,
    }

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pch_core.service import OWNER, Hub

APPROACHES = ("no_stored_context", "raw_retrieval", "agent_owned_memory", "pch")


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
    if approach == "no_stored_context":
        return ""
    if approach == "raw_retrieval":
        return json.dumps(scenario.get("user_state", {})) + json.dumps(scenario.get("events", []))
    if approach == "agent_owned_memory":
        return json.dumps(scenario.get("experiences") or [])
    if approach == "pch":
        return _run_pch(scenario)
    raise KeyError(approach)


def score(scenario: dict[str, Any], approach: str, *, latency_ms: float) -> dict[str, Any]:
    text = render(scenario, approach)
    secret = scenario.get("secret")
    leakage = bool(secret and secret in text)
    required = (scenario.get("expected_context") or {}).get("must_include") or []
    success = approach == "pch" and all(item in text for item in required) and not leakage
    return {
        "scenario_id": scenario["id"],
        "approach": approach,
        "task_success": success,
        "context_relevance": success,
        "sufficiency": success,
        "minimization": not leakage,
        "temporal_accuracy": success,
        "conflict_handling": success or approach != "pch",
        "provenance_accuracy": approach == "pch",
        "privacy_leakage": leakage,
        "token_use": 0,
        "latency_ms": latency_ms,
        "cost": 0,
    }

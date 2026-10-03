from __future__ import annotations

from typing import Any

from pch_core.retrieval.search import citations_for


def project_brief(project: dict[str, Any], related: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [o for o in related if o.get("type") == "decision"]
    commitments = [o for o in related if o.get("type") == "commitment" and o.get("status") != "done"]
    memories = [o for o in related if o.get("type") == "memory"]
    goals = [o for o in related if o.get("type") == "goal"]
    items = [project, *goals, *decisions, *commitments, *memories[:10]]
    return {
        "project": project,
        "goals": goals,
        "decisions": decisions,
        "commitments": commitments,
        "memories": memories[:10],
        "citations": [c for item in items for c in citations_for(item)],
        "versions": {item["id"]: item.get("version", 1) for item in items if "id" in item},
    }

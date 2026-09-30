from __future__ import annotations

import json
from typing import Any

_LIVE_SECTIONS = ("goals", "preferences", "memories", "decisions", "constraints", "state")
_OMISSION_KEYS = frozenset({"category", "label", "count"})


def superseded_values(scenario: dict[str, Any]) -> list[str]:
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


def _live_items(contract: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for name in _LIVE_SECTIONS:
        items.extend(contract.get(name) or [])
    return items


def _candidate_blob(candidate: dict[str, Any]) -> str:
    signals = " ".join(str(signal) for signal in candidate.get("signals") or [])
    return f"{candidate.get('excerpt') or ''} {signals}".lower()


def retrieval_judgment(
    candidates: list[dict[str, Any]], scenario: dict[str, Any], find_ms: float
) -> dict[str, Any]:
    expected = scenario.get("expected_context") or {}
    outcome = scenario.get("expected_outcome") or {}
    needles = [str(item) for item in expected.get("must_include") or []]
    marker = outcome.get("conflict")
    if marker is not None:
        needles = [item for item in needles if item != str(marker)]

    def matches(candidate: dict[str, Any]) -> bool:
        text = _candidate_blob(candidate)
        return any(needle.lower() in text for needle in needles)

    if needles:
        needed_items_found = all(
            any(needle.lower() in _candidate_blob(candidate) for candidate in candidates)
            for needle in needles
        )
    else:
        needed_items_found = True
    if not needles:
        needed_ranked_ahead = True
    else:
        seen_unneeded = False
        needed_ranked_ahead = True
        for candidate in candidates:
            if matches(candidate):
                if seen_unneeded:
                    needed_ranked_ahead = False
                    break
            else:
                seen_unneeded = True
    return {
        "needed_items_found": needed_items_found,
        "needed_ranked_ahead": needed_ranked_ahead,
        "find_ms": find_ms,
        "candidate_coverage": needed_items_found,
    }


def compilation_judgment(contract: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(contract)
    secret = scenario.get("secret")
    leakage = bool(secret and secret in text)
    required = [
        str(item) for item in (scenario.get("expected_context") or {}).get("must_include") or []
    ]
    present = all(item in text for item in required)
    omissions = list(contract.get("omissions") or [])
    omission_shape = all(set(note.keys()) <= _OMISSION_KEYS for note in omissions)
    items = _live_items(contract)
    outcome = scenario.get("expected_outcome") or {}
    marker = outcome.get("conflict")
    if marker:
        conflict_handling = str(marker) in text
    else:
        conflict_handling = True
    live = outcome.get("live")
    stale = superseded_values(scenario)
    live_text = json.dumps(items)
    if live:
        temporal_correct = str(live) in text and all(old not in text for old in stale)
    elif stale:
        temporal_correct = all(old not in live_text for old in stale)
    else:
        temporal_correct = True
    provenance_preserved = all(bool(item.get("citation")) for item in items) if items else True
    return {
        "sufficiency": present and bool(contract.get("sufficient")),
        "minimization": (not leakage) and omission_shape,
        "privacy_leakage": leakage,
        "policy_correct": (not leakage) and omission_shape,
        "authority_correct": all(
            item.get("authority") not in {"proposed", "agent_inferred"}
            or (item.get("ref") or {}).get("type") not in {"memory", "preference"}
            for item in items
        ),
        "conflict_handling": conflict_handling,
        "temporal_correct": temporal_correct,
        "provenance_preserved": provenance_preserved,
    }


def compilation_passed(judgment: dict[str, Any]) -> bool:
    return bool(
        judgment["sufficiency"]
        and judgment["minimization"]
        and judgment["policy_correct"]
        and judgment["authority_correct"]
        and judgment["conflict_handling"]
        and judgment["temporal_correct"]
        and judgment["provenance_preserved"]
        and not judgment["privacy_leakage"]
    )


def judge_override(secret: str, required: str) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = [
        {
            "item_id": "mem",
            "excerpt": required.lower(),
            "signals": [],
            "relevance": 1.0,
        }
    ]
    contract = {
        "sufficient": True,
        "omissions": [],
        "memories": [
            {
                "authority": "user_confirmed",
                "citation": [{"id": "mem", "role": "self"}],
                "body": {"statement": f"{required} {secret}"},
                "ref": {"id": "mem", "type": "memory", "summary": required},
            }
        ],
        "preferences": [],
        "decisions": [],
        "goals": [],
        "constraints": [],
        "state": [],
        "conflicts": [],
        "state_conflicts": [],
    }
    scenario = {
        "secret": secret,
        "expected_context": {"must_include": [required]},
        "expected_outcome": {},
    }
    return (
        retrieval_judgment(candidates, scenario, 1.0),
        compilation_judgment(contract, scenario),
    )

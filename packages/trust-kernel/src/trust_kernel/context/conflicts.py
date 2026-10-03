from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from trust_kernel.timeutil import row_is_current


def _condition(row: dict[str, Any]) -> str | None:
    text = str(row.get("condition") or "").strip()
    return text or None


def detect_state_conflicts(
    preferences: list[dict[str, Any]],
    memories: list[dict[str, Any]],
    *,
    at: datetime | None = None,
) -> list[dict[str, Any]]:
    moment = at or datetime.now(UTC)
    found: list[dict[str, Any]] = []

    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stale: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in memories:
        if row.get("tombstone") or row.get("never_true"):
            continue
        subject = str(row.get("subject_ref") or "").strip()
        if not subject:
            continue
        if row_is_current(row, moment):
            by_subject[subject].append(row)
        else:
            stale[subject].append(row)

    for subject, rows in by_subject.items():
        statements = {str(row.get("statement") or "") for row in rows}
        if len(rows) < 2 or len(statements) < 2:
            continue
        authorities = {str(row.get("authority") or "") for row in rows}
        if authorities == {"user_confirmed", "agent_inferred"}:
            resolution = "user_confirmed"
            status = "closed"
            detail = "the person's confirmation beats agent inference"
        else:
            resolution = "unresolved"
            status = "open"
            detail = "competing claims have no confirmed winner"
        found.append(
            {
                "subject": subject,
                "claim_ids": sorted(row["id"] for row in rows),
                "evidence_ids": [],
                "temporal_scope": {"valid_from": None, "valid_until": None},
                "resolution": resolution,
                "status": status,
                "detail": detail,
            }
        )

    for subject, old_rows in stale.items():
        current = by_subject.get(subject) or []
        if not current or not old_rows:
            continue
        found.append(
            {
                "subject": subject,
                "claim_ids": sorted(row["id"] for row in [*old_rows, *current]),
                "evidence_ids": [],
                "temporal_scope": {
                    "valid_from": old_rows[0].get("valid_from"),
                    "valid_until": current[0].get("valid_until"),
                },
                "resolution": "automated",
                "status": "closed",
                "detail": "a later value superseded a stale claim",
            }
        )

    pref_current: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pref_stale: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in preferences:
        if row.get("never_true"):
            continue
        key = str(row.get("key") or "")
        if not key:
            continue
        if row_is_current(row, moment):
            pref_current[key].append(row)
        else:
            pref_stale[key].append(row)

    for key, rows in pref_current.items():
        unconditional = [row for row in rows if _condition(row) is None]
        if len(unconditional) < 2:
            continue
        values = {repr(row.get("value")) for row in unconditional}
        if len(values) < 2:
            continue
        found.append(
            {
                "subject": key,
                "claim_ids": sorted(row["id"] for row in unconditional),
                "evidence_ids": [],
                "temporal_scope": {"valid_from": None, "valid_until": None},
                "resolution": "unresolved",
                "status": "open",
                "detail": "two current preferences disagree",
            }
        )

    for key, old_rows in pref_stale.items():
        current = [row for row in pref_current.get(key, []) if _condition(row) is None]
        if not current or not old_rows:
            continue
        found.append(
            {
                "subject": key,
                "claim_ids": sorted(row["id"] for row in [*old_rows, *current]),
                "evidence_ids": [],
                "temporal_scope": {
                    "valid_from": old_rows[0].get("valid_from"),
                    "valid_until": old_rows[0].get("valid_until"),
                },
                "resolution": "policy_based",
                "status": "closed",
                "detail": "the person's later statement superseded the earlier preference",
            }
        )
    return found

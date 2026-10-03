from __future__ import annotations

from datetime import UTC, datetime

from trust_kernel.ids import new_id
from trust_kernel.schema.grant import PRESETS, Capability, Grant, GrantStatus
from trust_kernel.timeutil import parse_instant


def grant_is_current(grant: Grant, at: datetime | None = None) -> bool:
    if grant.status != GrantStatus.ACTIVE:
        return False
    if not grant.expires_at:
        return True
    moment = at or datetime.now(UTC)
    return parse_instant(grant.expires_at) > moment


def grant_from_preset(
    connection_id: str,
    preset: str,
    selectors: dict[str, str] | None = None,
    classification_ceiling: str = "private",
) -> Grant:
    spec = PRESETS.get(preset, PRESETS["read_active_projects"])
    summary = spec["summary_human"]
    if selectors and selectors.get("project"):
        summary = f"Can read project {selectors['project']}"
    return Grant(
        id=new_id("grant"),
        connection_id=connection_id,
        capabilities=list(spec["capabilities"]),
        selectors=selectors or {},
        classification_ceiling=classification_ceiling,
        status=GrantStatus.ACTIVE,
        preset=preset,
        summary_human=summary,
    )


def grant_from_caps(
    connection_id: str,
    capabilities: list[str],
    selectors: dict[str, str] | None = None,
    classification_ceiling: str = "private",
    summary: str = "",
) -> Grant:
    parsed = [Capability(c) for c in capabilities]
    return Grant(
        id=new_id("grant"),
        connection_id=connection_id,
        capabilities=parsed,
        selectors=selectors or {},
        classification_ceiling=classification_ceiling,
        status=GrantStatus.ACTIVE,
        summary_human=summary or ", ".join(capabilities),
    )

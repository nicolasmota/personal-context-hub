from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pch_core.errors import ValidationFailed
from pch_core.ids import new_id
from pch_core.schema.manifest import ContextManifest, DisclosedRef, ManifestStatus


def build_manifest(
    connection_id: str,
    purpose: str,
    requested_capabilities: list[str],
    selectors: dict[str, str],
    entities: list[dict[str, Any]],
    redactions: list[str],
    ttl_seconds: int = 900,
) -> ContextManifest:
    if not purpose or not str(purpose).strip():
        raise ValidationFailed("purpose is required")
    if not requested_capabilities:
        raise ValidationFailed("requested_capabilities must be non-empty")
    expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    disclosed = [
        DisclosedRef(id=e["id"], type=e.get("type", ""), version=int(e.get("version", 1)))
        for e in entities
    ]
    citations = []
    for e in entities:
        for ref in e.get("source_refs") or []:
            citations.append({"object_id": e["id"], "source_id": ref})
    return ContextManifest(
        id=new_id("manifest"),
        connection_id=connection_id,
        purpose=purpose,
        requested_capabilities=requested_capabilities,
        selectors=selectors,
        disclosed_refs=disclosed,
        redaction_notices=redactions,
        expires_at=expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        status=ManifestStatus.ACTIVE,
        entities=entities,
        citations=citations,
    )

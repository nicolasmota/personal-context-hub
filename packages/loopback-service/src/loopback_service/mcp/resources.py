from __future__ import annotations

from pch_core.service import Hub


def profile_resource(hub: Hub, actor: str) -> dict:
    profiles = hub.list("profile")
    prefs = hub.list("preference")
    return {"profile": profiles[0] if profiles else {}, "preferences": prefs, "actor": actor}


def brief_resource(hub: Hub, project_id: str, actor: str) -> dict:
    return hub.brief(project_id, actor)


def self_resource(hub: Hub, actor: str) -> dict:
    grants = [g.model_dump(mode="json") for g in hub.grants_for(actor)]
    return {"connection_id": actor, "grants": grants}


def audit_resource(hub: Hub, actor: str) -> list[dict]:
    return hub.events(actor=actor)

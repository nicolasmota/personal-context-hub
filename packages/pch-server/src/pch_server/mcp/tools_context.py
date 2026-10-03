from __future__ import annotations

from typing import Any

from pch_core.errors import PolicyDenied
from pch_core.hub.const import OWNER
from pch_core.service import Hub


def attach_tools(mcp, hub: Hub) -> None:
    @mcp.tool()
    def search_personal_context(
        query: str, purpose: str, scope: dict[str, Any] | None = None
    ) -> dict:
        actor = mcp._current_actor  # set per-request
        project = (scope or {}).get("project")
        types = (scope or {}).get("types")
        type_ = types[0] if types else None
        return hub.search(query, type_=type_, project_id=project, actor=actor, purpose=purpose)

    @mcp.tool()
    def get_context_manifest(
        purpose: str,
        requested_capabilities: list[str],
        selectors: dict[str, str] | None = None,
        ttl_seconds: int = 900,
    ) -> dict:
        actor = mcp._current_actor
        return hub.create_manifest(
            actor, purpose, requested_capabilities, selectors or {}, ttl_seconds
        )

    @mcp.tool()
    def propose_memory(
        memory: dict, evidence_refs: list[str], retention: dict | None = None
    ) -> dict:
        actor = mcp._current_actor
        if retention:
            memory = {**memory, "retention": retention}
        return hub.propose_memory(memory, actor, evidence_refs)

    @mcp.tool()
    def get_context_contract(
        purpose: str = "",
        subject_ref: str | None = None,
        max_items: int | None = None,
        as_of: str | None = None,
    ) -> dict:
        actor = mcp._current_actor
        return hub.get_context_contract(actor, purpose, subject_ref, max_items, as_of)

    @mcp.tool()
    def propose_relation(from_id: str, to_id: str, relation_type: str) -> dict:
        actor = mcp._current_actor
        return hub.propose_relation(actor, from_id, to_id, relation_type)

    @mcp.tool()
    def explain_subject(subject: str, projection_id: str | None = None) -> dict:
        _owner_only(mcp)
        return hub.explain_subject(subject, projection_id)

    @mcp.tool()
    def source_impact(evidence_id: str) -> dict:
        _owner_only(mcp)
        return hub.source_impact(evidence_id)

    @mcp.tool()
    def proposal_status(proposal_id: str | None = None) -> dict:
        actor = mcp._current_actor
        rows = hub.list("proposal")
        if actor != OWNER:
            rows = [row for row in rows if row.get("submitted_by") == actor]
        if proposal_id:
            rows = [row for row in rows if row.get("id") == proposal_id]
        return {"proposals": rows}

    @mcp.tool()
    def request_action(
        kind: str,
        summary: str,
        contract_id: str,
        payload: dict | None = None,
        risk: str = "unspecified",
        reversible: bool = False,
        valid_until: str | None = None,
        limits: dict | None = None,
        idempotency_key: str = "request",
    ) -> dict:
        actor = mcp._current_actor
        return hub.propose_action(
            actor,
            kind,
            summary,
            payload or {},
            [],
            idempotency_key,
            contract_id,
            risk=risk,
            reversible=reversible,
            valid_until=valid_until,
            limits=limits,
        )

    @mcp.tool()
    def revoke_my_grant(grant_id: str) -> dict:
        actor = mcp._current_actor
        grant = hub.get(grant_id)
        if actor != OWNER and grant.get("connection_id") != actor:
            raise PolicyDenied("grant belongs to another recipient")
        return hub.revoke_grant(grant_id)

    @mcp.tool()
    def read_everything() -> dict:
        raise PolicyDenied("the whole personal record is not available")


def _owner_only(mcp) -> None:
    if mcp._current_actor != OWNER:
        raise PolicyDenied("owner only")

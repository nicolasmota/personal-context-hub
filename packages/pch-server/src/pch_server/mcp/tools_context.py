from __future__ import annotations

from typing import Any

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

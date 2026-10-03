from __future__ import annotations

from trust_kernel.schema.contract import (
    Citation,
    ContextContract,
    ContextQuery,
    ContractItem,
    StateConflictNote,
)
from trust_kernel.vault.objects import ObjectStore


def _enrich(item: ContractItem, store: ObjectStore) -> ContractItem:
    cites = list(item.citation)
    seen = {cite.id for cite in cites}
    for rel in store.list("relation"):
        if rel.get("status") != "live" or rel.get("from_id") != item.ref.id:
            continue
        if rel.get("relation_type") not in {"supported_by", "derived_from"}:
            continue
        target = rel.get("to_id")
        if target and target not in seen:
            cites.append(Citation(id=target, role=str(rel["relation_type"])))
            seen.add(target)
    for transition in store.list("state_transition"):
        if transition.get("subject_id") != item.ref.id:
            continue
        if transition["id"] not in seen:
            cites.append(Citation(id=transition["id"], role="transition"))
            seen.add(transition["id"])
        for evidence_id in transition.get("evidence_ids") or []:
            if evidence_id not in seen:
                cites.append(Citation(id=evidence_id, role="evidence"))
                seen.add(evidence_id)
    return item.model_copy(update={"citation": cites})


def _notes(store: ObjectStore) -> tuple[list[StateConflictNote], set[str]]:
    notes: list[StateConflictNote] = []
    hidden: set[str] = set()
    for row in store.list("state_conflict"):
        notes.append(
            StateConflictNote(
                id=row["id"],
                subject=str(row.get("subject") or ""),
                claim_ids=list(row.get("claim_ids") or []),
                evidence_ids=list(row.get("evidence_ids") or []),
                resolution=str(row.get("resolution") or "unresolved"),
                status=str(row.get("status") or "open"),
                detail=str(row.get("detail") or ""),
                temporal_scope=dict(row.get("temporal_scope") or {}),
            )
        )
        if row.get("status") == "open" and row.get("resolution") == "unresolved":
            hidden.update(row.get("claim_ids") or [])
    return notes, hidden


def finalize_contract(
    contract: ContextContract, store: ObjectStore, query: ContextQuery
) -> ContextContract:
    notes, hidden = _notes(store)

    def keep(items: list[ContractItem]) -> list[ContractItem]:
        return [_enrich(item, store) for item in items if item.ref.id not in hidden]

    return contract.model_copy(
        update={
            "goals": keep(contract.goals),
            "preferences": keep(contract.preferences),
            "memories": keep(contract.memories),
            "decisions": keep(contract.decisions),
            "constraints": keep(contract.constraints),
            "state": keep(contract.state),
            "state_conflicts": notes,
            "budget": query.max_items,
        }
    )

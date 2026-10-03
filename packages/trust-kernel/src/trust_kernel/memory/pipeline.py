from __future__ import annotations

import hashlib
from typing import Any

from pch_core.ids import new_id
from pch_core.memory.sensitivity import blocks_auto_accept
from pch_core.schema.conflict import Conflict, ConflictKind
from pch_core.schema.memory import Memory
from pch_core.schema.proposal import MemoryProposal, ProposalStatus
from pch_core.timeutil import now_iso


def statement_hash(statement: str) -> str:
    return hashlib.sha256(statement.strip().lower().encode()).hexdigest()


def evaluate_proposal(
    proposed: Memory,
    existing: list[dict[str, Any]],
    submitted_by: str,
    evidence_refs: list[str],
) -> tuple[MemoryProposal, list[Conflict]]:
    conflicts: list[Conflict] = []
    status = ProposalStatus.PENDING
    verdict = "needs_review"
    if blocks_auto_accept(proposed):
        verdict = "needs_review"
        status = ProposalStatus.PENDING
    h = statement_hash(proposed.statement)
    for item in existing:
        if item.get("type") != "memory":
            continue
        if statement_hash(item.get("statement") or "") == h:
            c = Conflict(
                id=new_id("conflict"),
                memory_id=item["id"],
                proposal_id="",
                kind=ConflictKind.DUPLICATE,
                detail="exact duplicate statement",
            )
            conflicts.append(c)
            status = ProposalStatus.SUPERSEDED
            verdict = "duplicate"
        elif (
            proposed.subject_ref
            and item.get("subject_ref") == proposed.subject_ref
            and item.get("authority") == "user_confirmed"
            and item.get("statement") != proposed.statement
        ):
            c = Conflict(
                id=new_id("conflict"),
                memory_id=item["id"],
                proposal_id="",
                kind=ConflictKind.CONTRADICTION,
                detail="contradicts user_confirmed memory",
            )
            conflicts.append(c)
            verdict = "conflict"
            status = ProposalStatus.PENDING
    proposal = MemoryProposal(
        id=new_id("proposal"),
        proposed_memory=proposed,
        evidence_refs=evidence_refs,
        submitted_by=submitted_by,
        status=status,
        policy_verdict=verdict,
        conflict_ids=[c.id for c in conflicts],
        created_at=now_iso(),
    )
    for c in conflicts:
        c.proposal_id = proposal.id
    return proposal, conflicts

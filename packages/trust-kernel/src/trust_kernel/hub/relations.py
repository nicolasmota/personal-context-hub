from __future__ import annotations

from pch_core.errors import NotFound, ValidationFailed, VersionConflict
from pch_core.hub.const import OWNER
from pch_core.ids import new_id
from pch_core.schema.audit import EventKind
from pch_core.schema.proposal import ProposalStatus
from pch_core.schema.relation import RelationLinkStatus, RelationProposal, RelationType
from pch_core.timeutil import now_iso


class RelationsMixin:
    def _parse_relation_type(self, relation_type: str) -> RelationType:
        try:
            return RelationType(relation_type)
        except ValueError as exc:
            raise ValidationFailed("unknown relation type") from exc

    def _live_relation_conflict(
        self, from_id: str, to_id: str, relation_type: str, *, exclude_id: str | None = None
    ) -> None:
        for row in self.store.list("relation"):
            if row["id"] == exclude_id:
                continue
            if row.get("status") != RelationLinkStatus.LIVE:
                continue
            if (
                row.get("from_id") == from_id
                and row.get("to_id") == to_id
                and row.get("relation_type") == relation_type
            ):
                raise VersionConflict("duplicate live relation")

    def create_relation(
        self, from_id: str, to_id: str, relation_type: str, actor: str = OWNER
    ) -> dict:
        if from_id == to_id:
            raise ValidationFailed("self-link forbidden")
        parsed = self._parse_relation_type(relation_type)
        self.store.get(from_id)
        self.store.get(to_id)
        self._live_relation_conflict(from_id, to_id, parsed.value)
        body = {
            "from_id": from_id,
            "to_id": to_id,
            "relation_type": parsed.value,
            "status": RelationLinkStatus.LIVE,
        }
        return self.create("relation", body, actor)

    def list_relations(
        self, from_id: str | None = None, object_id: str | None = None
    ) -> list[dict]:
        rows = [
            row
            for row in self.store.list("relation")
            if row.get("status") == RelationLinkStatus.LIVE
        ]
        if from_id:
            rows = [row for row in rows if row.get("from_id") == from_id]
        if object_id:
            rows = [
                row
                for row in rows
                if row.get("from_id") == object_id or row.get("to_id") == object_id
            ]
        rows.sort(key=lambda row: (row.get("relation_type") or "", row["id"]))
        return rows

    def delete_relation(self, relation_id: str, actor: str = OWNER) -> dict:
        current = self.store.get(relation_id)
        if current.get("type") != "relation":
            raise NotFound(relation_id)
        return self.patch(relation_id, {"status": RelationLinkStatus.REMOVED}, None, actor)

    def patch_relation_type(self, relation_id: str, relation_type: str, actor: str = OWNER) -> dict:
        current = self.store.get(relation_id)
        if current.get("type") != "relation":
            raise NotFound(relation_id)
        if current.get("status") != RelationLinkStatus.LIVE:
            raise NotFound(relation_id)
        parsed = self._parse_relation_type(relation_type)
        self._live_relation_conflict(
            current["from_id"], current["to_id"], parsed.value, exclude_id=relation_id
        )
        return self.patch(relation_id, {"relation_type": parsed.value}, None, actor)

    def propose_relation(self, actor: str, from_id: str, to_id: str, relation_type: str) -> dict:
        if actor == OWNER:
            raise ValidationFailed("owner writes relations directly")
        if from_id == to_id:
            raise ValidationFailed("self-link forbidden")
        parsed = self._parse_relation_type(relation_type)
        self.store.get(from_id)
        self.store.get(to_id)
        created = now_iso()
        proposal = RelationProposal(
            id=new_id("relation_proposal"),
            from_id=from_id,
            to_id=to_id,
            relation_type=parsed,
            submitted_by=actor,
            status=ProposalStatus.PENDING,
            created_at=created,
        )
        with self.engine.tx():
            payload = proposal.model_dump(mode="json")
            payload.update(
                {
                    "type": "relation_proposal",
                    "owner": self.person_id(),
                    "labels": [],
                    "classification": "personal",
                    "updated_at": created,
                    "source_refs": [],
                    "confidence": 1.0,
                    "authority": "proposed",
                    "retention": {"mode": "until_revoked"},
                    "policy_tags": [],
                    "version": 1,
                }
            )
            stored = self.store.put(payload, new=True)
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                actor,
                "relation proposed",
                [stored["id"], from_id, to_id],
            )
            return stored

    def list_relation_proposals(self, status: str | None = None) -> list[dict]:
        rows = self.store.list("relation_proposal")
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def decide_relation_proposal(self, proposal_id: str, accept: bool) -> dict:
        with self.engine.tx():
            proposal = self.store.get(proposal_id)
            if proposal.get("type") != "relation_proposal":
                raise NotFound(proposal_id)
            if proposal.get("status") != ProposalStatus.PENDING:
                raise VersionConflict("proposal already resolved")
            if accept:
                created = self.create_relation(
                    proposal["from_id"],
                    proposal["to_id"],
                    proposal["relation_type"],
                )
                proposal["status"] = ProposalStatus.ACCEPTED
                proposal["relation_id"] = created["id"]
                stored = self.store.put(proposal)
                self.ledger.append(
                    EventKind.OBJECT_WRITE,
                    OWNER,
                    "relation proposal accepted",
                    [proposal_id, created["id"]],
                )
                return stored
            proposal["status"] = ProposalStatus.REJECTED
            stored = self.store.put(proposal)
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                OWNER,
                "relation proposal rejected",
                [proposal_id],
            )
            return stored

    def resolve_conflict(self, conflict_id: str, status: str) -> dict:
        with self.engine.tx():
            c = self.store.get(conflict_id)
            c["status"] = status
            return self.store.put(c)

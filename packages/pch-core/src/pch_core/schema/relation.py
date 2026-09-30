from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, model_validator

from pch_core.schema.metadata import UniversalMetadata
from pch_core.schema.proposal import ProposalStatus


class RelationType(StrEnum):
    OWNED_BY = "owned_by"
    DEPENDS_ON = "depends_on"
    BLOCKED_BY = "blocked_by"
    RELATED_TO = "related_to"
    SUPPORTED_BY = "supported_by"
    DERIVED_FROM = "derived_from"


class RelationLinkStatus(StrEnum):
    LIVE = "live"
    REMOVED = "removed"


class Relation(UniversalMetadata):
    from_id: str
    to_id: str
    relation_type: RelationType
    status: RelationLinkStatus = RelationLinkStatus.LIVE

    @model_validator(mode="after")
    def _no_self_link(self) -> Relation:
        if self.from_id == self.to_id:
            raise ValueError("self-link forbidden")
        return self


class RelationProposal(BaseModel):
    id: str
    space_id: str = "personal"
    from_id: str
    to_id: str
    relation_type: RelationType
    submitted_by: str
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str

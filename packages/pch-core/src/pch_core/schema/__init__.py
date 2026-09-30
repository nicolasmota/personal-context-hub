from pch_core.schema.action import ActionIntent, IntentStatus
from pch_core.schema.approval import Approval, DecisionKind
from pch_core.schema.artifact import Artifact, ArtifactKind
from pch_core.schema.audit import AuditEvent, EventKind
from pch_core.schema.conflict import Conflict, ConflictKind, ConflictStatus
from pch_core.schema.connection import AgentConnection, ConnectionStatus
from pch_core.schema.contract import (
    ENVELOPE_SCHEMA_ID,
    Citation,
    ConflictPair,
    ContextContract,
    ContextQuery,
    ContractItem,
    ItemRef,
    OmissionCategory,
    OmissionNote,
    RelationRef,
    ScopeSummary,
    SituationRef,
    envelope_json_schema,
)
from pch_core.schema.event import CalendarEvent, CalendarEventStatus
from pch_core.schema.evidence import Evidence, EvidenceKind, VerificationStatus
from pch_core.schema.experience import Experience
from pch_core.schema.grant import PRESETS, Capability, Grant, GrantStatus
from pch_core.schema.manifest import ContextManifest, DisclosedRef, ManifestStatus
from pch_core.schema.memory import Memory, MemoryKind, SensitivityFlag
from pch_core.schema.metadata import (
    Authority,
    Classification,
    EntityType,
    Retention,
    RetentionMode,
    UniversalMetadata,
)
from pch_core.schema.person import Person
from pch_core.schema.portability import (
    ExportRecord,
    ImportStaging,
    ResolutionChoice,
    StagingStatus,
    VendorImportBatch,
    VendorOriginItem,
)
from pch_core.schema.preference import Preference
from pch_core.schema.profile import Profile
from pch_core.schema.project import (
    Commitment,
    Decision,
    Goal,
    OperationalPhase,
    Project,
    ProjectStatus,
)
from pch_core.schema.proposal import MemoryProposal, OperationalProposal, ProposalStatus
from pch_core.schema.relation import Relation, RelationProposal, RelationType
from pch_core.schema.space import ContextSpace
from pch_core.schema.state import SharedState, StateVisibility
from pch_core.schema.state_conflict import ConflictResolution, StateConflict, StateConflictStatus
from pch_core.schema.transition import StateTransition, TransitionKind

TYPE_MODELS = {
    EntityType.PERSON: Person,
    EntityType.SPACE: ContextSpace,
    EntityType.PROFILE: Profile,
    EntityType.PREFERENCE: Preference,
    EntityType.PROJECT: Project,
    EntityType.GOAL: Goal,
    EntityType.COMMITMENT: Commitment,
    EntityType.DECISION: Decision,
    EntityType.ARTIFACT: Artifact,
    EntityType.MEMORY: Memory,
    EntityType.EVENT: CalendarEvent,
    EntityType.RELATION: Relation,
    EntityType.EXPERIENCE: Experience,
    EntityType.EVIDENCE: Evidence,
    EntityType.STATE_TRANSITION: StateTransition,
    EntityType.STATE_CONFLICT: StateConflict,
}

__all__ = [
    "ActionIntent",
    "AgentConnection",
    "Approval",
    "Artifact",
    "ArtifactKind",
    "AuditEvent",
    "Authority",
    "CalendarEvent",
    "CalendarEventStatus",
    "Capability",
    "Classification",
    "Commitment",
    "Conflict",
    "ConflictKind",
    "ConflictStatus",
    "ConnectionStatus",
    "Citation",
    "ConflictPair",
    "ContextContract",
    "ContextManifest",
    "ContextQuery",
    "ContextSpace",
    "ContractItem",
    "Decision",
    "DecisionKind",
    "DisclosedRef",
    "ConflictResolution",
    "EntityType",
    "Evidence",
    "EvidenceKind",
    "Experience",
    "StateConflict",
    "StateConflictStatus",
    "StateTransition",
    "TransitionKind",
    "VerificationStatus",
    "ENVELOPE_SCHEMA_ID",
    "EventKind",
    "ExportRecord",
    "Goal",
    "Grant",
    "GrantStatus",
    "ImportStaging",
    "IntentStatus",
    "ItemRef",
    "ManifestStatus",
    "Memory",
    "MemoryKind",
    "MemoryProposal",
    "OmissionCategory",
    "OmissionNote",
    "OperationalPhase",
    "OperationalProposal",
    "PRESETS",
    "Person",
    "Preference",
    "Profile",
    "Project",
    "ProjectStatus",
    "ProposalStatus",
    "Relation",
    "RelationProposal",
    "RelationRef",
    "RelationType",
    "ResolutionChoice",
    "Retention",
    "RetentionMode",
    "ScopeSummary",
    "SensitivityFlag",
    "SituationRef",
    "SharedState",
    "StagingStatus",
    "StateVisibility",
    "TYPE_MODELS",
    "UniversalMetadata",
    "VendorImportBatch",
    "VendorOriginItem",
    "envelope_json_schema",
]

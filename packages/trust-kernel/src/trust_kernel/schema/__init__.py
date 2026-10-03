from trust_kernel.schema.action import ActionIntent, IntentStatus
from trust_kernel.schema.approval import Approval, DecisionKind
from trust_kernel.schema.artifact import Artifact, ArtifactKind
from trust_kernel.schema.audit import AuditEvent, EventKind
from trust_kernel.schema.conflict import Conflict, ConflictKind, ConflictStatus
from trust_kernel.schema.connection import AgentConnection, ConnectionStatus
from trust_kernel.schema.contract import (
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
from trust_kernel.schema.event import CalendarEvent, CalendarEventStatus
from trust_kernel.schema.evidence import Evidence, EvidenceKind, VerificationStatus
from trust_kernel.schema.experience import Experience
from trust_kernel.schema.grant import PRESETS, Capability, Grant, GrantStatus
from trust_kernel.schema.manifest import ContextManifest, DisclosedRef, ManifestStatus
from trust_kernel.schema.memory import Memory, MemoryKind, SensitivityFlag
from trust_kernel.schema.metadata import (
    Authority,
    Classification,
    EntityType,
    Retention,
    RetentionMode,
    UniversalMetadata,
)
from trust_kernel.schema.person import Person
from trust_kernel.schema.portability import (
    ExportRecord,
    ImportStaging,
    ResolutionChoice,
    StagingStatus,
    VendorImportBatch,
    VendorOriginItem,
)
from trust_kernel.schema.preference import Preference
from trust_kernel.schema.profile import Profile
from trust_kernel.schema.project import (
    Commitment,
    Decision,
    Goal,
    OperationalPhase,
    Project,
    ProjectStatus,
)
from trust_kernel.schema.proposal import MemoryProposal, OperationalProposal, ProposalStatus
from trust_kernel.schema.relation import Relation, RelationProposal, RelationType
from trust_kernel.schema.space import ContextSpace
from trust_kernel.schema.state import SharedState, StateVisibility
from trust_kernel.schema.state_conflict import (
    ConflictResolution,
    StateConflict,
    StateConflictStatus,
)
from trust_kernel.schema.transition import StateTransition, TransitionKind

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

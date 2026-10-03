from enum import StrEnum

from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    ARCHIVED = "archived"


class OperationalPhase(StrEnum):
    PLANNING = "planning"
    DECIDING = "deciding"
    WAITING = "waiting"
    EXECUTING = "executing"
    OTHER = "other"


class GoalStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


class CommitmentStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class Project(UniversalMetadata):
    title: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    charter: str = ""
    stakeholders: list[str] = Field(default_factory=list)
    operational_phase: OperationalPhase | None = None
    current_step: str | None = Field(default=None, max_length=200)
    situation_intent: str | None = Field(default=None, max_length=200)


class Goal(UniversalMetadata):
    title: str
    outcome: str = ""
    horizon: str | None = None
    measure: str | None = None
    status: GoalStatus = GoalStatus.OPEN
    project_id: str | None = None
    operational_phase: OperationalPhase | None = None
    current_step: str | None = Field(default=None, max_length=200)
    situation_intent: str | None = Field(default=None, max_length=200)


class Commitment(UniversalMetadata):
    title: str
    due_at: str | None = None
    counterparty: str | None = None
    status: CommitmentStatus = CommitmentStatus.OPEN
    project_id: str | None = None
    goal_id: str | None = None


class Decision(UniversalMetadata):
    title: str
    chosen_option: str = ""
    alternatives: list[str] = Field(default_factory=list)
    rationale: str = ""
    decided_at: str | None = None
    project_id: str | None = None

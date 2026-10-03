from __future__ import annotations

from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class Experience(UniversalMetadata):
    action: str
    operating_context: str
    outcome: str
    feedback: str | None = None
    lesson: str | None = None
    occurred_at: str
    provenance: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

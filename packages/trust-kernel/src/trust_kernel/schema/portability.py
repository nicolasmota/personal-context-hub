from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StagingStatus(StrEnum):
    STAGED = "staged"
    APPLIED = "applied"
    DISCARDED = "discarded"


class ResolutionChoice(StrEnum):
    MERGE = "merge"
    REPLACE = "replace"
    KEEP_SEPARATE = "keep_separate"
    SKIP = "skip"


class ExportRecord(BaseModel):
    id: str
    space_id: str = "personal"
    filters: dict[str, Any] = Field(default_factory=dict)
    pca_version: str = "0.1.0"
    manifest_hash: str = ""
    created_at: str
    path: str = ""


class VendorOriginItem(BaseModel):
    fingerprint: str
    original_id: str
    proposal_id: str | None = None
    statement_preview: str = ""


class VendorImportBatch(BaseModel):
    id: str
    space_id: str = "personal"
    source: str
    path_basename: str = ""
    status: str = "enqueued"
    archive_status: str = "none"
    memory_item_count: int = 0
    conversation_count: int = 0
    proposal_ids: list[str] = Field(default_factory=list)
    skipped_fingerprints: list[str] = Field(default_factory=list)
    items: list[VendorOriginItem] = Field(default_factory=list)
    created_at: str
    owner: str = ""


class ImportStaging(BaseModel):
    id: str
    space_id: str = "personal"
    archive_manifest: dict[str, Any] = Field(default_factory=dict)
    item_resolutions: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    records: list[dict[str, Any]] = Field(default_factory=list)
    status: StagingStatus = StagingStatus.STAGED
    created_at: str

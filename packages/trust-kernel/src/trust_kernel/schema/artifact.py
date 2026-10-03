from enum import StrEnum

from pydantic import Field

from pch_core.schema.metadata import UniversalMetadata


class ArtifactKind(StrEnum):
    DOCUMENT = "document"
    MESSAGE_THREAD = "message_thread"
    CONVERSATION = "conversation"
    FILE = "file"
    URL = "url"
    EMAIL = "email"


class Artifact(UniversalMetadata):
    kind: ArtifactKind = ArtifactKind.DOCUMENT
    title: str
    content_hash: str | None = None
    external_ref: str | None = None
    untrusted: bool = True
    body: str = ""
    subject: str | None = None
    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    sent_at: str | None = None
    body_text: str | None = None

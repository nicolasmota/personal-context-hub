from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class ContextSpace(UniversalMetadata):
    name: str = "Personal"
    kind: str = "personal"
    key_hint: str = Field(default="", description="non-secret key metadata")

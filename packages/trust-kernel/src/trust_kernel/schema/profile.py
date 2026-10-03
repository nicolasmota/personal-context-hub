from pydantic import Field

from trust_kernel.schema.metadata import UniversalMetadata


class Profile(UniversalMetadata):
    contact_norms: str = ""
    working_hours: str = ""
    extra: dict = Field(default_factory=dict)

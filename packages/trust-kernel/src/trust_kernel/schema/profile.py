from pydantic import Field

from pch_core.schema.metadata import UniversalMetadata


class Profile(UniversalMetadata):
    contact_norms: str = ""
    working_hours: str = ""
    extra: dict = Field(default_factory=dict)

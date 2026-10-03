from enum import StrEnum

from pydantic import Field

from pch_core.schema.metadata import Classification, UniversalMetadata


class CalendarEventStatus(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class CalendarEvent(UniversalMetadata):
    title: str
    starts_at: str
    ends_at: str
    all_day: bool = False
    location: str | None = None
    attendees: list[str] = Field(default_factory=list)
    calendar_id: str = "primary"
    status: CalendarEventStatus = CalendarEventStatus.CONFIRMED
    source_key: str | None = None
    classification: Classification = Classification.PRIVATE

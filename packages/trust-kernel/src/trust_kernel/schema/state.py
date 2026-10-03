from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class StateVisibility(StrEnum):
    PRIVATE_TO_CONNECTION = "private_to_connection"
    SHARED = "shared"


class SharedState(BaseModel):
    key: str
    space_id: str = "personal"
    value: Any = None
    ttl_seconds: int = 900
    expires_at: str
    visibility: StateVisibility = StateVisibility.PRIVATE_TO_CONNECTION
    created_by: str

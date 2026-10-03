from __future__ import annotations

from pch_core.errors import PolicyDenied
from pch_core.schema.action import ActionIntent, IntentStatus


def assert_executable(intent: ActionIntent | dict) -> None:
    status = intent.status if isinstance(intent, ActionIntent) else intent.get("status")
    if status != IntentStatus.APPROVED and status != "approved":
        raise PolicyDenied("action is not approved")

from __future__ import annotations

from trust_kernel.errors import PolicyDenied
from trust_kernel.schema.action import ActionIntent, IntentStatus


def assert_executable(intent: ActionIntent | dict) -> None:
    status = intent.status if isinstance(intent, ActionIntent) else intent.get("status")
    if status != IntentStatus.APPROVED and status != "approved":
        raise PolicyDenied("action is not approved")

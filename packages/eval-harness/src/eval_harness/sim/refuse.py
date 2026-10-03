from __future__ import annotations


class SimRefused(Exception):
    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        super().__init__(message or reason)


EVERYDAY_CONFIRM = "WRITE_EVERYDAY_VAULT"
FORBIDDEN_ACTIONS = frozenset({"propose_action"})

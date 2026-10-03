from __future__ import annotations

from pch_core.schema.memory import Memory, SensitivityFlag
from pch_core.schema.proposal import ProposalStatus


def blocks_auto_accept(memory: Memory) -> bool:
    return bool(memory.sensitivity_flags)


def required_verdict(memory: Memory) -> str:
    if memory.sensitivity_flags:
        flags = [SensitivityFlag(f) if not isinstance(f, SensitivityFlag) else f for f in memory.sensitivity_flags]
        if flags:
            return "needs_review"
    return "needs_review"


def cannot_auto_accept(status: ProposalStatus, memory: Memory) -> bool:
    if memory.sensitivity_flags and status == ProposalStatus.AUTO_ACCEPTED:
        return True
    return False

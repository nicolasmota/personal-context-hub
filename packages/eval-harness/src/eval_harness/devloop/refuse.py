from __future__ import annotations


class LoopRefused(Exception):
    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        super().__init__(message or reason)


NOT_A_FEATURE = frozenset(
    {
        "docs/VISION.md",
        "docs/ROADMAP.md",
        "VISION.md",
        "ROADMAP.md",
    }
)


def refuse_start(
    *,
    desc: str | None,
    epic: str | None,
    dir: str | None,
    roadmap: bool,
) -> None:
    desc_ok = bool(desc and str(desc).strip())
    flags = int(desc_ok) + int(bool(epic)) + int(bool(dir)) + int(bool(roadmap))
    if flags == 0:
        raise LoopRefused("empty_start", "Need --desc, --epic, --dir, or --roadmap")
    if flags > 1:
        raise LoopRefused("empty_start", "Give exactly one of --desc, --epic, --dir, --roadmap")
    if dir is not None:
        normalized = str(dir).replace("\\", "/").lstrip("./")
        if normalized in NOT_A_FEATURE or normalized.endswith("/VISION.md") or normalized.endswith(
            "/ROADMAP.md"
        ):
            raise LoopRefused("not_a_feature", "Vision and roadmap are not Speckit features")
    if epic is not None:
        raw = str(epic).strip()
        if raw.startswith(("001", "002", "003")):
            raise LoopRefused(
                "closed_chapter",
                "Closed chapters 001–003 cannot be reopened as epics",
            )

from datetime import UTC, datetime


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def interval_contains(
    valid_from: str | None,
    valid_until: str | None,
    at: datetime,
    *,
    created_at: str | None = None,
) -> bool:
    start_raw = valid_from or created_at
    if start_raw:
        start = parse_instant(start_raw)
        if at < start:
            return False
    if not valid_until:
        return True
    return at < parse_instant(valid_until)


def validate_interval(valid_from: str | None, valid_until: str | None) -> None:
    if valid_from and valid_until and parse_instant(valid_from) >= parse_instant(valid_until):
        raise ValueError("valid_until must be after valid_from")


def row_is_current(obj: dict, at: datetime) -> bool:
    if obj.get("never_true") or obj.get("tombstone"):
        return False
    return interval_contains(
        obj.get("valid_from"),
        obj.get("valid_until"),
        at,
        created_at=obj.get("created_at"),
    )

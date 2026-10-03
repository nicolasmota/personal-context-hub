from datetime import UTC, datetime

from pch_core.timeutil import interval_contains, parse_instant


def test_parse_instant_zulu():
    parsed = parse_instant("2026-06-01T12:00:00Z")
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def test_open_ended_is_current_after_start():
    at = parse_instant("2026-06-01T00:00:00Z")
    assert interval_contains("2026-01-01T00:00:00Z", None, at)


def test_future_start_not_current():
    at = parse_instant("2026-01-01T00:00:00Z")
    assert not interval_contains("2026-06-01T00:00:00Z", None, at)


def test_half_open_end_not_included():
    start = "2026-01-01T00:00:00Z"
    end = "2026-06-01T00:00:00Z"
    assert interval_contains(start, end, parse_instant("2026-05-31T23:59:59Z"))
    assert not interval_contains(start, end, parse_instant(end))


def test_missing_valid_from_uses_created_at():
    at = parse_instant("2026-02-01T00:00:00Z")
    assert interval_contains(None, None, at, created_at="2026-01-01T00:00:00Z")
    assert not interval_contains(None, None, at, created_at="2026-03-01T00:00:00Z")

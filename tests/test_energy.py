"""Tests for Mysa expanded energy parsing."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from custom_components.mysa.energy import parse_energy_history


def test_parse_daily_energy_and_buckets() -> None:
    """Use the daily kWh summary and retain UTC bucket timestamps."""
    timezone = ZoneInfo("America/Toronto")
    payload = [
        {
            "T": "2026-10-30T04:00:00+00:00",
            "summary": {"a": {"k": 0.68}},
            "aggregatedReadings": [
                {"T": "2026-10-30T04:00:00+00:00", "a": {"k": 0.30}},
                {"T": "2026-10-30T04:30:00+00:00", "a": {"k": 0.38}},
            ],
        }
    ]

    result = parse_energy_history(payload, timezone)

    assert result["2026-10-30"].energy_kwh == 0.68
    assert sum(result["2026-10-30"].buckets.values()) == 0.68


def test_parse_bucket_energy_when_daily_summary_is_missing() -> None:
    """Fall back to the sum of available kWh buckets."""
    timezone = ZoneInfo("America/Toronto")
    payload = [
        {
            "T": "2026-10-31T04:00:00+00:00",
            "summary": {"a": {"oH1": 1200}},
            "aggregatedReadings": [
                {"T": "2026-10-31T04:00:00+00:00", "a": {"k": 0.21}},
                {"T": "2026-10-31T04:30:00+00:00", "a": {"k": 0.29}},
            ],
        }
    ]

    result = parse_energy_history(payload, timezone)

    assert result["2026-10-31"].energy_kwh == 0.5


def test_dst_fall_back_buckets_keep_distinct_instants() -> None:
    """The repeated local 01:00 hour must not collapse two UTC buckets."""
    timezone = ZoneInfo("America/Toronto")
    payload = [
        {
            "T": "2026-11-01T04:00:00+00:00",
            "summary": {"a": {"k": 0.51}},
            "aggregatedReadings": [
                {"T": "2026-11-01T05:00:00+00:00", "a": {"k": 0.25}},
                {"T": "2026-11-01T06:00:00+00:00", "a": {"k": 0.26}},
            ],
        }
    ]

    result = parse_energy_history(payload, timezone)

    assert len(result["2026-11-01"].buckets) == 2
    assert result["2026-11-01"].energy_kwh == 0.51


def test_ignore_invalid_or_unavailable_energy_values() -> None:
    """Ignore malformed data rather than creating bogus energy readings."""
    timezone = ZoneInfo("America/Toronto")
    payload = [
        {
            "T": "2026-11-02T05:00:00+00:00",
            "summary": {"a": {"k": None}},
            "aggregatedReadings": [
                {"T": "2026-11-02T05:00:00+00:00", "a": {"k": -1}},
                {"T": "not-a-time", "a": {"k": 1.2}},
            ],
        },
        {"T": None, "summary": {"a": {"k": 2.0}}},
    ]

    assert parse_energy_history(payload, timezone) == {}

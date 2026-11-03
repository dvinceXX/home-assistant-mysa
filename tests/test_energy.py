"""Tests for Mysa expanded energy parsing."""

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from custom_components.mysa.energy import EnergyDay, parse_energy_history
from custom_components.mysa.energy_coordinator import _hourly_energy, _merge_day


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
    assert sum(result["2026-10-30"].buckets.values()) == pytest.approx(0.68)


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


def test_hourly_statistics_keep_dst_fall_back_hours_separate() -> None:
    """Keep both UTC hours when the local clock repeats 01:00."""
    timezone = ZoneInfo("America/Toronto")
    days = {
        "2026-11-01": {
            "energy_kwh": 0.51,
            "buckets": {
                "2026-11-01T05:00:00+00:00": 0.25,
                "2026-11-01T06:00:00+00:00": 0.26,
            },
        }
    }

    hourly = _hourly_energy(days, timezone)

    assert len(hourly) == 2
    assert sum(hourly.values()) == pytest.approx(0.51)


def test_merge_preserves_previously_imported_buckets() -> None:
    """A partial refresh must not discard intervals already stored."""
    saved_days = {
        "2026-10-30": {
            "energy_kwh": 0.3,
            "buckets": {"2026-10-30T04:00:00+00:00": 0.3},
        }
    }
    fetched = EnergyDay(
        day=date(2026, 10, 30),
        energy_kwh=0.68,
        buckets={"2026-10-30T04:30:00+00:00": 0.38},
    )

    _merge_day(saved_days, "2026-10-30", fetched)

    assert saved_days["2026-10-30"]["energy_kwh"] == 0.68
    assert len(saved_days["2026-10-30"]["buckets"]) == 2

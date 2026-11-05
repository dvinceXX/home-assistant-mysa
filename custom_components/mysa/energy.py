"""Expanded Mysa usage history and energy parsing.

The Mysa cloud API is undocumented. The expanded `k` metric is used only
when returned by the device; this module never estimates energy from runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
import math
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from mysa_client.cloud import MysaClient


# Four days is a known-working window for the expanded telemetry endpoint.
ENERGY_HISTORY_CHUNK_DAYS = 4


@dataclass(frozen=True, slots=True)
class EnergyDay:
    """Energy totals and 30-minute readings for one thermostat-local day."""

    day: date
    energy_kwh: float
    buckets: dict[str, float]


def _number(value: Any) -> float | None:
    """Return a finite non-negative number."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _timestamp(value: Any, timezone: ZoneInfo) -> datetime | None:
    """Parse an API timestamp, preserving its instant."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        try:
            return datetime.fromtimestamp(float(value), UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed


def parse_energy_history(
    payload: Any, timezone: ZoneInfo
) -> dict[str, EnergyDay]:
    """Parse expanded usage response into local-day energy records.

    The daily summary's `summary.a.k` is authoritative when present.
    Bucket values are retained for hourly Energy-dashboard statistics.
    """
    # The telemetry endpoint returns a single day object for some
    # requests, while diagnostic/export paths may return a list of days.
    # Accept both shapes; rejecting the object form silently drops all energy.
    if isinstance(payload, Mapping):
        raw_days = [payload]
    elif isinstance(payload, list):
        raw_days = payload
    else:
        return {}

    days: dict[str, EnergyDay] = {}
    for raw_day in raw_days:
        if not isinstance(raw_day, Mapping):
            continue
        day_start = _timestamp(raw_day.get("T"), timezone)
        if day_start is None:
            continue
        local_date = day_start.astimezone(timezone).date()

        summary = raw_day.get("summary")
        summary_values = summary.get("a") if isinstance(summary, Mapping) else None
        summary_values = summary_values if isinstance(summary_values, Mapping) else {}
        summary_kwh = _number(summary_values.get("k"))

        buckets: dict[str, float] = {}
        raw_buckets = raw_day.get("aggregatedReadings")
        if isinstance(raw_buckets, list):
            for raw_bucket in raw_buckets:
                if not isinstance(raw_bucket, Mapping):
                    continue
                bucket_start = _timestamp(raw_bucket.get("T"), timezone)
                values = raw_bucket.get("a")
                if bucket_start is None or not isinstance(values, Mapping):
                    continue
                energy = _number(values.get("k"))
                if energy is None:
                    continue
                # UTC keys distinguish the repeated hour during DST fall-back.
                buckets[bucket_start.astimezone(UTC).isoformat()] = energy

        bucket_total = sum(buckets.values())
        daily_total = summary_kwh if summary_kwh is not None else bucket_total
        if summary_kwh is None and not buckets:
            continue

        key = local_date.isoformat()
        days[key] = EnergyDay(
            day=local_date,
            energy_kwh=daily_total,
            buckets=buckets,
        )
    return days


async def async_get_expanded_energy(
    client: MysaClient,
    device_id: str,
    timezone: str,
    start: datetime,
    end: datetime,
) -> Any:
    """Read expanded usage including the Mysa app's energy metric.

    mysa-client's public get_usage method currently requests runtime and
    temperature only. This uses its authenticated request transport for the
    documented read-only expanded usage request.
    """
    if end <= start:
        return []

    combined: list[Any] = []
    cursor = start
    while cursor < end:
        chunk_end = min(
            cursor + timedelta(days=ENERGY_HISTORY_CHUNK_DAYS),
            end,
        )
        body = {
            "timezone": timezone,
            "start": int(cursor.timestamp()),
            "end": int(chunk_end.timestamp()),
            "summary": {
                "oH1": "sum",
                "k": "sum",
                "t": "average",
                "h": "average",
                "n": "sum",
            },
            "aggregatedReadings": ["oH1", "k", "t", "h", "n"],
        }
        payload = await client._request(  # noqa: SLF001
            "POST", f"/telemetry/usage/{device_id}", body=body
        )
        if isinstance(payload, list):
            combined.extend(payload)
        elif isinstance(payload, Mapping):
            combined.append(payload)
        cursor = chunk_end

    return combined

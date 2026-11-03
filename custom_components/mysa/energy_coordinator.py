"""Persistent Mysa energy history and Home Assistant statistics import."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
import hashlib
import logging
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.unit_conversion import EnergyConverter

from mysa_client.cloud import MysaClient

from .const import DOMAIN
from .energy import EnergyDay, async_get_expanded_energy, parse_energy_history

_LOGGER = logging.getLogger(__name__)

INITIAL_HISTORY_DAYS = 365
REFRESH_HISTORY_DAYS = 30
UPDATE_INTERVAL = timedelta(hours=12)


class MysaEnergyCoordinator(DataUpdateCoordinator[dict[str, dict[str, float | None]]]):
    """Fetch, persist and import daily Mysa energy history."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MysaClient,
        devices: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize energy history coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_energy",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.devices = devices
        self.store = Store(hass, 1, f"{DOMAIN}_{entry_id}_energy")
        self.history: dict[str, dict[str, Any]] = {}
        self._loaded = False

    async def async_initialize(self) -> None:
        """Load persisted history before the first refresh."""
        stored = await self.store.async_load()
        if isinstance(stored, dict):
            devices = stored.get("devices")
            if isinstance(devices, dict):
                self.history = devices
        self._loaded = True
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, dict[str, float | None]]:
        """Fetch recent expanded usage and import updated statistics."""
        if not self._loaded:
            stored = await self.store.async_load()
            if isinstance(stored, dict) and isinstance(stored.get("devices"), dict):
                self.history = stored["devices"]
            self._loaded = True

        result: dict[str, dict[str, float | None]] = {}
        for device_id, device in self.devices.items():
            timezone_name = device.time_zone or self.hass.config.time_zone
            try:
                timezone = ZoneInfo(timezone_name)
            except (ZoneInfoNotFoundError, TypeError):
                _LOGGER.warning(
                    "Invalid timezone for Mysa device %s; using Home Assistant timezone",
                    device.name or device_id,
                )
                timezone_name = self.hass.config.time_zone
                timezone = ZoneInfo(timezone_name)

            now_local = datetime.now(timezone)
            today = now_local.date()
            device_history = self.history.setdefault(device_id, {"days": {}})
            saved_days = device_history.setdefault("days", {})
            valid_saved_dates = [
                date.fromisoformat(day_key)
                for day_key in saved_days
                if _valid_date_key(day_key)
            ]
            if valid_saved_dates:
                # Re-read recent days to repair partial imports and catch up after
                # Home Assistant has been offline.
                start_date = max(
                    today - timedelta(days=INITIAL_HISTORY_DAYS),
                    max(valid_saved_dates) - timedelta(days=REFRESH_HISTORY_DAYS),
                )
            else:
                start_date = today - timedelta(days=INITIAL_HISTORY_DAYS)

            start = datetime.combine(start_date, time.min, tzinfo=timezone)
            try:
                payload = await async_get_expanded_energy(
                    self.client,
                    device_id,
                    timezone_name,
                    start,
                    now_local,
                )
                fetched = parse_energy_history(payload, timezone)
                for day_key, energy_day in fetched.items():
                    _merge_day(saved_days, day_key, energy_day)
            except Exception as err:  # Keep other thermostats updating independently.
                _LOGGER.warning(
                    "Unable to refresh Mysa energy history for %s: %s",
                    device.name or device_id,
                    err,
                )

            valid_energy_days = [
                item
                for item in saved_days.values()
                if isinstance(item, dict)
                and not isinstance(item.get("energy_kwh"), bool)
                and isinstance(item.get("energy_kwh"), int | float)
            ]
            cumulative: float | None = None
            if valid_energy_days:
                cumulative = sum(_valid_energy_day(item) for item in valid_energy_days)
                # Preserve a monotonic meter value if Mysa later revises an old
                # day downward. Newly recovered missing days can still increase it.
                cumulative = max(
                    float(device_history.get("cumulative_kwh", 0.0)),
                    cumulative,
                )
                device_history["cumulative_kwh"] = cumulative

            today_record = saved_days.get(today.isoformat(), {})
            today_kwh = (
                _valid_energy_day(today_record)
                if isinstance(today_record, dict)
                and not isinstance(today_record.get("energy_kwh"), bool)
                and isinstance(today_record.get("energy_kwh"), int | float)
                else None
            )
            result[device_id] = {
                "today_kwh": today_kwh,
                "total_kwh": cumulative,
            }
            import_start = datetime.combine(start_date, time.min, tzinfo=timezone)
            self._import_device_statistics(
                device_id, device, saved_days, timezone, import_start
            )

        await self.store.async_save({"devices": self.history})
        return result

    def _import_device_statistics(
        self,
        device_id: str,
        device: Any,
        saved_days: dict[str, Any],
        timezone: ZoneInfo,
        import_start: datetime,
    ) -> None:
        """Import recent hourly statistics, including corrected partial days."""
        hourly = _hourly_energy(saved_days, timezone)
        if not hourly:
            return

        digest = hashlib.sha256(device_id.encode()).hexdigest()[:12]
        statistic_id = f"{DOMAIN}:energy_{digest}"
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"Mysa {device.name or 'Thermostat'} energy",
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_class=EnergyConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )

        import_start_utc = import_start.astimezone(UTC).replace(
            minute=0, second=0, microsecond=0
        )
        running_total = sum(
            energy for hour_start, energy in hourly.items()
            if hour_start < import_start_utc
        )
        statistics: list[StatisticData] = []
        for hour_start, energy in sorted(hourly.items()):
            if hour_start < import_start_utc:
                continue
            running_total += energy
            statistics.append(
                StatisticData(start=hour_start, state=energy, sum=running_total)
            )
        async_add_external_statistics(self.hass, metadata, statistics)


def _valid_date_key(value: Any) -> bool:
    """Return whether a stored date key is an ISO calendar date."""
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_energy_day(value: dict[str, Any]) -> float:
    """Read a stored daily energy value safely."""
    energy = value.get("energy_kwh")
    if isinstance(energy, bool) or not isinstance(energy, int | float):
        return 0.0
    return max(0.0, float(energy))


def _merge_day(
    saved_days: dict[str, Any],
    day_key: str,
    fetched: EnergyDay,
) -> None:
    """Merge newly received buckets while refreshing the authoritative daily sum."""
    old = saved_days.get(day_key)
    old_buckets = old.get("buckets", {}) if isinstance(old, dict) else {}
    buckets = dict(old_buckets) if isinstance(old_buckets, dict) else {}
    buckets.update(fetched.buckets)
    saved_days[day_key] = {
        "energy_kwh": fetched.energy_kwh,
        "buckets": buckets,
    }


def _hourly_energy(
    saved_days: dict[str, Any], timezone: ZoneInfo
) -> dict[datetime, float]:
    """Group 30-minute kWh buckets into UTC hourly consumption."""
    hourly: dict[datetime, float] = {}
    for day_record in saved_days.values():
        if not isinstance(day_record, dict):
            continue
        buckets = day_record.get("buckets")
        if not isinstance(buckets, dict) or not buckets:
            continue
        bucket_total = 0.0
        day_hours: list[datetime] = []
        for stamp, raw_energy in buckets.items():
            try:
                start = datetime.fromisoformat(stamp).astimezone(UTC)
                energy = float(raw_energy)
            except (TypeError, ValueError):
                continue
            if energy < 0:
                continue
            hour_start = start.replace(minute=0, second=0, microsecond=0)
            hourly[hour_start] = hourly.get(hour_start, 0.0) + energy
            bucket_total += energy
            day_hours.append(hour_start)

        # Reconcile bucket rounding differences against the daily summary.
        daily_total = _valid_energy_day(day_record)
        if day_hours and abs(daily_total - bucket_total) > 0.0001:
            last_hour = max(day_hours)
            adjustment = daily_total - bucket_total
            hourly[last_hour] = max(0.0, hourly.get(last_hour, 0.0) + adjustment)

    # If only a daily summary is available, place it at the local day's final
    # hour. This keeps the correct daily total without inventing a profile.
    for day_key, day_record in saved_days.items():
        if not isinstance(day_record, dict) or day_record.get("buckets"):
            continue
        if not _valid_date_key(day_key):
            continue
        energy = _valid_energy_day(day_record)
        if energy <= 0:
            continue
        local_date = date.fromisoformat(day_key)
        local_hour = datetime.combine(local_date, time(23), tzinfo=timezone)
        hour_start = local_hour.astimezone(UTC).replace(
            minute=0, second=0, microsecond=0
        )
        hourly[hour_start] = hourly.get(hour_start, 0.0) + energy

    return hourly

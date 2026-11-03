"""Sensors for Mysa thermostats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import MysaCoordinator
from .energy_coordinator import MysaEnergyCoordinator


@dataclass(frozen=True, kw_only=True)
class MysaSensorDescription(SensorEntityDescription):
    """Describe a Mysa sensor."""

    value_fn: Any


SENSORS: tuple[MysaSensorDescription, ...] = (
    MysaSensorDescription(
        key="room_temperature",
        name="Room Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.room_temperature,
    ),
    MysaSensorDescription(
        key="heat_setpoint",
        name="Heat Setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.heat_setpoint,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mysa sensors."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: MysaCoordinator = entry_data["coordinator"]
    energy_coordinator: MysaEnergyCoordinator = entry_data["energy_coordinator"]

    entities: list[SensorEntity] = [
        MysaSensor(coordinator, device_id, description)
        for device_id in coordinator.devices
        for description in SENSORS
    ]
    for device_id in coordinator.devices:
        entities.extend(
            (
                MysaEnergySensor(
                    energy_coordinator,
                    device_id,
                    energy_type="today",
                ),
                MysaEnergySensor(
                    energy_coordinator,
                    device_id,
                    energy_type="total",
                ),
            )
        )
    async_add_entities(entities)


class MysaSensor(CoordinatorEntity[MysaCoordinator], SensorEntity):
    """A read-only thermostat sensor."""

    entity_description: MysaSensorDescription

    def __init__(
        self,
        coordinator: MysaCoordinator,
        device_id: str,
        description: MysaSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        device = coordinator.devices[device_id]
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name or "Mysa Thermostat",
            manufacturer="Mysa",
            model=device.model,
        )

    @property
    def native_value(self) -> float | None:
        """Return the latest value."""
        state = self.coordinator.data.get(self._device_id)
        if state is None:
            return None
        return self.entity_description.value_fn(state)


class MysaEnergySensor(CoordinatorEntity[MysaEnergyCoordinator], SensorEntity):
    """Daily or cumulative energy from Mysa's expanded usage history."""

    def __init__(
        self,
        coordinator: MysaEnergyCoordinator,
        device_id: str,
        *,
        energy_type: str,
    ) -> None:
        """Initialize an energy sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._energy_type = energy_type
        device = coordinator.devices[device_id]
        is_total = energy_type == "total"
        self._attr_unique_id = f"{device_id}_energy_{energy_type}"
        self._attr_name = (
            "Total Energy" if is_total else "Energy Today"
        )
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = (
            SensorStateClass.TOTAL_INCREASING
            if is_total
            else SensorStateClass.TOTAL
        )
        self._attr_suggested_display_precision = 2
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name or "Mysa Thermostat",
            manufacturer="Mysa",
            model=device.model,
        )

    @property
    def last_reset(self) -> datetime | None:
        """Return local midnight for the daily meter reset."""
        if self._energy_type == "total":
            return None
        device = self.coordinator.devices[self._device_id]
        timezone = ZoneInfo(device.time_zone or self.hass.config.time_zone)
        today = dt_util.now(timezone).date()
        return datetime.combine(today, time.min, tzinfo=timezone)

    @property
    def native_value(self) -> float | None:
        """Return today's or cumulative energy."""
        values = self.coordinator.data.get(self._device_id)
        if values is None:
            return None
        key = "total_kwh" if self._energy_type == "total" else "today_kwh"
        return values.get(key)

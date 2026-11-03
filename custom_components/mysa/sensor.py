"""Sensors for Mysa thermostats."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MysaCoordinator


@dataclass(frozen=True, kw_only=True)
class MysaSensorDescription(SensorEntityDescription):
    """Describe a Mysa sensor."""

    value_fn: Any


SENSORS: tuple[MysaSensorDescription, ...] = (
    MysaSensorDescription(
        key="room_temperature",
        name="Room Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda state: state.room_temperature,
    ),
    MysaSensorDescription(
        key="heat_setpoint",
        name="Heat Setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda state: state.heat_setpoint,
    ),
    MysaSensorDescription(
        key="duty_cycle",
        name="Heating Duty Cycle",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda state: state.duty_cycle,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mysa sensors."""
    coordinator: MysaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        MysaSensor(coordinator, device_id, description)
        for device_id in coordinator.devices
        for description in SENSORS
    ]
    async_add_entities(entities)


class MysaSensor(CoordinatorEntity[MysaCoordinator], SensorEntity):
    """A read-only sensor for one Mysa thermostat."""

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

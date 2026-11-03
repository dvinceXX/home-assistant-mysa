"""Binary sensors for Mysa thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MysaCoordinator


DESCRIPTION = BinarySensorEntityDescription(
    key="connected",
    name="Connected",
    device_class="connectivity",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mysa connectivity entities."""
    coordinator: MysaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        MysaConnectedSensor(coordinator, device_id)
        for device_id in coordinator.devices
    )


class MysaConnectedSensor(CoordinatorEntity[MysaCoordinator], BinarySensorEntity):
    """Show whether a Mysa thermostat is connected."""

    entity_description = DESCRIPTION

    def __init__(self, coordinator: MysaCoordinator, device_id: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        device = coordinator.devices[device_id]
        self._attr_unique_id = f"{device_id}_connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name or "Mysa Thermostat",
            manufacturer="Mysa",
            model=device.model,
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current connection state."""
        state = self.coordinator.data.get(self._device_id)
        return state.connected if state else None

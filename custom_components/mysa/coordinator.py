"""Data update coordinator for Mysa devices."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from mysa_client.cloud import MysaClient

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MysaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll read-only state from all Mysa thermostats."""

    def __init__(self, hass: HomeAssistant, client: MysaClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.client = client
        self.devices: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current device state."""
        try:
            account = await self.client.bootstrap()
            self.devices = account.devices
            states: dict[str, Any] = {}
            for device_id in account.devices:
                states[device_id] = await self.client.get_state(device_id)
            return states
        except Exception as err:
            raise UpdateFailed(f"Unable to update Mysa devices: {err}") from err

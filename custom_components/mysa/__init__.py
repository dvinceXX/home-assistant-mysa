"""The Mysa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import create_client
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MysaCoordinator
from .energy_coordinator import MysaEnergyCoordinator

type MysaConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Mysa from YAML (config entries are required)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MysaConfigEntry) -> bool:
    """Set up a Mysa account."""
    session = async_get_clientsession(hass)

    def save_refresh_token(token: str) -> None:
        """Persist refreshed Cognito token without logging it."""
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_REFRESH_TOKEN: token},
        )

    client = create_client(
        session,
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        on_refresh_token=save_refresh_token,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = MysaCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    energy_coordinator = MysaEnergyCoordinator(
        hass,
        client,
        coordinator.devices,
        entry.entry_id,
    )
    await energy_coordinator.async_initialize()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "energy_coordinator": energy_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MysaConfigEntry) -> bool:
    """Unload a Mysa account."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok

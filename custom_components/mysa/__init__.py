"""The Mysa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

type MysaConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Mysa integration from YAML (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MysaConfigEntry) -> bool:
    """Set up a Mysa config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MysaConfigEntry) -> bool:
    """Unload a Mysa config entry."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True

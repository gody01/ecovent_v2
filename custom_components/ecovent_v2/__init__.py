"""The EcoVent_v2 integration."""
# from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import EcoVentCoordinator

_LOGGER = logging.getLogger(__name__)

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)

_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.FAN,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoVent_v2 from a config entry."""

    entry.runtime_data = {
        CONF_IP_ADDRESS: entry.data.get(CONF_IP_ADDRESS, "<broadcast>"),
        CONF_PORT: entry.data.get(CONF_PORT, 4000),
        CONF_DEVICE_ID: entry.data.get(CONF_DEVICE_ID, "DEFAULT_DEVICEID"),
        CONF_PASSWORD: entry.data.get(CONF_PASSWORD, "1111"),
        CONF_NAME: entry.data.get(CONF_NAME, "Vento Expert Fan"),
        UPDATE_INTERVAL: entry.data.get(UPDATE_INTERVAL, 30),
    }

    coordinator = EcoVentCoordinator(hass, entry, update_seconds=entry.runtime_data[UPDATE_INTERVAL])

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    return unload_ok

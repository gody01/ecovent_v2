"""The EcoVent_v2 integration."""
from __future__ import annotations

import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent

from .const import DOMAIN

from ecoventv2 import Fan

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_NAME,
    CONF_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# PLATFORMS: list[str] = ["fan", "sensor"]
PLATFORMS: list[str] = ["fan", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoVent_v2 from a config entry."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = VentoFan(hass, entry)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok


class VentoFan(EntityComponent):
    """We only want to have common instance of Fan."""

    def __init__(self, hass, config: ConfigEntry):
        super().__init__(_LOGGER, config.domain, hass)
        self._fan = Fan(
            config.data[CONF_IP_ADDRESS],
            config.data[CONF_PASSWORD],
            config.data[CONF_DEVICE_ID],
            config.data[CONF_NAME],
            config.data[CONF_PORT],
        )
        self._fan.init_device()
        self._fan.update()

    async def async_update(self):
        self._fan.update()

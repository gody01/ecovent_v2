"""The EcoVent_v2 integration."""
# from __future__ import annotations
from datetime import timedelta
import logging

from ecoventv2 import Fan

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "fan"]

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.FAN,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoVent_v2 from a config entry."""

    coordinator = VentoFanDataUpdateCoordinator(
        hass,
        entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok


class VentoFanDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
    ) -> None:
        """Initialize global Venstar data updater."""
        self._fan = Fan(
            config.data[CONF_IP_ADDRESS],
            config.data[CONF_PASSWORD],
            config.data[CONF_DEVICE_ID],
            config.data[CONF_NAME],
            config.data[CONF_PORT],
        )
        self._fan.init_device()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
            update_method=self._fan.update(),
        )

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint.
        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        self._fan.update()

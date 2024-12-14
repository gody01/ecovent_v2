"""VentoUpdateCoordinator class."""

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
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VentoFanDataUpdateCoordinator(DataUpdateCoordinator):
    """Class for Vento Fan Update Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
    ) -> None:
        """Initialize global Vento data updater."""
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

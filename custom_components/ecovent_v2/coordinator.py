"""VentoUpdateCoordinator class."""

# from __future__ import annotations
from datetime import timedelta
import logging

from .ecoventv2 import Fan

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
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcoVentCoordinator(DataUpdateCoordinator):
    """Class for Vento Fan Update Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        update_seconds: int = 30,
    ) -> None:
        """Initialize global Vento data updater."""
        self._fan = Fan(
            config.data[CONF_IP_ADDRESS],
            config.data[CONF_PASSWORD],
            # config.data[CONF_DEVICE_ID],
            "DEFAULT_DEVICEID",
            config.data[CONF_NAME],
            config.data[CONF_PORT],
        )
        # self._fan.init_device()  is a blocking call cannot be done in constructur ...
        self.fan_initialized = False  # flag to indicate if the fan has been initialized
        self.updateCounter = 0
        _LOGGER.debug(
            "EcoVentCoordinator initialized with update rate: %d", update_seconds
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config,
            update_interval=timedelta(seconds=update_seconds),
        )

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint.

        The concept is, we have one common update rate and read all data into the fan object, then the entities read from that object. This way we can avoid multiple API calls and have a single source of truth for the data.
        """
        if not self.fan_initialized:
            _LOGGER.debug("EcoVentCoordinator: Initializing fan for the first time...")
            await self.hass.async_add_executor_job(self._fan.init_device)
            if self._fan.id is None or self._fan.id == "DEFAULT_DEVICEID":
                _LOGGER.error(
                    "EcoVentCoordinator: Failed to initialize fan, check connection and configuration."
                )
                raise ConnectionError(
                    "Failed to initialize fan, check connection and configuration."
                )
            self.fan_initialized = True

        self.updateCounter += 1
        if (self.updateCounter % 2 == 0) or (self.updateCounter < 4):
            # every 2nd update do a full update, otherwise a quick update to reduce load on the device
            _LOGGER.debug("EcoVentCoordinator: Starting full data update...")
            await self.hass.async_add_executor_job(self._fan.update)
        else:
            _LOGGER.debug("EcoVentCoordinator: Starting quick data update...")
            await self.hass.async_add_executor_job(self._fan.quick_update)


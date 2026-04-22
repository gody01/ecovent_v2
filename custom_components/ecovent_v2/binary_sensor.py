"""Vento fan binary sensors."""

from __future__ import annotations

from .ecoventv2 import Fan

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .coordinator import EcoVentCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entities."""
    async_add_entities(
        [
            VentoBinarySensor(
                hass,
                config,
                "_relay_status",
                "Relay status",
                "relay_status",
                False,
                "mdi:electric-switch",
            ),
            VentoBinarySensor(
                hass,
                config,
                "_filter_replacement_status",
                "Filter replacement required",
                "filter_replacement_status",
                True,
                "mdi:air-filter",
                BinarySensorDeviceClass.PROBLEM,
            ),
            VentoBinarySensor(
                hass,
                config,
                "_cloud_server_state",
                "Cloud server",
                "cloud_server_state",
                False,
                "mdi:cloud-check-outline",
            ),
            VentoBinarySensor(
                hass,
                config,
                "_humidity_status",
                "Humidity status",
                "humidity_status",
                False,
                "mdi:water-alert-outline",
            ),
            VentoBinarySensor(
                hass,
                config,
                "_analogV_status",
                "Analog voltage status",
                "analogV_status",
                False,
                "mdi:flash-alert-outline",
            ),
        ]
    )


class VentoBinarySensor(CoordinatorEntity, BinarySensorEntity):  # CoordinatorEntity
    """Vento Binary Sensor class."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        key="VentoBinarySensor",
        name=None,
        method=None,
        enable_by_default: bool = False,
        icon: str | None = "",
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize fan binary sensors."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_unique_id = self._fan.id + key
        self._attr_name = name
        self._state = None
        self._attr_device_class = device_class
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = method
        self._attr_icon = icon

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)}, name=self._fan.name
        )

    @property
    def is_on(self):
        """Is on."""
        self._state = getattr(self._fan, self._method) == "on"
        # self.async_write_ha_state() dangerous not allowed
        # self.schedule_update_ha_state() # not needed
        # _LOGGER.debug(f"VentoBinarySensor: {self._attr_name} state updated to {self._state}")
        return self._state

    @property
    def should_poll(self) -> bool:
        """No polling needed for this sensors. Would multiply update calls."""
        return False

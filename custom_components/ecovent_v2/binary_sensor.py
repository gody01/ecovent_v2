"""Vento fan binary sensors."""

from __future__ import annotations

from ecoventv2 import Fan

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .coordinator import VentoFanDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entities."""
    async_add_entities(
        [
            VentoBinarySensor(
                hass, config, "_boost_status", "boost_status", False, None
            ),
            VentoBinarySensor(hass, config, "_timer_mode", "timer_mode", False, None),
            VentoBinarySensor(
                hass, config, "_relay_status", "relay_status", False, None
            ),
            VentoBinarySensor(
                hass,
                config,
                "_filter_replacement_status",
                "filter_replacement_status",
                True,
                None,
            ),
            VentoBinarySensor(
                hass, config, "_alarm_status", "alarm_status", True, None
            ),
            VentoBinarySensor(
                hass,
                config,
                "_cloud_server_state",
                "cloud_server_state",
                False,
                None,
            ),
            VentoBinarySensor(
                hass, config, "_humidity_status", "humidity_status", False, None
            ),
            VentoBinarySensor(
                hass, config, "_analogV_status", "analogV_status", False, None
            ),
        ]
    )


class VentoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Vento Binary Sensor class."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name="VentoBinarySensor",
        method=None,
        enable_by_default: bool = False,
        icon: str | None = "",
        device_class=BinarySensorDeviceClass,
    ) -> None:
        """Initialize fan binary sensors."""
        coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_unique_id = self._fan.id + name
        self._attr_name = self._fan.name + name
        self._state = None
        self._sensor_type = device_class
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = getattr(self, method)
        self._attr_icon = icon

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)}, name=self._fan.name
        )

    @property
    def is_on(self):
        """Is on."""
        self._state = self._method() == "on"
        return self._state

    @property
    def should_poll(self) -> bool:
        """No polling needed for a demo binary sensor."""
        return True

    def boost_status(self) -> bool:
        """Boost status."""
        return self._fan.boost_status

    def timer_mode(self) -> bool:
        """Timer mode status."""
        return self._fan.timer_mode

    def relay_sensor_state(self) -> bool:
        """Relay sensoir state."""
        return self._fan.relay_sensor_state

    def filter_replacement_status(self) -> bool:
        """Filter replacement state state."""
        return self._fan.filter_replacement_status

    def relay_status(self) -> bool:
        """Relay status."""
        return self._fan.relay_status

    def alarm_status(self) -> bool:
        """Alarm status."""
        return self._fan.alarm_status

    def cloud_server_state(self) -> bool:
        """Cloud server state."""
        return self._fan.cloud_server_state

    def humidity_status(self) -> bool:
        """Humidity status."""
        return self._fan.humidity_status

    def analogV_status(self) -> bool:
        """AnalogV status."""
        return self._fan.analogV_status

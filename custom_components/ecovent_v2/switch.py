"""Switches on Fan device."""
from __future__ import annotations

from ecoventv2 import Fan

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VentoFanDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan switches."""
    async_add_entities(
        [
            VentoSwitch(
                hass,
                config,
                "_humidity_sensor_state",
                "humidity_sensor_state",
                SwitchDeviceClass.SWITCH,
                False,
                EntityCategory.CONFIG,
                True,
                "mdi:switch",
                False,
            ),
            VentoSwitch(
                hass,
                config,
                "_relay_sensor_state",
                "relay_sensor_state",
                SwitchDeviceClass.SWITCH,
                False,
                EntityCategory.CONFIG,
                True,
                "mdi:switch",
                False,
            ),
            VentoSwitch(
                hass,
                config,
                "_analogV_sensor_state",
                "analogV_sensor_state",
                SwitchDeviceClass.SWITCH,
                False,
                EntityCategory.CONFIG,
                True,
                "mdi:switch",
                False,
            ),
        ]
    )


class VentoSwitch(CoordinatorEntity, SwitchEntity):
    """Class for Vento Fan Switches."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name="VentoSwitch",
        method=None,
        device_class: SwitchDeviceClass | None = None,
        state: bool = False,
        entity_category=None,
        enable_by_default=False,
        icon=None,
        assumed: bool = False,
    ) -> None:
        """Init switches."""
        coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_name = self._fan.name + name
        self._attr_unique_id = self._fan.id + name
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = getattr(self, method)
        self._func = method
        self._attr_icon = icon
        self._attr_is_on = state
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._attr_is_on = True
        self._fan.set_param(self._func, "on")
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        self._attr_is_on = False
        self._fan.set_param(self._func, "off")
        self.schedule_update_ha_state()

    def humidity_sensor_state(self):
        """Humidity sensor state."""
        return self._fan.humidity_sensor_state

    def relay_sensor_state(self):
        """Relay sensor state."""
        return self._fan.relay_sensor_state

    def analogV_sensor_state(self):
        """Analog Voltage sensor state."""
        return self._fan.analogV_sensor_state

    @property
    def is_on(self) -> bool | None:
        """Is switch on."""
        self._attr_is_on = self._method() == "on"
        return self._attr_is_on

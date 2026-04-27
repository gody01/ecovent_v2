"""Switches on Fan device."""

from __future__ import annotations

from dataclasses import dataclass

from .ecoventv2 import Fan

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwitchSpec:
    """Switch description guarded by protocol capabilities."""

    key: str
    name: str
    method: str
    device_class: SwitchDeviceClass | None
    state: bool
    entity_category: EntityCategory
    enable_by_default: bool
    icon: str
    assumed: bool
    required_capabilities: tuple[str, ...] = ("sensor_switches",)


SWITCH_SPECS = (
    SwitchSpec(
        "_humidity_sensor_state",
        "Humidity sensor",
        "humidity_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:water-percent-alert",
        False,
    ),
    SwitchSpec(
        "_relay_sensor_state",
        "Relay sensor",
        "relay_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:electric-switch",
        False,
    ),
    SwitchSpec(
        "_analogV_sensor_state",
        "Analog voltage sensor",
        "analogV_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:flash-alert-outline",
        False,
    ),
    SwitchSpec(
        "_weekly_schedule_state",
        "Weekly schedule",
        "weekly_schedule_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:calendar-clock",
        False,
    ),
    SwitchSpec(
        "_light_sensor_state",
        "Light sensor",
        "light_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:brightness-5",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_motion_sensor_state",
        "Motion sensor",
        "motion_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:motion-sensor",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_temperature_sensor_state",
        "Temperature sensor",
        "temperature_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:thermometer",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_boost_status",
        "Boost",
        "boost_status",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:fan-chevron-up",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_all_day_mode",
        "All day mode",
        "all_day_mode",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:hours-24",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_interval_ventilation_state",
        "Interval ventilation",
        "interval_ventilation_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:fan-auto",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_silent_mode_state",
        "Silent mode",
        "silent_mode_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:volume-off",
        False,
        required_capabilities=("arc_environment",),
    ),
    SwitchSpec(
        "_co2_sensor_state",
        "CO2 sensor",
        "co2_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:molecule-co2",
        False,
        required_capabilities=("co2",),
    ),
    SwitchSpec(
        "_voc_sensor_state",
        "VOC sensor",
        "voc_sensor_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:air-filter",
        False,
        required_capabilities=("voc",),
    ),
    SwitchSpec(
        "_heater_state",
        "Heater",
        "heater_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        True,
        "mdi:heat-wave",
        False,
        required_capabilities=("heater",),
    ),
    SwitchSpec(
        "_screen_standby_time_state",
        "Screen standby time",
        "screen_standby_time_state",
        SwitchDeviceClass.SWITCH,
        False,
        EntityCategory.CONFIG,
        False,
        "mdi:clock-digital",
        False,
        required_capabilities=("breezy_screen",),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan switches."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [
            VentoSwitch(
                hass,
                config,
                spec.key,
                spec.name,
                spec.method,
                spec.device_class,
                spec.state,
                spec.entity_category,
                spec.enable_by_default,
                spec.icon,
                spec.assumed,
            )
            for spec in SWITCH_SPECS
            if coordinator._fan.supports_entity(
                required_params=(spec.method,),
                required_capabilities=spec.required_capabilities,
            )
        ]
    )


class VentoSwitch(CoordinatorEntity, SwitchEntity):
    """Class for Vento Fan Switches."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        key="VentoSwitch",
        name=None,
        method=None,
        device_class: SwitchDeviceClass | None = None,
        state: bool = False,
        entity_category=None,
        enable_by_default=False,
        icon=None,
        assumed: bool = False,
    ) -> None:
        """Init switches."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_name = name
        self._attr_unique_id = self._fan.id + key
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = getattr(self, method)
        #  self._attribute2 = getattr(self._fan, method)  crazy cannot be done here, only works for binary sensor.
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
        await self.hass.async_add_executor_job(self._fan.set_param, self._func, "on")
        # self._fan.set_param(self._func, "on")
        # self.schedule_update_ha_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        self._attr_is_on = False
        await self.hass.async_add_executor_job(self._fan.set_param, self._func, "off")
        # self._fan.set_param(self._func, "off")
        # self.schedule_update_ha_state()
        self.async_write_ha_state()

    def humidity_sensor_state(self):
        """Humidity sensor state."""
        return self._fan.humidity_sensor_state

    def relay_sensor_state(self):
        """Relay sensor state."""
        return self._fan.relay_sensor_state

    def analogV_sensor_state(self):
        """Analog Voltage sensor state."""
        # _LOGGER.debug(f"Getting analogV_sensor_state: {self._fan.analogV_sensor_state}")
        # _LOGGER.debug(f"Attribute2 value: {self._attribute2}")
        return self._fan.analogV_sensor_state

    def weekly_schedule_state(self):
        """Weekly schedule state."""
        return self._fan.weekly_schedule_state

    def light_sensor_state(self):
        """Light sensor state."""
        return self._fan.light_sensor_state

    def motion_sensor_state(self):
        """Motion sensor state."""
        return self._fan.motion_sensor_state

    def temperature_sensor_state(self):
        """Temperature sensor state."""
        return self._fan.temperature_sensor_state

    def boost_status(self):
        """Boost mode state."""
        return self._fan.boost_status

    def all_day_mode(self):
        """All day mode state."""
        return self._fan.all_day_mode

    def interval_ventilation_state(self):
        """Interval ventilation state."""
        return self._fan.interval_ventilation_state

    def silent_mode_state(self):
        """Silent mode state."""
        return self._fan.silent_mode_state

    def co2_sensor_state(self):
        """CO2 sensor state."""
        return self._fan.co2_sensor_state

    def voc_sensor_state(self):
        """VOC sensor state."""
        return self._fan.voc_sensor_state

    def heater_state(self):
        """Heater control state."""
        return self._fan.heater_state

    def screen_standby_time_state(self):
        """Screen standby time display state."""
        return self._fan.screen_standby_time_state

    @property
    def is_on(self) -> bool | None:
        """Is switch on."""
        self._attr_is_on = self._method() == "on"
        # self._attr_is_on = (self._attribute == "on")  # do not work reliably, use method instead
        # _LOGGER.debug(f"Switch {self._attr_name}, val [{self._attribute2}] is_on: {self._attr_is_on}")
        _LOGGER.debug(f"Switch {self._attr_name} is_on: {self._attr_is_on}")
        return self._attr_is_on

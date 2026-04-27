"""Vento fan binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class BinarySensorSpec:
    """Binary sensor description guarded by protocol capabilities."""

    key: str
    name: str
    method: str
    enable_by_default: bool
    icon: str
    device_class: BinarySensorDeviceClass | None = None
    required_capabilities: tuple[str, ...] = ("binary_diagnostics",)
    on_values: tuple[str, ...] = ("on",)


BINARY_SENSOR_SPECS = (
    BinarySensorSpec(
        "_relay_status",
        "Relay status",
        "relay_status",
        False,
        "mdi:electric-switch",
    ),
    BinarySensorSpec(
        "_filter_replacement_status",
        "Filter replacement required",
        "filter_replacement_status",
        True,
        "mdi:air-filter",
        BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorSpec(
        "_alarm_status",
        "Alarm status",
        "alarm_status",
        True,
        "mdi:alert-outline",
        BinarySensorDeviceClass.PROBLEM,
        required_capabilities=(),
        on_values=("alarm", "warning"),
    ),
    BinarySensorSpec(
        "_cloud_server_state",
        "Cloud server",
        "cloud_server_state",
        False,
        "mdi:cloud-check-outline",
    ),
    BinarySensorSpec(
        "_humidity_status",
        "Humidity status",
        "humidity_status",
        False,
        "mdi:water-alert-outline",
    ),
    BinarySensorSpec(
        "_low_battery_status",
        "Low battery",
        "low_battery_status",
        False,
        "mdi:battery-alert",
        BinarySensorDeviceClass.PROBLEM,
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_light_status",
        "Light status",
        "light_status",
        False,
        "mdi:brightness-5",
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_motion_status",
        "Motion status",
        "motion_status",
        False,
        "mdi:motion-sensor",
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_temperature_status",
        "Temperature status",
        "temperature_status",
        False,
        "mdi:thermometer-alert",
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_interval_ventilation_status",
        "Interval ventilation status",
        "interval_ventilation_status",
        False,
        "mdi:fan-auto",
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_silent_mode_status",
        "Silent mode status",
        "silent_mode_status",
        False,
        "mdi:volume-off",
        required_capabilities=("arc_environment",),
    ),
    BinarySensorSpec(
        "_analogV_status",
        "Analog voltage status",
        "analogV_status",
        False,
        "mdi:flash-alert-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entities."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [
            VentoBinarySensor(
                hass,
                config,
                spec.key,
                spec.name,
                spec.method,
                spec.enable_by_default,
                spec.icon,
                spec.device_class,
                spec.on_values,
            )
            for spec in BINARY_SENSOR_SPECS
            if coordinator._fan.supports_entity(
                required_params=(spec.method,),
                required_capabilities=spec.required_capabilities,
            )
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
        on_values: tuple[str, ...] = ("on",),
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
        self._on_values = on_values
        self._attr_icon = icon

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)}, name=self._fan.name
        )

    @property
    def is_on(self):
        """Is on."""
        value = getattr(self._fan, self._method)
        self._state = None if value is None else value in self._on_values
        # self.async_write_ha_state() dangerous not allowed
        # self.schedule_update_ha_state() # not needed
        # _LOGGER.debug(f"VentoBinarySensor: {self._attr_name} state updated to {self._state}")
        return self._state

    @property
    def should_poll(self) -> bool:
        """No polling needed for this sensors. Would multiply update calls."""
        return False

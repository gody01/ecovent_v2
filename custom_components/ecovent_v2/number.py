"""Vento platform that offers a fake Number entity."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .ecoventv2 import Fan

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NumberSpec:
    """Number entity description guarded by protocol capabilities."""

    name: str
    method: str
    icon: str
    enable_by_default: bool
    mode: NumberMode = NumberMode.AUTO
    entity_category: EntityCategory = EntityCategory.CONFIG
    native_min_value: float | None = None
    native_max_value: float | None = None
    native_step: float | None = None
    unit_of_measurement: str | None = None
    device_class: NumberDeviceClass | None = None
    required_capabilities: tuple[str, ...] = ()
    value_bytes: int = 1


NUMBER_SPECS = (
    NumberSpec(
        "Humidity threshold",
        "humidity_treshold",
        "mdi:water-percent",
        False,
        native_min_value=40.0,
        native_max_value=80.0,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
    ),
    NumberSpec(
        "Temperature threshold",
        "temperature_treshold",
        "mdi:thermometer",
        False,
        native_min_value=18.0,
        native_max_value=36.0,
        native_step=1,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        required_capabilities=("temperature",),
    ),
    NumberSpec(
        "Max speed setpoint",
        "max_speed_setpoint",
        "mdi:fan-speed-3",
        False,
        native_min_value=30.0,
        native_max_value=100.0,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
        required_capabilities=("speed_setpoints",),
    ),
    NumberSpec(
        "Silent speed setpoint",
        "silent_speed_setpoint",
        "mdi:fan-speed-1",
        False,
        native_min_value=30.0,
        native_max_value=100.0,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
        required_capabilities=("speed_setpoints",),
    ),
    NumberSpec(
        "Interval ventilation speed setpoint",
        "interval_ventilation_speed_setpoint",
        "mdi:fan-auto",
        False,
        native_min_value=30.0,
        native_max_value=100.0,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
        required_capabilities=("speed_setpoints",),
    ),
    NumberSpec(
        "Analog voltage threshold",
        "analogV_treshold",
        "mdi:flash-triangle-outline",
        False,
        native_min_value=0.0,
        native_max_value=100.0,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
        required_capabilities=("analog_voltage",),
    ),
    NumberSpec(
        "Boost time",
        "boost_time",
        "mdi:fan-clock",
        False,
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        unit_of_measurement="min",
        required_capabilities=("timer_mode",),
    ),
    NumberSpec(
        "Filter timer setpoint",
        "filter_timer_setpoint",
        "mdi:air-filter",
        False,
        native_min_value=10,
        native_max_value=999,
        native_step=1,
        unit_of_measurement="d",
        required_capabilities=("filter_maintenance",),
        value_bytes=2,
    ),
    NumberSpec(
        "CO2 threshold",
        "co2_treshold",
        "mdi:molecule-co2",
        False,
        native_min_value=400,
        native_max_value=2000,
        native_step=10,
        unit_of_measurement="ppm",
        required_capabilities=("co2",),
        value_bytes=2,
    ),
    NumberSpec(
        "VOC threshold",
        "voc_treshold",
        "mdi:air-filter",
        False,
        native_min_value=50,
        native_max_value=250,
        native_step=1,
        unit_of_measurement="index",
        required_capabilities=("voc",),
        value_bytes=2,
    ),
    NumberSpec(
        "Screen brightness",
        "screen_brightness",
        "mdi:brightness-6",
        False,
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        unit_of_measurement=PERCENTAGE,
        required_capabilities=("breezy_screen",),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vento config entry."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [
            VentoNumber(
                hass,
                config,
                spec.name,
                spec.method,
                None,
                spec.icon,
                spec.enable_by_default,
                device_class=spec.device_class,
                mode=spec.mode,
                entity_category=spec.entity_category,
                native_min_value=spec.native_min_value,
                native_max_value=spec.native_max_value,
                native_step=spec.native_step,
                unit_of_measurement=spec.unit_of_measurement,
                value_bytes=spec.value_bytes,
            )
            for spec in NUMBER_SPECS
            if coordinator._fan.supports_entity(
                required_params=(spec.method,),
                required_capabilities=spec.required_capabilities,
            )
        ]
    )


class VentoNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Vento Number entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name="VentoNumber",
        method="",
        state=None,
        icon=None,
        assumed_state=False,
        *,
        device_class: NumberDeviceClass | None = None,
        mode: NumberMode = NumberMode.AUTO,
        entity_category: EntityCategory = EntityCategory.CONFIG,
        native_min_value: float | None = None,
        native_max_value: float | None = None,
        native_step: float | None = None,
        unit_of_measurement: str | None = None,
        value_bytes: int = 1,
    ) -> None:
        """Initialize the Vento Number entity."""

        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)

        self._fan: Fan = coordinator._fan
        self._attr_assumed_state = assumed_state
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_mode = mode
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_name = name
        self._attr_unique_id = self._fan.id + method
        self._attr_native_value = getattr(self._fan, method)
        self._func = method
        self._value_bytes = value_bytes

        if native_min_value is not None:
            self._attr_native_min_value = native_min_value
        if native_max_value is not None:
            self._attr_native_max_value = native_max_value
        if native_step is not None:
            self._attr_native_step = native_step
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def native_value(self) -> float | None:
        """Return the numeric part of the current device value."""
        value = getattr(self._fan, self._func)
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value

        match = re.match(r"(?P<value>\d+(?:\.\d+)?)", str(value))
        if match is None:
            return None

        return float(match.group("value"))

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        intval = int(value)
        if self._value_bytes > 1:
            value_hex = intval.to_bytes(self._value_bytes, "little").hex()
        else:
            value_hex = hex(intval).replace("0x", "").zfill(2)
        await self.hass.async_add_executor_job(
            self._fan.set_param,
            self._func,
            value_hex,
        )
        self.async_write_ha_state()
        await self.coordinator.async_refresh()

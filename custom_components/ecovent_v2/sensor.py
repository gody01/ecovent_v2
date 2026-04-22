"""EcoVentV2 platform sensors."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from .ecoventv2 import Fan

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE, EntityCategory
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SensorSpec:
    """Sensor description guarded by protocol parameters and capabilities."""

    key: str
    name: str
    method: str
    native_unit_of_measurement: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None
    enable_by_default: bool = True
    icon: str | None = None
    translation_key: str | None = None
    suggested_display_precision: int | None = None
    required_params: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    excluded_params: tuple[str, ...] = ()
    excluded_capabilities: tuple[str, ...] = ()


SENSOR_SPECS = (
    SensorSpec(
        "_humidity",
        "Humidity",
        "humidity",
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
    ),
    SensorSpec(
        "_temperature",
        "Temperature",
        "temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        required_capabilities=("temperature",),
    ),
    SensorSpec(
        "_room_temperature",
        "Room temperature",
        "room_temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:home-thermometer-outline",
        required_params=("room_temperature",),
    ),
    SensorSpec(
        "_outdoor_temperature",
        "Outdoor temperature",
        "outdoor_temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-lines",
        required_capabilities=("temperature_probes",),
    ),
    SensorSpec(
        "_supply_temperature",
        "Supply temperature",
        "supply_temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-chevron-up",
        required_capabilities=("temperature_probes",),
    ),
    SensorSpec(
        "_exhaust_in_temperature",
        "Exhaust inlet temperature",
        "exhaust_in_temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-chevron-down",
        required_capabilities=("temperature_probes",),
    ),
    SensorSpec(
        "_exhaust_out_temperature",
        "Exhaust outlet temperature",
        "exhaust_out_temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-low",
        required_capabilities=("temperature_probes",),
    ),
    SensorSpec(
        "_co2",
        "CO2",
        "co2",
        "ppm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule-co2",
        required_capabilities=("co2",),
    ),
    SensorSpec(
        "_voc",
        "VOC",
        "voc",
        "index",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        required_capabilities=("voc",),
    ),
    SensorSpec(
        "_air_quality",
        "Air quality",
        "air_quality",
        "index",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        required_params=("air_quality",),
    ),
    SensorSpec(
        "_speed",
        "Fan speed",
        "fan1_speed",
        REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
        excluded_params=("fan2_speed",),
    ),
    SensorSpec(
        "_speed1",
        "Fan 1 speed",
        "fan1_speed",
        REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan-speed-1",
        required_params=("fan1_speed", "fan2_speed"),
    ),
    SensorSpec(
        "_speed2",
        "Fan 2 speed",
        "fan2_speed",
        REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:fan-speed-2",
        required_params=("fan2_speed",),
    ),
    SensorSpec(
        "_airflow",
        "Airflow",
        "airflow",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:hvac",
        translation_key="airflow",
        required_capabilities=("airflow",),
    ),
    SensorSpec(
        "_beeper",
        "Beeper",
        "beeper",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:volume-high",
        translation_key="beeper",
        required_capabilities=("beeper_status",),
    ),
    SensorSpec(
        "_battery_status",
        "Battery status",
        "battery_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery",
        translation_key="battery_status",
        required_capabilities=("battery_status",),
    ),
    SensorSpec(
        "_boost_status",
        "Boost status",
        "boost_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan-chevron-up",
        translation_key="boost_status",
        required_capabilities=("toggle_boost_status",),
    ),
    SensorSpec(
        "_boost_status",
        "Boost status",
        "boost_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan-chevron-up",
        translation_key="boost_status",
        required_capabilities=("boost_delay_status",),
    ),
    SensorSpec(
        "_timer_mode",
        "Timer mode",
        "timer_mode",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:timer-cog-outline",
        translation_key="timer_mode",
        required_capabilities=("timer_mode",),
    ),
    SensorSpec(
        "_timer_status",
        "Timer status",
        "timer_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:timer-check-outline",
        required_capabilities=("arc_environment",),
    ),
    SensorSpec(
        "_alarm_status",
        "Alarm status",
        "alarm_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-outline",
        translation_key="alarm_status",
    ),
    SensorSpec(
        "_alarm_list",
        "Alarm list",
        "alarm_list",
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:alert-box-outline",
        required_capabilities=("air_quality",),
    ),
    SensorSpec(
        "_heater_status",
        "Heater status",
        "heater_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:heat-wave",
        required_capabilities=("heater",),
    ),
    SensorSpec(
        "_air_quality_status",
        "Air quality status",
        "air_quality_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:air-filter",
        required_capabilities=("air_quality",),
    ),
    SensorSpec(
        "_air_quality_status",
        "Air quality status",
        "air_quality_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:air-filter",
        required_capabilities=("arc_environment",),
    ),
    SensorSpec(
        "_recovery_efficiency",
        "Recovery efficiency",
        "recovery_efficiency",
        PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heat-pump-outline",
        required_capabilities=("air_quality",),
    ),
    SensorSpec(
        "_schedule_speed",
        "Schedule speed",
        "schedule_speed",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        required_capabilities=("air_quality",),
    ),
    SensorSpec(
        "_frost_protection_status",
        "Frost protection",
        "frost_protection_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:snowflake-alert",
        required_capabilities=("air_quality",),
    ),
    SensorSpec(
        "_timer_counter",
        "Timer counter",
        "timer_counter",
        "h",
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        False,
        "mdi:timer-play-outline",
    ),
    SensorSpec(
        "_battery",
        "Battery",
        "battery_voltage",
        PERCENTAGE,
        SensorDeviceClass.BATTERY,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        icon="mdi:battery",
        required_capabilities=("battery_voltage",),
    ),
    SensorSpec(
        "_filter_change_in",
        "Filter change in",
        "filter_timer_countdown",
        "h",
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-sand",
        suggested_display_precision=1,
        required_capabilities=("filter_maintenance",),
    ),
    SensorSpec(
        "_filter_remaining",
        "Filter remaining",
        "filter_remaining",
        PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:air-filter",
        suggested_display_precision=0,
        required_params=("filter_timer_countdown", "filter_timer_setpoint"),
        required_capabilities=("filter_maintenance",),
    ),
    SensorSpec(
        "_night_mode_timer",
        "Night mode timer",
        "night_mode_timer",
        "h",
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        False,
        "mdi:weather-night",
        suggested_display_precision=2,
        required_capabilities=("night_party_timers",),
    ),
    SensorSpec(
        "_party_mode_timer",
        "Party mode timer",
        "party_mode_timer",
        "h",
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        False,
        "mdi:party-popper",
        suggested_display_precision=2,
        required_capabilities=("night_party_timers",),
    ),
    SensorSpec(
        "_analogv",
        "Analog voltage",
        "analogv",
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:flash",
        required_params=("analogV",),
        required_capabilities=("analog_voltage",),
    ),
    SensorSpec(
        "_machine_hours",
        "Machine hours",
        "machine_hours",
        "h",
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        EntityCategory.DIAGNOSTIC,
        False,
        "mdi:timer-outline",
    ),
    SensorSpec(
        "_screen_off_start_time",
        "Screen off start time",
        "screen_off_start_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:clock-start",
        required_capabilities=("breezy_screen",),
    ),
    SensorSpec(
        "_screen_off_end_time",
        "Screen off end time",
        "screen_off_end_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        enable_by_default=False,
        icon="mdi:clock-end",
        required_capabilities=("breezy_screen",),
    ),
    SensorSpec(
        "_ip",
        "IP address",
        "current_wifi_ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
)


def _parse_hours(
    value: str | None, pattern: str, precision: int | None = None
) -> float | None:
    """Parse device duration strings and expose them as hours."""
    if value is None:
        return None

    match = re.match(pattern, value)
    if not match:
        return None

    parts = {key: int(val) for key, val in match.groupdict().items() if val is not None}
    total_hours = (
        parts.get("days", 0) * 24
        + parts.get("hours", 0)
        + parts.get("minutes", 0) / 60
        + parts.get("seconds", 0) / 3600
    )
    if precision is not None:
        return round(total_hours, precision)
    return total_hours


def _parse_days(value: str | None) -> int | None:
    """Parse simple device duration strings formatted as days."""
    if value is None:
        return None

    match = re.match(r"(?P<days>\d+) d", value)
    if not match:
        return None

    return int(match.group("days"))


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vento Sensors."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [
            VentoSensor(
                hass,
                config,
                spec.key,
                spec.name,
                spec.method,
                spec.native_unit_of_measurement,
                spec.device_class,
                spec.state_class,
                spec.entity_category,
                spec.enable_by_default,
                spec.icon,
                translation_key=spec.translation_key,
                suggested_display_precision=spec.suggested_display_precision,
            )
            for spec in SENSOR_SPECS
            if coordinator._fan.supports_entity(
                required_params=spec.required_params or (spec.method,),
                required_capabilities=spec.required_capabilities,
                excluded_params=spec.excluded_params,
                excluded_capabilities=spec.excluded_capabilities,
            )
        ]
    )


# VentoSensor class
class VentoSensor(CoordinatorEntity, SensorEntity):
    """Class for Vento Fan Sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        key="VentoSensor",
        name=None,
        method=None,
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        entity_category=None,
        enable_by_default=True,
        icon=None,
        options=None,
        *,
        suggested_display_precision: int | None = None,
        translation_key: str | None = None,
    ) -> None:
        """Initialize fan sensors."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_name = name
        self._attr_unique_id = self._fan.id + key
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = getattr(self, method)
        self._attr_icon = icon
        self._attr_options = options or self._fan.parameter_options(method)
        self._attr_translation_key = translation_key
        if suggested_display_precision is not None:
            self._attr_suggested_display_precision = suggested_display_precision
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def native_value(self):
        """Get native value property from method."""
        self._attr_native_value = self._method()
        return self._attr_native_value

    def get_native_value(self):
        """Get native value method."""
        val = self._fan.get_param(self._method)
        return val

    def humidity(self):
        """Get humidity sensor value."""
        return self._fan.humidity

    def temperature(self):
        """Get temperature sensor value."""
        return self._fan.temperature

    def room_temperature(self):
        """Get room temperature value."""
        return self._fan.room_temperature

    def outdoor_temperature(self):
        """Get outdoor air temperature."""
        return self._fan.outdoor_temperature

    def supply_temperature(self):
        """Get supply air temperature after reheater."""
        return self._fan.supply_temperature

    def exhaust_in_temperature(self):
        """Get exhaust air temperature at the inlet."""
        return self._fan.exhaust_in_temperature

    def exhaust_out_temperature(self):
        """Get exhaust air temperature at the outlet."""
        return self._fan.exhaust_out_temperature

    def co2(self):
        """Get indoor CO2 level."""
        return self._fan.co2

    def voc(self):
        """Get indoor VOC air quality index."""
        return self._fan.voc

    def air_quality(self):
        """Get indoor air quality index."""
        return self._fan.air_quality

    def fan1_speed(self):
        """Get fan1 speed value."""
        return self._fan.fan1_speed

    def fan2_speed(self):
        """Get fan2 speed value."""
        return self._fan.fan2_speed

    def airflow(self):
        """Get airflow value."""
        return self._fan.airflow

    def beeper(self):
        """Get beeper command mode reported by the device."""
        return self._fan.beeper

    def battery_status(self):
        """Get enum battery status."""
        return self._fan.battery_status

    def boost_status(self):
        """Get boost status."""
        return self._fan.boost_status

    def timer_mode(self):
        """Get timer mode."""
        return self._fan.timer_mode

    def timer_status(self):
        """Get timer status."""
        return self._fan.timer_status

    def alarm_status(self):
        """Get alarm status."""
        return self._fan.alarm_status

    def alarm_list(self):
        """Get current alarm list."""
        return self._fan.alarm_list

    def heater_status(self):
        """Get heater status."""
        return self._fan.heater_status

    def air_quality_status(self):
        """Get compound air quality status."""
        return self._fan.air_quality_status

    def recovery_efficiency(self):
        """Get recovery efficiency."""
        return self._fan.recovery_efficiency

    def schedule_speed(self):
        """Get current schedule speed."""
        return self._fan.schedule_speed

    def frost_protection_status(self):
        """Get frost protection status."""
        return self._fan.frost_protection_status

    def battery_voltage(self):
        """Get battery used percentage."""
        high = 3300
        low = 2500
        value = self._fan.battery_voltage
        if value is None:
            return None

        if isinstance(value, (int, float)):
            voltage = int(value)
        else:
            match = re.match(r"(?P<voltage>\d+)", str(value))
            if match is None:
                return None
            voltage = int(match.group("voltage"))
        voltage = round(((voltage - low) / (high - low)) * 100)
        return min(100, max(0, voltage))

    def timer_counter(self):
        """Get timer counter value as total hours."""
        return _parse_hours(
            self._fan.timer_counter,
            r"(?P<hours>\d+)h (?P<minutes>\d+)m (?P<seconds>\d+)s",
            3,
        )

    def filter_timer_countdown(self):
        """Get filter time countdown as total hours."""
        return _parse_hours(
            self._fan.filter_timer_countdown,
            r"(?P<days>\d+)d (?P<hours>\d+)h (?P<minutes>\d+)m",
            1,
        )

    def filter_remaining(self):
        """Get filter lifetime remaining as a percentage."""
        remaining_hours = self.filter_timer_countdown()
        setpoint_days = _parse_days(self._fan.filter_timer_setpoint)
        if remaining_hours is None or not setpoint_days:
            return None

        remaining = remaining_hours / (setpoint_days * 24) * 100
        return min(100, max(0, round(remaining)))

    def night_mode_timer(self):
        """Get night mode timer value as total hours."""
        return _parse_hours(
            self._fan.night_mode_timer,
            r"(?P<hours>\d+)h (?P<minutes>\d+)m",
            2,
        )

    def party_mode_timer(self):
        """Get party mode timer value as total hours."""
        return _parse_hours(
            self._fan.party_mode_timer,
            r"(?P<hours>\d+)h (?P<minutes>\d+)m",
            2,
        )

    def machine_hours(self):
        """Get machine hours value as total hours."""
        return _parse_hours(
            self._fan.machine_hours,
            r"(?P<days>\d+)d (?P<hours>\d+)h (?P<minutes>\d+)m",
            1,
        )

    def screen_off_start_time(self):
        """Get screen display off interval start."""
        return self._fan.screen_off_start_time

    def screen_off_end_time(self):
        """Get screen display off interval end."""
        return self._fan.screen_off_end_time

    def analogv(self):
        """Get analog Voltage value."""
        return self._fan.analogV

    def current_wifi_ip(self):
        """Get current wifi IP value."""
        return self._fan.current_wifi_ip

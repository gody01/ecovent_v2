"""EcoVentV2 platform sensors."""

from __future__ import annotations

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator

_LOGGER = logging.getLogger(__name__)


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
    async_add_entities(
        [
            VentoSensor(
                hass,
                config,
                "_humidity",
                "Humidity",
                "humidity",
                PERCENTAGE,
                SensorDeviceClass.HUMIDITY,
                SensorStateClass.MEASUREMENT,
                None,
                True,
                "mdi:water-percent",
            ),
            VentoSensor(
                hass,
                config,
                "_speed1",
                "Fan 1 speed",
                "fan1_speed",
                REVOLUTIONS_PER_MINUTE,
                None,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:fan-speed-1",
            ),
            VentoSensor(
                hass,
                config,
                "_speed2",
                "Fan 2 speed",
                "fan2_speed",
                REVOLUTIONS_PER_MINUTE,
                None,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                False,
                "mdi:fan-speed-2",
            ),
            VentoSensor(
                hass,
                config,
                "_airflow",
                "Airflow",
                "airflow",
                None,
                SensorDeviceClass.ENUM,
                None,
                None,
                True,
                "mdi:hvac",
                ["ventilation", "heat_recovery", "air_supply"],
                translation_key="airflow",
            ),
            VentoSensor(
                hass,
                config,
                "_beeper",
                "Beeper",
                "beeper",
                None,
                SensorDeviceClass.ENUM,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:volume-high",
                ["off", "on", "silent"],
                translation_key="beeper",
            ),
            VentoSensor(
                hass,
                config,
                "_boost_status",
                "Boost status",
                "boost_status",
                None,
                SensorDeviceClass.ENUM,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:fan-chevron-up",
                ["off", "on", "delay"],
                translation_key="boost_status",
            ),
            VentoSensor(
                hass,
                config,
                "_timer_mode",
                "Timer mode",
                "timer_mode",
                None,
                SensorDeviceClass.ENUM,
                None,
                EntityCategory.DIAGNOSTIC,
                False,
                "mdi:timer-cog-outline",
                ["off", "night", "party"],
                translation_key="timer_mode",
            ),
            VentoSensor(
                hass,
                config,
                "_alarm_status",
                "Alarm status",
                "alarm_status",
                None,
                SensorDeviceClass.ENUM,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:alert-outline",
                ["no", "alarm", "warning"],
                translation_key="alarm_status",
            ),
            VentoSensor(
                hass,
                config,
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
            VentoSensor(
                hass,
                config,
                "_battery",
                "Battery",
                "battery_voltage",
                PERCENTAGE,
                SensorDeviceClass.BATTERY,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:battery",
            ),
            VentoSensor(
                hass,
                config,
                "_filter_change_in",
                "Filter change in",
                "filter_timer_countdown",
                "h",
                SensorDeviceClass.DURATION,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-sand",
                suggested_display_precision=1,
            ),
            VentoSensor(
                hass,
                config,
                "_filter_remaining",
                "Filter remaining",
                "filter_remaining",
                PERCENTAGE,
                None,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:air-filter",
                suggested_display_precision=0,
            ),
            VentoSensor(
                hass,
                config,
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
            ),
            VentoSensor(
                hass,
                config,
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
            ),
            VentoSensor(
                hass,
                config,
                "_analogv",
                "Analog voltage",
                "analogv",
                None,
                None,
                None,
                EntityCategory.DIAGNOSTIC,
                False,
                "mdi:flash",
            ),
            VentoSensor(
                hass,
                config,
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
            VentoSensor(
                hass,
                config,
                "_ip",
                "IP address",
                "current_wifi_ip",
                None,
                None,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:ip-network",
            ),
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
        self._attr_options = options
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

    def boost_status(self):
        """Get boost status."""
        return self._fan.boost_status

    def timer_mode(self):
        """Get timer mode."""
        return self._fan.timer_mode

    def alarm_status(self):
        """Get alarm status."""
        return self._fan.alarm_status

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

    def analogv(self):
        """Get analog Voltage value."""
        return self._fan.analogV

    def current_wifi_ip(self):
        """Get current wifi IP value."""
        return self._fan.current_wifi_ip

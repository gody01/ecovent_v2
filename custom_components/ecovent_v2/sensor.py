"""EcoVentV2 platform sensors."""
from __future__ import annotations

from ecoventv2 import Fan

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
from .coordinator import VentoFanDataUpdateCoordinator

import re

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
                "airflow",
                None,
                None,
                None,
                None,
                True,
            ),
            VentoSensor(
                hass,
                config,
                "_timer_counter",
                "timer_counter",
                "h",
                SensorDeviceClass.DURATION,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                False,
            ),
            VentoSensor(
                hass,
                config,
                "_battery",
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
                "filter_timer_countdown",
                "h",
                SensorDeviceClass.DURATION,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-sand",
            ),
            VentoSensor(
                hass,
                config,
                "_analogv",
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

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name="VentoSensor",
        method=None,
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        entity_category=None,
        enable_by_default=True,
        icon=None,
    ) -> None:
        """Initialize fan sensors."""
        coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_name = self._fan.name + name
        self._attr_unique_id = self._fan.id + name
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method = getattr(self, method)
        self._attr_icon = icon
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

    def battery_voltage(self):
        """Get battery used percentage."""
        high = 3300
        low = 2500
        if self._fan.battery_voltage is None:
            voltage = 0
        else:
            voltage = int(self._fan.battery_voltage.split()[0])
            voltage = round(((voltage - low) / (high - low)) * 100)
        return voltage

    def timer_counter(self):
        """Get timer counter value as total hours."""
        timer_counter_str = self._fan.timer_counter

        # Use regex to extract days, hours, and minutes
        match = re.match(r"(\d+)h (\d+)m (\d+)s", timer_counter_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))

            # Convert everything to total hours
            total_hours = hours + minutes / 60 + seconds / 3600
            return total_hours
        return None  # In case the string format is unexpected

    def filter_timer_countdown(self):
        """Get filter time countdown as total hours."""
        remaining_time_str = self._fan.filter_timer_countdown

        # Use regex to extract days, hours, and minutes
        match = re.match(r"(\d+)d (\d+)h (\d+)m", remaining_time_str)
        if match:
            days = int(match.group(1))
            hours = int(match.group(2))
            minutes = int(match.group(3))

            # Convert everything to total hours
            total_hours = days * 24 + hours + minutes / 60
            return total_hours
        return None  # In case the string format is unexpected

    def machine_hours(self):
        """Get machine hours value as total hours."""
        machine_hours_str = self._fan.machine_hours

        # Use regex to extract days, hours, and minutes
        match = re.match(r"(\d+)d (\d+)h (\d+)m", machine_hours_str)
        if match:
            days = int(match.group(1))
            hours = int(match.group(2))
            minutes = int(match.group(3))

            # Convert everything to total hours
            total_hours = days * 24 + hours + minutes / 60
            return total_hours
        return None  # In case the string format is unexpected


    def analogv(self):
        """Get analog Voltage value."""
        return self._fan.analogV

    def current_wifi_ip(self):
        """Get current wifi IP value."""
        return self._fan.curent_wifi_ip

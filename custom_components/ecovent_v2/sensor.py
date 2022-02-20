"""EcoVentV2 platform sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    CONCENTRATION_PARTS_PER_MILLION,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    FREQUENCY_HERTZ,
    POWER_WATT,
    TEMP_CELSIUS,
    DEVICE_CLASS_HUMIDITY,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from . import VentoFan
from .const import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Demo sensors."""
    async_add_entities(
        [
            HumiditySensor(hass, config),
            Fan1SpeedSensor(hass, config),
            Fan2SpeedSensor(hass, config),
            AirflowSensor(hass, config),
        ],
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Demo config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


class HumiditySensor(SensorEntity):
    """Representation of a Humidity sensor."""

    _attr_should_poll = True

    def __init__(self, hass, config) -> None:
        """Initialize the sensor."""

        component: VentoFan = hass.data[DOMAIN][config.entry_id]
        self._fan = component._fan

        self._attr_name = "Humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_name = self._fan.name + "_humidity"
        self._attr_unique_id = self._fan.id + "_humidity"
        self._attr_native_value = self._fan.humidity
        self._humidity = self._fan.humidity

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._fan.update()
        self._humidity = self._fan.humidity
        self._attr_native_value = self._fan.humidity

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class Fan1SpeedSensor(SensorEntity):
    """Fan Speed 1."""

    _attr_should_poll = True

    def __init__(self, hass, config) -> None:
        """Initialize the sensor."""

        component: VentoFan = hass.data[DOMAIN][config.entry_id]
        self._fan = component._fan

        self._attr_native_unit_of_measurement = "rpm"
        self._attr_device_class = None
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_name = self._fan.name + "_speed1"
        self._attr_unique_id = self._fan.id + "_speed1"
        self._attr_native_value = self._fan.fan1_speed

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._fan.update()
        self._attr_native_value = self._fan.fan1_speed

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class Fan2SpeedSensor(SensorEntity):
    """Fan Speed 2."""

    _attr_should_poll = True

    def __init__(self, hass, config) -> None:
        """Initialize the sensor."""

        component: VentoFan = hass.data[DOMAIN][config.entry_id]
        self._fan = component._fan

        self._attr_native_unit_of_measurement = "rpm"
        self._attr_device_class = None
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_name = self._fan.name + "_speed2"
        self._attr_unique_id = self._fan.id + "_speed2"
        self._attr_native_value = self._fan.fan2_speed

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._fan.update()
        self._attr_native_value = self._fan.fan2_speed

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class AirflowSensor(SensorEntity):
    """Airflow sensor."""

    _attr_should_poll = True

    def __init__(self, hass, config) -> None:
        """Initialize the sensor."""

        component: VentoFan = hass.data[DOMAIN][config.entry_id]
        self._fan = component._fan

        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_name = self._fan.name + "_airflow"
        self._attr_unique_id = self._fan.id + "_airflow"
        self._attr_native_value = self._fan.airflow

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._fan.update()
        self._attr_native_value = self._fan.airflow

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }

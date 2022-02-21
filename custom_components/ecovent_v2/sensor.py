"""EcoVentV2 platform sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

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


class HumiditySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    # _attr_state_class = SensorStateClass.MEASUREMENT
    # _attr_device_class = None
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, hass, config) -> None:
        """Initialize the sensor."""
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan = coordinator._fan

        self._attr_name = self._fan.name + "_humidity"
        self._attr_unique_id = self._fan.id + "_humidity"

    @property
    def native_value(self):
        return self._fan.humidity

    # @property
    # def humidity(self):
    #    return self._fan.humidity

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class Fan1SpeedSensor(CoordinatorEntity, SensorEntity):

    _attr_device_class = None
    _attr_state_class = None
    # _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "rpm"

    def __init__(self, hass, config) -> None:
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)

        self._fan = coordinator._fan
        self._attr_unique_id = self._fan.id + "_speed1"
        self._attr_name = self._fan.name + "_speed1"

    @property
    def native_value(self):
        return self._fan.fan1_speed

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class Fan2SpeedSensor(CoordinatorEntity, SensorEntity):

    _attr_device_class = None
    _attr_state_class = None
    # _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "rpm"

    def __init__(self, hass, config) -> None:
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan = coordinator._fan

        self._attr_name = self._fan.name + "_speed2"
        self._attr_unique_id = self._fan.id + "_speed2"

    @property
    def native_value(self):
        return self._fan.fan2_speed

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }


class AirflowSensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = None
    _attr_device_class = None
    _attr_state_class = None

    def __init__(self, hass, config) -> None:
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan = coordinator._fan
        self._attr_name = self._fan.name + "_airflow"
        self._attr_unique_id = self._fan.id + "_airflow"

    @property
    def native_value(self):
        return self._fan.airflow

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._attr_name,
        }

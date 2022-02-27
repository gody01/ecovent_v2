"""EcoVentV2 platform sensors."""
from __future__ import annotations
from xml.sax.handler import property_encoding

from numpy import False_

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from ecoventv2 import Fan
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
                None,
                None,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:fan-speed-1",
            ),
            VentoSensor(
                hass,
                config,
                "_speed2",
                "fan2_speed",
                None,
                None,
                None,
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
                None,
                None,
                None,
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
                "_humidity_treshold",
                "humidity_treshold",
                PERCENTAGE,
                None,
                None,
                EntityCategory.CONFIG,
                True,
                "mdi:water-percent-alert",
            ),
            VentoSensor(
                hass,
                config,
                "_filter_change_in",
                "filter_timer_countdown",
                None,
                None,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-sand",
            ),
            VentoSensor(
                hass,
                config,
                "_boost_time",
                "boost_time",
                None,
                None,
                None,
                EntityCategory.CONFIG,
                False,
                "mdi:timer-outline",
            ),
            VentoSensor(
                hass,
                config,
                "_analogV",
                "analogV",
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
                "_analogV_treshold",
                "analogV_treshold",
                None,
                None,
                None,
                EntityCategory.CONFIG,
                False,
                "mdi:flash-alert",
            ),
            VentoSensor(
                hass,
                config,
                "_machine_hours",
                "machine_hours",
                None,
                None,
                None,
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
        ],
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Demo config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


class VentoSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        hass,
        config,
        name="VentoSensor",
        method=None,
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        entity_category=None,
        enable_by_default=True,
        icon=None,
    ) -> None:
        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
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

    @property
    def native_value(self):
        self._attr_native_value = self._method()
        return self._attr_native_value

    def get_native_value(self):
        val = self._fan.get_param(self._method)
        return val

    def humidity(self):
        return self._fan.humidity

    def fan1_speed(self):
        return self._fan.fan1_speed

    def fan2_speed(self):
        return self._fan.fan2_speed

    def airflow(self):
        return self._fan.airflow

    def battery_voltage(self):
        high = 3300
        low = 2500
        voltage = int(self._fan.battery_voltage.split()[0])
        voltage = round(((voltage - low) / (high - low)) * 100)
        return voltage

    def timer_counter(self):
        return self._fan.timer_counter

    def humidity_treshold(self):
        return self._fan.humidity_treshold

    def filter_timer_countdown(self):
        return self._fan.filter_timer_countdown

    def boost_time(self):
        return self._fan.boost_time

    def machine_hours(self):
        return self._fan.machine_hours

    def analogV(self):
        return self._fan.analogV

    def analogV_treshold(self):
        return self._fan.analogV_treshold

    def current_wifi_ip(self):
        return self._fan.curent_wifi_ip

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
        }

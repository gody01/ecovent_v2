"""Demo platform that offers a fake Number entity."""

from __future__ import annotations

from ecoventv2 import Fan

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigType, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Vento number platform."""
    async_add_entities(
        [
            VentoNumber(
                hass,
                config,
                "_humidity_threshold",
                "humidity_treshold",
                None,
                "mdi:water-percent",
                False,
                mode=NumberMode.AUTO,
                entity_category=EntityCategory.CONFIG,
                native_min_value=40.0,
                native_max_value=80.0,
                native_step=1,
            ),
            VentoNumber(
                hass,
                config,
                "_analogV_treshold",
                "analogV_treshold",
                None,
                "mdi:flash-triangle-outline",
                False,
                mode=NumberMode.AUTO,
                entity_category=EntityCategory.CONFIG,
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1,
            ),
            VentoNumber(
                hass,
                config,
                "_boost_time",
                "boost_time",
                None,
                "mdi:fan-clock",
                False,
                mode=NumberMode.AUTO,
                entity_category=EntityCategory.CONFIG,
                native_min_value=0,
                native_max_value=60,
                native_step=1,
            ),
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
        config: ConfigType,
        name: str,
        method: str,
        state: float,
        icon: str,
        assumed_state: bool,
        *,
        device_class: NumberDeviceClass | None = None,
        mode: NumberMode = NumberMode.AUTO,
        entity_category: EntityCategory = EntityCategory.CONFIG,
        native_min_value: float | None = None,
        native_max_value: float | None = None,
        native_step: float | None = None,
        unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize the Vento Number entity."""

        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)

        self._fan: Fan = coordinator._fan
        self._attr_assumed_state = assumed_state
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_mode = mode
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_unique_id = self._fan.id + name
        self._attr_native_value = getattr(self._fan, method)
        self._attr_name = name

        # self._method = getattr(self, method)
        self._func = method

        if native_min_value is not None:
            self._attr_native_min_value = native_min_value
        if native_max_value is not None:
            self._attr_native_max_value = native_max_value
        if native_step is not None:
            self._attr_native_step = native_step

        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._fan.id)
            },
            name=self._fan.name + self._attr_name,
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        intval = int(value)
        self._fan.set_param(self._func, hex(intval).replace("0x", "").zfill(2))
        self.async_write_ha_state()
        await self.coordinator.async_refresh()

    @property
    def device_info(self):
        """Get device info."""
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
        }

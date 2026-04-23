"""Time entities for EcoVent schedule editing."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator
from .ecoventv2 import Fan


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up schedule end-time entities for supported devices."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    if not coordinator._fan.supports_parameter("weekly_schedule_setup"):
        return

    async_add_entities(
        [
            WeeklyScheduleEndTimeEntity(hass, config, period)
            for period in range(1, 4)
        ]
    )


class WeeklyScheduleEndTimeEntity(CoordinatorEntity, TimeEntity):
    """Edit the end time of one weekly schedule period."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, period: int
    ) -> None:
        """Initialize one schedule end-time editor."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._period = period
        self._attr_name = f"Schedule period {period} end"
        self._attr_unique_id = self._fan.id + f"_schedule_period_{period}_end"
        self._attr_icon = "mdi:clock-end"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def native_value(self) -> time | None:
        """Return the end time for the selected schedule day/period."""
        return self.coordinator.schedule_period_end_time(self._period)

    async def async_set_value(self, value: time) -> None:
        """Write a new period end time."""
        await self.coordinator.async_set_schedule_period_end(self._period, value)

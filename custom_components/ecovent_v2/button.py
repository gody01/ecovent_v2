"""Button entities for EcoVent actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up EcoVent action buttons."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    entities = []
    if coordinator._fan.supports_parameter("rtc_time") and coordinator._fan.supports_parameter(
        "rtc_date"
    ):
        entities.append(SyncDeviceClockButton(hass, config))

    if entities:
        async_add_entities(entities)


class SyncDeviceClockButton(CoordinatorEntity, ButtonEntity):
    """Synchronize the device RTC with Home Assistant local time."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the sync-clock button."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_name = "Sync device clock"
        self._attr_unique_id = self._fan.id + "_sync_device_clock"
        self._attr_icon = "mdi:clock-check-outline"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    async def async_press(self) -> None:
        """Sync the device RTC immediately."""
        await self.coordinator.async_sync_device_clock()

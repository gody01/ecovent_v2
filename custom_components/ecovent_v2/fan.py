import time
from homeassistant.components.fan import (
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    SUPPORT_PRESET_MODE,
    SUPPORT_SET_SPEED,
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)


from .const import DOMAIN

# _LOGGER = logging.getLogger(__name__)

DEFAULT_ON_PERCENTAGE = 5
SPEED_RANGE = (1, 3)  # off is not included

FULL_SUPPORT = (
    SUPPORT_SET_SPEED | SUPPORT_OSCILLATE | SUPPORT_DIRECTION | SUPPORT_PRESET_MODE
)

PRESET_MODES = ["low", "medium", "high", "manual"]
DIRECTIONS = ["ventilation", "air_supply", "heat_recovery"]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Set up the Ecovent fan platform."""
    async_add_entities([VentoExpertFan(hass, config)])


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Fan config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities, None)


class VentoExpertFan(CoordinatorEntity, FanEntity):
    def __init__(self, hass, config) -> None:
        """Initialize fan."""

        coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan = coordinator._fan
        self._percentage = self._fan.man_speed
        self._attr_unique_id: self._fan.id
        self._attr_name = self._fan.name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": self._fan.unit_type,
            "sw_version": self._fan.firmware,
            "manufacturer": "Blauberg",
        }

    @property
    def name(self) -> str:
        """Get entity name."""
        return self._fan.name

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._fan.id

    @property
    def state(self):
        """Return state."""
        return self._fan.state

    @property
    def percentage(self):
        """Return the current speed."""
        return self._percentage

    @property
    def preset_modes(self) -> list[str]:
        """Return a list of available preset modes."""
        return PRESET_MODES

    @property
    def directions(self) -> list[str]:
        """Return a list of available preset modes."""
        return DIRECTIONS

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        return self._fan.speed

    @property
    def current_direction(self) -> str:
        """Fan direction."""
        return self._fan.airflow

    @property
    def oscillating(self) -> bool:
        """Oscillating."""
        return self._fan.airflow == "heat_recovery"

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return FULL_SUPPORT

    # pylint: disable=arguments-differ
    async def async_turn_on(
        self,
        speed: str,
        percentage: int,
        preset_mode: str,
        **kwargs,
    ) -> None:
        """Turn on the entity."""
        self._fan.set_param("state", "on")
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self._fan.set_param("state", "off")
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_set_preset_mode(self, preset_mode: str):
        """Set the preset mode of the fan."""
        if preset_mode in self.preset_modes:
            self._fan.set_param("speed", preset_mode)
            if preset_mode == "manual":
                self._fan.set_man_speed_percent(self.percentage)
            await self.coordinator.async_refresh()
            self.schedule_update_ha_state()
        else:
            raise ValueError(f"Invalid preset mode: {preset_mode}")

    async def async_set_percentage(self, percentage: int):
        """Set the speed of the fan, as a percentage."""
        self._percentage = percentage
        if self._fan.speed == "manual":
            self._fan.set_man_speed_percent(percentage)
            await self.coordinator.async_refresh()
            self.schedule_update_ha_state()

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if direction == "forward" and self._fan.airflow != "ventilation":
            self._fan.set_param("airflow", "ventilation")
        if direction == "reverse" and self._fan.airflow != "air_supply":
            self._fan.set_param("airflow", "air_supply")
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        if oscillating:
            self._fan.set_param("airflow", "heat_recovery")
        else:
            self._fan.set_param("airflow", "ventilation")
        await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    # async def async_increase_speed(self, percentage_step: int):
    # pylint: disable=arguments-differ
    async def async_increase_speed(self, percentage_step: int) -> None:
        new_percentage = int(self.percentage) + percentage_step
        if new_percentage > 100:
            new_percentage = 100
        self._percentage = new_percentage
        if self._fan.set_speed == "manual":
            self._fan.set_man_speed_percent(new_percentage)
            self.schedule_update_ha_state()

    # async def async_decrease_speed(self, percentage_step: int):
    # pylint: disable=arguments-differ
    async def async_decrease_speed(self, percentage_step: int) -> None:
        new_percentage = int(self.percentage) - percentage_step
        if new_percentage < 5:
            new_percentage = 5
        self._percentage = new_percentage
        if self._fan.speed == "manual":
            self._fan.set_man_speed_percent(new_percentage)
            self.schedule_update_ha_state()

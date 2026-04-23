"""Select entities for writable EcoVent enum parameters."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoVentCoordinator
from .ecoventv2 import Fan
from .schedule_helpers import (
    SCHEDULE_DAY_OPTIONS,
    SCHEDULE_SPEED_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectSpec:
    """Writable enum description guarded by runtime capabilities."""

    key: str
    name: str
    method: str
    icon: str
    required_capabilities: tuple[str, ...]
    entity_category: EntityCategory = EntityCategory.CONFIG
    enable_by_default: bool = True
    translation_key: str | None = None


SELECT_SPECS = (
    SelectSpec(
        "_beeper",
        "Beeper",
        "beeper",
        "mdi:volume-high",
        ("beeper_control",),
        translation_key="beeper",
    ),
    SelectSpec(
        "_screen_backlight_mode",
        "Screen backlight mode",
        "screen_backlight_mode",
        "mdi:brightness-auto",
        ("breezy_screen",),
        enable_by_default=False,
    ),
    SelectSpec(
        "_screen_temperature_source",
        "Screen temperature source",
        "screen_temperature_source",
        "mdi:thermometer-lines",
        ("breezy_screen",),
        enable_by_default=False,
    ),
    SelectSpec(
        "_screen_air_quality_source",
        "Screen air quality source",
        "screen_air_quality_source",
        "mdi:air-filter",
        ("breezy_screen",),
        enable_by_default=False,
    ),
    SelectSpec(
        "_screen_display_mode",
        "Screen display mode",
        "screen_display_mode",
        "mdi:monitor-dashboard",
        ("breezy_screen",),
        enable_by_default=False,
    ),
    SelectSpec(
        "_screen_display_state",
        "Screen display state",
        "screen_display_state",
        "mdi:monitor-shimmer",
        ("breezy_screen",),
        enable_by_default=False,
    ),
    SelectSpec(
        "_humidity_sensor_state",
        "Humidity sensor mode",
        "humidity_sensor_state",
        "mdi:water-percent-alert",
        ("arc_environment",),
    ),
    SelectSpec(
        "_air_quality_sensor_state",
        "Air quality sensor mode",
        "air_quality_sensor_state",
        "mdi:air-filter",
        ("arc_environment",),
    ),
    SelectSpec(
        "_humidity_airflow",
        "Humidity airflow",
        "humidity_airflow",
        "mdi:water-percent",
        ("arc_environment",),
    ),
    SelectSpec(
        "_motion_light_airflow",
        "Motion/light airflow",
        "motion_light_airflow",
        "mdi:motion-sensor",
        ("arc_environment",),
    ),
    SelectSpec(
        "_air_quality_airflow",
        "Air quality airflow",
        "air_quality_airflow",
        "mdi:air-filter",
        ("arc_environment",),
    ),
    SelectSpec(
        "_interval_ventilation_airflow",
        "Interval ventilation airflow",
        "interval_ventilation_airflow",
        "mdi:fan-auto",
        ("arc_environment",),
    ),
    SelectSpec(
        "_all_day_airflow",
        "All day airflow",
        "all_day_airflow",
        "mdi:hours-24",
        ("arc_environment",),
    ),
    SelectSpec(
        "_temperature_airflow",
        "Temperature airflow",
        "temperature_airflow",
        "mdi:thermometer",
        ("arc_environment",),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable enum select entities."""
    coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
    entities = [
        VentoSelect(hass, config, spec)
        for spec in SELECT_SPECS
        if coordinator._fan.supports_entity(
            required_params=(spec.method,),
            required_capabilities=spec.required_capabilities,
        )
    ]

    if coordinator._fan.supports_parameter("weekly_schedule_setup"):
        entities.append(WeeklyScheduleDaySelect(hass, config))
        entities.extend(
            WeeklyScheduleSpeedSelect(hass, config, period)
            for period in range(1, 5)
        )

    async_add_entities(entities)


class VentoSelect(CoordinatorEntity, SelectEntity):
    """Writable EcoVent enum select entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        spec: SelectSpec,
    ) -> None:
        """Initialize a writable enum select."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._method = spec.method
        self._attr_name = spec.name
        self._attr_unique_id = self._fan.id + spec.key
        self._attr_icon = spec.icon
        self._attr_entity_category = spec.entity_category
        self._attr_entity_registry_enabled_default = spec.enable_by_default
        self._attr_translation_key = spec.translation_key
        self._attr_options = self._fan.parameter_options(spec.method) or []
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def current_option(self) -> str | None:
        """Return the current enum option."""
        return getattr(self._fan, self._method)

    async def async_select_option(self, option: str) -> None:
        """Select a new enum option."""
        if option not in self.options:
            raise ValueError(f"Invalid {self._method} option: {option}")

        await self.hass.async_add_executor_job(self._fan.set_param, self._method, option)
        await self.coordinator.async_refresh()


class WeeklyScheduleDaySelect(CoordinatorEntity, SelectEntity):
    """Choose which weekday is shown in the schedule editor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the schedule day select."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_name = "Schedule day"
        self._attr_unique_id = self._fan.id + "_schedule_day"
        self._attr_icon = "mdi:calendar-week"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(SCHEDULE_DAY_OPTIONS)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def current_option(self) -> str | None:
        """Return the selected day."""
        return self.coordinator.schedule_day_option

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Show a compact summary of the selected day's periods."""
        return self.coordinator.schedule_summaries()

    async def async_select_option(self, option: str) -> None:
        """Switch the schedule editor to another day."""
        if option not in self.options:
            raise ValueError(f"Invalid schedule day: {option}")
        await self.coordinator.async_select_schedule_day(option)


class WeeklyScheduleSpeedSelect(CoordinatorEntity, SelectEntity):
    """Edit one schedule period speed."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, period: int
    ) -> None:
        """Initialize one schedule speed selector."""
        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._period = period
        self._attr_name = f"Schedule period {period} speed"
        self._attr_unique_id = self._fan.id + f"_schedule_period_{period}_speed"
        self._attr_icon = f"mdi:numeric-{period}-circle-outline"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(SCHEDULE_SPEED_OPTIONS)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def current_option(self) -> str | None:
        """Return the current speed option for the selected day/period."""
        return self.coordinator.schedule_period_speed_option(self._period)

    async def async_select_option(self, option: str) -> None:
        """Write a new speed for the selected day/period."""
        if option not in self.options:
            raise ValueError(f"Invalid schedule speed: {option}")
        await self.coordinator.async_set_schedule_period_speed(self._period, option)

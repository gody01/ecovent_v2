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

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectSpec:
    """Writable enum description guarded by documented profile support."""

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
        (),
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
        "Boost mode on humidity",
        "humidity_sensor_state",
        "mdi:water-percent-alert",
        ("arc_environment",),
    ),
    SelectSpec(
        "_air_quality_sensor_state",
        "Trigger mode on air quality",
        "air_quality_sensor_state",
        "mdi:air-filter",
        ("arc_environment",),
    ),
    SelectSpec(
        "_humidity_airflow",
        "Boost airflow on humidity",
        "humidity_airflow",
        "mdi:water-percent",
        ("arc_environment",),
    ),
    SelectSpec(
        "_motion_light_airflow",
        "Airflow on motion/light",
        "motion_light_airflow",
        "mdi:motion-sensor",
        ("arc_environment",),
    ),
    SelectSpec(
        "_air_quality_airflow",
        "Airflow on air quality",
        "air_quality_airflow",
        "mdi:air-filter",
        ("arc_environment",),
    ),
    SelectSpec(
        "_interval_ventilation_airflow",
        "Airflow for interval ventilation",
        "interval_ventilation_airflow",
        "mdi:fan-auto",
        ("arc_environment",),
    ),
    SelectSpec(
        "_all_day_airflow",
        "Airflow for all day",
        "all_day_airflow",
        "mdi:hours-24",
        ("arc_environment",),
    ),
    SelectSpec(
        "_temperature_airflow",
        "Airflow on temperature",
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

        await self.hass.async_add_executor_job(
            self._fan.set_param, self._method, option
        )
        await self.coordinator.async_refresh()

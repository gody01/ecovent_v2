"""The EcoVent_v2 integration."""

# from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STARTED,
    PERCENTAGE,
    Platform,
    REVOLUTIONS_PER_MINUTE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import EcoVentCoordinator
from .frontend import async_register_frontend

_LOGGER = logging.getLogger(__name__)

_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.TIME,
    Platform.FAN,
]

_STATISTICS_UNIT_MIGRATIONS = {
    "fan_1_speed": REVOLUTIONS_PER_MINUTE,
    "fan_2_speed": REVOLUTIONS_PER_MINUTE,
    "timer_counter": "h",
    "battery": PERCENTAGE,
    "filter_change_in": "h",
    "machine_hours": "h",
}


def _async_migrate_entity_registry(
    hass: HomeAssistant, coordinator: EcoVentCoordinator
) -> None:
    """Move legacy entities to clearer domains and ids."""
    registry = er.async_get(hass)
    fan = coordinator._fan
    device_slug = slugify(fan.name)

    stale_binary_unique_ids = (
        fan.id + "_boost_status",
        fan.id + "_timer_mode",
    )
    for unique_id in stale_binary_unique_ids:
        entity_id = registry.async_get_entity_id(
            Platform.BINARY_SENSOR, DOMAIN, unique_id
        )
        if entity_id is not None:
            registry.async_remove(entity_id)
            _LOGGER.info("Removed legacy EcoVent V2 binary sensor %s", entity_id)

    if not fan.supports_parameter("beeper"):
        for platform in (Platform.SENSOR, Platform.SELECT):
            beeper_entity_id = registry.async_get_entity_id(
                platform, DOMAIN, fan.id + "_beeper"
            )
            if beeper_entity_id is None:
                continue

            registry.async_remove(beeper_entity_id)
            _LOGGER.info(
                "Removed stale EcoVent V2 beeper entity %s", beeper_entity_id
            )

    entity_id_migrations = {
        (Platform.SENSOR, fan.id + "_speed1"): f"sensor.{device_slug}_fan_1_speed",
        (Platform.SENSOR, fan.id + "_speed2"): f"sensor.{device_slug}_fan_2_speed",
        (
            Platform.SENSOR,
            fan.id + "_filter_change_in",
        ): f"sensor.{device_slug}_filter_change_in",
        (
            Platform.SWITCH,
            fan.id + "_humidity_sensor_state",
        ): f"switch.{device_slug}_humidity_sensor",
        (
            Platform.SWITCH,
            fan.id + "_relay_sensor_state",
        ): f"switch.{device_slug}_relay_sensor",
        (
            Platform.SWITCH,
            fan.id + "_analogV_sensor_state",
        ): f"switch.{device_slug}_analog_voltage_sensor",
        (
            Platform.NUMBER,
            fan.id + "humidity_treshold",
        ): f"number.{device_slug}_humidity_threshold",
        (
            Platform.NUMBER,
            fan.id + "analogV_treshold",
        ): f"number.{device_slug}_analog_voltage_threshold",
    }
    for (domain, unique_id), new_entity_id in entity_id_migrations.items():
        entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
        if entity_id is None or entity_id == new_entity_id:
            continue

        existing = registry.async_get(new_entity_id)
        if existing is not None and existing.unique_id != unique_id:
            _LOGGER.debug(
                "Skipping EcoVent V2 entity id migration for %s: %s already exists",
                entity_id,
                new_entity_id,
            )
            continue

        registry.async_update_entity(entity_id, new_entity_id=new_entity_id)
        _LOGGER.info("Migrated EcoVent V2 entity id %s to %s", entity_id, new_entity_id)

    if fan.supports_parameter("weekly_schedule_setup"):
        schedule_switch_entity_id = registry.async_get_entity_id(
            Platform.SWITCH,
            DOMAIN,
            fan.id + "_weekly_schedule_state",
        )
        if schedule_switch_entity_id is not None:
            schedule_switch_entry = registry.async_get(schedule_switch_entity_id)
            if schedule_switch_entry.hidden_by is not None:
                registry.async_update_entity(
                    schedule_switch_entity_id,
                    hidden_by=None,
                )
                _LOGGER.info(
                    "Restored visible EcoVent V2 weekly schedule switch %s",
                    schedule_switch_entity_id,
                )

        schedule_helper_entity_ids = (
            f"select.{device_slug}_schedule_day",
            *[
                f"select.{device_slug}_schedule_period_{period}_speed"
                for period in range(1, 5)
            ],
            *[
                f"time.{device_slug}_schedule_period_{period}_end"
                for period in range(1, 4)
            ],
        )
        for entity_id in schedule_helper_entity_ids:
            if registry.async_get(entity_id) is None:
                continue
            registry.async_remove(entity_id)
            _LOGGER.info("Removed EcoVent V2 legacy schedule helper entity %s", entity_id)


async def _async_migrate_statistics_metadata(
    hass: HomeAssistant, coordinator: EcoVentCoordinator
) -> None:
    """Update historic statistics units after adding explicit sensor units."""
    try:
        from homeassistant.components.recorder.statistics import (
            async_list_statistic_ids,
            async_update_statistics_metadata,
        )
    except ImportError:
        _LOGGER.debug("Recorder statistics unavailable; skipping EcoVent V2 migration")
        return

    fan = coordinator._fan
    device_slug = slugify(fan.name)
    statistic_units = {
        f"sensor.{device_slug}_{suffix}": unit
        for suffix, unit in _STATISTICS_UNIT_MIGRATIONS.items()
    }

    try:
        statistics = await async_list_statistic_ids(hass, set(statistic_units))
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Unable to inspect EcoVent V2 statistics metadata: %s", err)
        return

    for statistic in statistics:
        statistic_id = statistic.get("statistic_id")
        new_unit = statistic_units.get(statistic_id)
        if new_unit is None:
            continue

        old_unit = statistic.get("unit_of_measurement")
        if old_unit == new_unit:
            continue

        async_update_statistics_metadata(
            hass,
            statistic_id,
            new_unit_class=None,
            new_unit_of_measurement=new_unit,
        )
        _LOGGER.info(
            "Migrated EcoVent V2 statistics unit for %s from %s to %s",
            statistic_id,
            old_unit,
            new_unit,
        )


async def _async_migrate_statistics_metadata_on_start(
    hass: HomeAssistant, coordinator: EcoVentCoordinator
) -> None:
    """Run statistics migration now and again after recorder startup."""
    await _async_migrate_statistics_metadata(hass, coordinator)

    async def _async_run_at_start(_event) -> None:
        await _async_migrate_statistics_metadata(hass, coordinator)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_run_at_start)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoVent_v2 from a config entry."""

    entry.runtime_data = {
        CONF_IP_ADDRESS: entry.data.get(CONF_IP_ADDRESS, "<broadcast>"),
        CONF_PORT: entry.data.get(CONF_PORT, 4000),
        # CONF_DEVICE_ID: entry.data.get(CONF_DEVICE_ID, "DEFAULT_DEVICEID"),
        CONF_PASSWORD: entry.data.get(CONF_PASSWORD, "1111"),
        CONF_NAME: entry.data.get(CONF_NAME, "Vento Expert Fan"),
        UPDATE_INTERVAL: entry.data.get(UPDATE_INTERVAL, 30),
    }

    coordinator = EcoVentCoordinator(
        hass, entry, update_seconds=entry.runtime_data[UPDATE_INTERVAL]
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await async_register_frontend(hass)
    _async_migrate_entity_registry(hass, coordinator)
    await _async_migrate_statistics_metadata_on_start(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    return unload_ok

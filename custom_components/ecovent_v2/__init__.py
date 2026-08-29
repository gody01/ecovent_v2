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

from .const import (
    CONF_AUTO_CLOCK_SYNC,
    CONF_TRANSPORT,
    DOMAIN,
    TRANSPORT_BGCP_UDP,
    UPDATE_INTERVAL,
)
from .coordinator import (
    EcoVentCoordinator,
    async_delete_hardware_profile_mismatch_issue,
)
from .entity_naming import stable_entity_id
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


def _entity_id_has_legacy_device_id(entity_id: str, fan_id: str | None) -> bool:
    """Return whether an entity id still carries the old device-id suffix.

    Legacy EcoVent entity ids were generated from device names like
    ``Ventilator 5``. Only rewrite those one-shot legacy ids; if a user has
    already renamed an entity id manually, do not keep forcing our preferred id
    on every integration reload.
    """
    if fan_id is None:
        return False

    legacy_slug = slugify(fan_id)
    if not legacy_slug:
        return False

    object_id = entity_id.split(".", 1)[-1]
    object_tokens = object_id.split("_")
    legacy_tokens = legacy_slug.split("_")
    token_count = len(legacy_tokens)
    return any(
        object_tokens[index : index + token_count] == legacy_tokens
        for index in range(0, len(object_tokens) - token_count + 1)
    )


def _entity_id_matches_generated_suffix(
    entity_id: str,
    fan_name: str,
    fan_id: str | None,
    suffixes: tuple[str, ...],
) -> bool:
    """Return whether an entity id matches a known integration-generated name.

    EcoVent ids went through several naming schemes before the stable suffixes:
    raw keys, friendly-label slugs, typo-preserving parameter names, and old
    ``*_set`` number names. Migrate those known generated variants, but still
    leave unrelated user-customized ids alone.
    """
    object_id = entity_id.split(".", 1)[-1]
    device_slug = slugify(fan_name)
    legacy_device_match = _entity_id_has_legacy_device_id(entity_id, fan_id)

    for suffix in {slugify(suffix) for suffix in suffixes}:
        if object_id == suffix:
            return True

        if not object_id.endswith(f"_{suffix}"):
            continue

        prefix = object_id[: -(len(suffix) + 1)]
        if prefix == device_slug or legacy_device_match:
            return True

    return False


def _known_generated_unique_ids(
    fan_name: str,
    fan_id: str | None,
    suffixes: tuple[str, ...],
) -> tuple[str, ...]:
    """Return known unique ids emitted by older EcoVent naming schemes."""
    prefixes = (fan_name,)
    if fan_id:
        prefixes = (fan_name, f"{fan_name} {fan_id}", fan_id)

    unique_ids: list[str] = []
    for suffix in suffixes:
        suffix_variants = (suffix, f"_{suffix}")
        for suffix_variant in suffix_variants:
            unique_ids.append(suffix_variant)
            for prefix in prefixes:
                unique_ids.append(f"{prefix}{suffix_variant}")

    return tuple(dict.fromkeys(unique_ids))


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

    stale_sensor_unique_ids = (
        fan.id + "_rtc_date",
        fan.id + "_rtc_time",
    )
    for unique_id in stale_sensor_unique_ids:
        entity_id = registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id)
        if entity_id is not None:
            registry.async_remove(entity_id)
            _LOGGER.info("Removed legacy EcoVent V2 sensor %s", entity_id)

    if not fan.supports_parameter("beeper"):
        for platform in (Platform.SENSOR, Platform.SELECT):
            beeper_entity_id = registry.async_get_entity_id(
                platform, DOMAIN, fan.id + "_beeper"
            )
            if beeper_entity_id is None:
                continue

            registry.async_remove(beeper_entity_id)
            _LOGGER.info("Removed stale EcoVent V2 beeper entity %s", beeper_entity_id)

    entity_id_migrations = {
        (Platform.SENSOR, fan.id + "_speed1"): (
            stable_entity_id(Platform.SENSOR, fan.name, "fan1_speed"),
            ("fan1_speed", "fan_1_speed", "speed1", "fan_speed"),
        ),
        (Platform.SENSOR, fan.id + "_speed2"): (
            stable_entity_id(Platform.SENSOR, fan.name, "fan2_speed"),
            ("fan2_speed", "fan_2_speed", "speed2"),
        ),
        (
            Platform.SENSOR,
            fan.id + "_filter_change_in",
        ): (
            stable_entity_id(Platform.SENSOR, fan.name, "filter_change_in"),
            ("filter_change_in", "filter_remaining", "filter_timer_countdown"),
        ),
        (
            Platform.SENSOR,
            fan.id + "_analogv",
        ): (
            stable_entity_id(Platform.SENSOR, fan.name, "analogv"),
            ("analogv", "analogV", "analog_v", "analog_voltage"),
        ),
        (
            Platform.BINARY_SENSOR,
            fan.id + "_analogV_status",
        ): (
            stable_entity_id(Platform.BINARY_SENSOR, fan.name, "analogV_status"),
            (
                "analogV_status",
                "analogv_status",
                "analog_v_status",
                "analog_voltage_status",
            ),
        ),
        (
            Platform.SWITCH,
            fan.id + "_humidity_sensor_state",
        ): (
            stable_entity_id(Platform.SWITCH, fan.name, "humidity_sensor_state"),
            ("humidity_sensor_state", "humidity_sensor"),
        ),
        (
            Platform.SWITCH,
            fan.id + "_relay_sensor_state",
        ): (
            stable_entity_id(Platform.SWITCH, fan.name, "relay_sensor_state"),
            ("relay_sensor_state", "relay_sensor"),
        ),
        (
            Platform.SWITCH,
            fan.id + "_analogV_sensor_state",
        ): (
            stable_entity_id(Platform.SWITCH, fan.name, "analogV_sensor_state"),
            (
                "analogV_sensor_state",
                "analogv_sensor_state",
                "analog_voltage_sensor_state",
                "analogV_sensor",
                "analogv_sensor",
                "analog_voltage_sensor",
            ),
        ),
        (
            Platform.NUMBER,
            fan.id + "humidity_treshold",
        ): (
            stable_entity_id(Platform.NUMBER, fan.name, "humidity_treshold"),
            (
                "humidity_treshold",
                "humidity_threshold",
                "humidity_threshold_set",
            ),
        ),
        (
            Platform.NUMBER,
            fan.id + "analogV_treshold",
        ): (
            stable_entity_id(Platform.NUMBER, fan.name, "analogV_treshold"),
            (
                "analogV_treshold",
                "analogv_treshold",
                "analogV_treshold_set",
                "analogv_treshold_set",
                "analog_v_treshold",
                "analog_v_treshold_set",
                "analog_voltage_treshold",
                "analogV_threshold",
                "analogv_threshold",
                "analogV_threshold_set",
                "analogv_threshold_set",
                "analog_v_threshold",
                "analog_v_threshold_set",
                "analog_voltage_threshold",
            ),
        ),
    }
    for (domain, target_unique_id), (
        new_entity_id,
        generated_suffixes,
    ) in entity_id_migrations.items():
        unique_ids = (
            target_unique_id,
            *_known_generated_unique_ids(fan.name, fan.id, generated_suffixes),
        )
        seen_entity_ids: set[str] = set()

        for unique_id in unique_ids:
            entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
            if entity_id is None or entity_id in seen_entity_ids:
                continue
            seen_entity_ids.add(entity_id)

            has_generated_entity_id = _entity_id_matches_generated_suffix(
                entity_id,
                fan.name,
                fan.id,
                generated_suffixes,
            )
            has_legacy_unique_id = unique_id != target_unique_id
            if not has_generated_entity_id and not has_legacy_unique_id:
                _LOGGER.debug(
                    "Skipping EcoVent V2 entity id migration for %s: user-customized "
                    "entity ids are preserved",
                    entity_id,
                )
                continue

            update_kwargs: dict[str, str] = {}
            if has_generated_entity_id and entity_id != new_entity_id:
                existing = registry.async_get(new_entity_id)
                if existing is not None and existing.entity_id != entity_id:
                    _LOGGER.debug(
                        "Skipping EcoVent V2 entity id migration for %s: %s already "
                        "exists",
                        entity_id,
                        new_entity_id,
                    )
                else:
                    update_kwargs["new_entity_id"] = new_entity_id

            if has_legacy_unique_id:
                conflict_entity_id = registry.async_get_entity_id(
                    domain,
                    DOMAIN,
                    target_unique_id,
                )
                if conflict_entity_id is not None and conflict_entity_id != entity_id:
                    _LOGGER.debug(
                        "Skipping EcoVent V2 unique id migration for %s: %s is "
                        "already used by %s",
                        entity_id,
                        target_unique_id,
                        conflict_entity_id,
                    )
                else:
                    update_kwargs["new_unique_id"] = target_unique_id

            if not update_kwargs:
                continue

            registry.async_update_entity(entity_id, **update_kwargs)
            _LOGGER.info(
                "Migrated EcoVent V2 registry entry %s with %s",
                entity_id,
                update_kwargs,
            )

    if fan.supports_parameter("weekly_schedule_setup"):
        schedule_switch_entity_id = registry.async_get_entity_id(
            Platform.SWITCH,
            DOMAIN,
            fan.id + "_weekly_schedule_state",
        )
        if schedule_switch_entity_id is not None:
            schedule_switch_entry = registry.async_get(schedule_switch_entity_id)
            if (
                schedule_switch_entry is not None
                and schedule_switch_entry.hidden_by
                == er.RegistryEntryHider.INTEGRATION
            ):
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
            _LOGGER.info(
                "Removed EcoVent V2 legacy schedule helper entity %s", entity_id
            )

    _async_update_unsupported_optional_poll_entities(registry, fan)


def _async_update_unsupported_optional_poll_entities(registry, fan) -> None:
    """Hide or restore generated entities for rows this hardware rejects."""
    from .binary_sensor import BINARY_SENSOR_SPECS
    from .number import NUMBER_SPECS
    from .select import SELECT_SPECS
    from .sensor_specs import SENSOR_SPECS
    from .switch import SWITCH_SPECS

    entity_specs = (
        *(
            (
                Platform.SENSOR,
                fan.id + spec.key,
                spec.method,
                fan.supports_entity(
                    required_params=spec.required_params or (spec.method,),
                    required_capabilities=spec.required_capabilities,
                    excluded_params=spec.excluded_params,
                    excluded_capabilities=spec.excluded_capabilities,
                ),
            )
            for spec in SENSOR_SPECS
        ),
        *(
            (
                Platform.BINARY_SENSOR,
                fan.id + spec.key,
                spec.method,
                fan.supports_entity(
                    required_params=(spec.method,),
                    required_capabilities=spec.required_capabilities,
                ),
            )
            for spec in BINARY_SENSOR_SPECS
        ),
        *(
            (
                Platform.SWITCH,
                fan.id + spec.key,
                spec.method,
                fan.supports_entity(
                    required_params=(spec.method,),
                    required_capabilities=spec.required_capabilities,
                ),
            )
            for spec in SWITCH_SPECS
        ),
        *(
            (
                Platform.NUMBER,
                fan.id + spec.method,
                spec.method,
                fan.supports_entity(
                    required_params=(spec.method,),
                    required_capabilities=spec.required_capabilities,
                ),
            )
            for spec in NUMBER_SPECS
        ),
        *(
            (
                Platform.SELECT,
                fan.id + spec.key,
                spec.method,
                fan.supports_entity(
                    required_params=(spec.method,),
                    required_capabilities=spec.required_capabilities,
                ),
            )
            for spec in SELECT_SPECS
        ),
        (
            Platform.SENSOR,
            fan.id + "_schedule",
            "weekly_schedule_setup",
            fan.supports_parameter("weekly_schedule_setup"),
        ),
    )
    for platform, unique_id, method, supported in entity_specs:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id is None:
            continue

        entry = registry.async_get(entity_id)
        if entry is None:
            continue

        if not supported:
            if entry.hidden_by is None:
                registry.async_update_entity(
                    entity_id,
                    hidden_by=er.RegistryEntryHider.INTEGRATION,
                )
                _LOGGER.info(
                    "Hidden EcoVent V2 entity %s because this hardware rejected %s",
                    entity_id,
                    method,
                )
            continue

        if entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
            registry.async_update_entity(entity_id, hidden_by=None)
            _LOGGER.info(
                "Restored EcoVent V2 entity %s because %s is supported again",
                entity_id,
                method,
            )


def _async_register_optional_poll_entity_sync(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EcoVentCoordinator,
) -> None:
    """Keep generated entity visibility aligned with learned capabilities."""
    registry = er.async_get(hass)
    loaded_identity = (
        coordinator._fan.profile_key,
        getattr(coordinator._fan, "_unit_type_id", None),
        coordinator._fan.firmware,
    )
    last_capability_state = None
    reload_requested = False

    def _async_sync_entity_registry() -> None:
        nonlocal last_capability_state, reload_requested
        if not coordinator.last_update_success:
            return

        current_identity = (
            coordinator._fan.profile_key,
            getattr(coordinator._fan, "_unit_type_id", None),
            coordinator._fan.firmware,
        )
        if current_identity != loaded_identity:
            if not reload_requested:
                _LOGGER.info(
                    "Reloading EcoVent V2 config entry %s after device identity "
                    "changed from %s to %s",
                    entry.entry_id,
                    loaded_identity,
                    current_identity,
                )
                hass.config_entries.async_schedule_reload(entry.entry_id)
                reload_requested = True
            return

        capability_state = (
            *current_identity,
            coordinator._fan.unsupported_optional_poll_parameter_ids(),
        )
        if capability_state == last_capability_state:
            return

        _async_update_unsupported_optional_poll_entities(registry, coordinator._fan)
        last_capability_state = capability_state

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entity_registry))
    _async_sync_entity_registry()


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
    hass: HomeAssistant, entry: ConfigEntry, coordinator: EcoVentCoordinator
) -> None:
    """Run statistics migration now and again after recorder startup."""
    await _async_migrate_statistics_metadata(hass, coordinator)

    async def _async_run_at_start(_event) -> None:
        await _async_migrate_statistics_metadata(hass, coordinator)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_run_at_start)
    )


async def _async_close_coordinator(
    hass: HomeAssistant, coordinator: EcoVentCoordinator | None
) -> None:
    """Close a coordinator transport without blocking setup or unload cleanup."""
    close = getattr(getattr(coordinator, "_fan", None), "close", None)
    if close is None:
        return

    try:
        await hass.async_add_executor_job(close)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Unable to close EcoVent V2 transport during cleanup: %s",
            err,
            exc_info=True,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoVent_v2 from a config entry."""

    entry.runtime_data = dict(entry.data)
    entry.runtime_data.update(
        {
            CONF_IP_ADDRESS: entry.data.get(CONF_IP_ADDRESS, "<broadcast>"),
            CONF_PORT: entry.data.get(CONF_PORT, 4000),
            # CONF_DEVICE_ID: entry.data.get(CONF_DEVICE_ID, "DEFAULT_DEVICEID"),
            CONF_PASSWORD: entry.data.get(CONF_PASSWORD, "1111"),
            CONF_NAME: entry.data.get(CONF_NAME, "Vento Expert Fan"),
            UPDATE_INTERVAL: entry.data.get(UPDATE_INTERVAL, 30),
            CONF_AUTO_CLOCK_SYNC: entry.data.get(CONF_AUTO_CLOCK_SYNC, True),
            CONF_TRANSPORT: entry.data.get(CONF_TRANSPORT, TRANSPORT_BGCP_UDP),
        }
    )

    coordinator = EcoVentCoordinator(
        hass, entry, update_seconds=entry.runtime_data[UPDATE_INTERVAL]
    )

    try:
        await coordinator.async_config_entry_first_refresh()

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator
        await async_register_frontend(hass)
        _async_migrate_entity_registry(hass, coordinator)
        await _async_migrate_statistics_metadata_on_start(hass, entry, coordinator)
        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
        _async_register_optional_poll_entity_sync(hass, entry, coordinator)
        return True
    except Exception:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        await _async_close_coordinator(hass, coordinator)
        raise


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    if unload_ok:
        try:
            async_delete_hardware_profile_mismatch_issue(hass, entry.entry_id)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Unable to remove EcoVent V2 hardware profile Repair for %s: %s",
                entry.entry_id,
                err,
                exc_info=True,
            )
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        await _async_close_coordinator(hass, coordinator)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Mark pre-Modbus entries as the legacy BGCP/UDP transport."""
    if entry.version >= 2:
        return True

    data = dict(entry.data)
    data.setdefault(CONF_TRANSPORT, TRANSPORT_BGCP_UDP)
    hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True

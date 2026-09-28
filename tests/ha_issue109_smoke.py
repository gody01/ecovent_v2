"""End-to-end regression coverage for the RECOM 4 SR report in issue #109."""

import asyncio
import importlib
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.entity_component import EntityComponent

from ha_issues101_102_smoke import ScheduleWire


ROOT = Path(os.environ.get("ECOVENT_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
RECOM_TEMPERATURE_PARAMS = (0x001F, 0x0020, 0x0021, 0x0022)
REJECTED_PARAMS = frozenset({0x00B7, 0x00B8, 0x0302, 0x0303, 0x0304, 0x0305, 0x0306})
TEMPERATURE_METHODS = (
    "outdoor_temperature",
    "supply_temperature",
    "exhaust_in_temperature",
    "exhaust_out_temperature",
    "temperature_setpoint",
)
ISSUE_109_DUMP_VALUES = {
    0x0010: b"\x00\x80",
    0x0018: b"\x13",
    0x001E: b"\xe4\x00",
    0x001F: b"\xa9\x00",
    0x0020: b"\xe4\x00",
    0x0021: b"\xe9\x00",
    0x0022: b"\xc0\x00",
    0x0023: b"\x00\x80",
    0x0024: b"\xa4\x0c",
    0x004A: b"\x24\x09",
    0x004B: b"\x60\x09",
    0x0063: b"\xb3",
    0x0086: b"\x00\x2b\x1c\x06\xe8\x07",
    0x00B9: b"\x01\x00",
}
ISSUE_109_EXPECTED_STATES = {
    "outdoor_temperature": "16.9",
    "supply_temperature": "22.8",
    "exhaust_in_temperature": "23.3",
    "exhaust_out_temperature": "19.2",
    "temperature_setpoint": "19",
}


_package = types.ModuleType("issue109_ecovent")
_package.__path__ = [str(ROOT / "custom_components/ecovent_v2")]
sys.modules[_package.__name__] = _package
Coordinator = importlib.import_module(_package.__name__ + ".coordinator").EcoVentCoordinator
Sensors = importlib.import_module(_package.__name__ + ".sensor")
Diagnostics = importlib.import_module(_package.__name__ + ".protocol_diagnostics")
FanProtocol = importlib.import_module(_package.__name__ + ".fan_protocol")
Integration = importlib.import_module(_package.__name__ + ".__init__")


async def _setup_sensor_platform(hass, entry):
    batches = []

    def add_entities(entities):
        batches.append(list(entities))

    platform = types.SimpleNamespace(
        async_register_entity_service=lambda *_args: None
    )
    with patch.object(
        Sensors.entity_platform, "async_get_current_platform", return_value=platform
    ):
        await Sensors.async_setup_entry(hass, entry, add_entities)
    return batches


def _sensor_methods(batches):
    return [
        entity._method.__name__
        for batch in batches
        for entity in batch
        if hasattr(entity, "_method")
    ]


def _unload_entity_listeners(unload_callbacks, coordinator):
    shutdown = coordinator.async_shutdown
    for unload in reversed(unload_callbacks):
        if unload != shutdown:
            unload()
    unload_callbacks[:] = [
        unload for unload in unload_callbacks if unload == shutdown
    ]


async def _async_unload_entry_callbacks(unload_callbacks):
    for unload in reversed(unload_callbacks):
        result = unload()
        if result is not None:
            await result
    unload_callbacks.clear()


async def _run_issue_fixture(*, temperature_answers, late_temperature_answers=False):
    with tempfile.TemporaryDirectory(prefix="ecovent-ha-issue109-") as tmp:
        hass = HomeAssistant(tmp)
        unload_callbacks = []
        entry = types.SimpleNamespace(
            data={
                "ip_address": "192.0.2.1",
                "password": "1111",
                "name": "RECOM 4 SR issue 109 fixture",
                "auto_clock_sync": False,
            },
            unique_id=None,
            entry_id=f"issue109-{temperature_answers}-{late_temperature_answers}",
            async_on_unload=unload_callbacks.append,
            pref_disable_polling=True,
        )
        device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        coordinator = Coordinator(hass, entry)
        fan = coordinator._fan
        fan.id = "0123456789ABCDEF"
        wire = ScheduleWire(fan)
        wire.values = dict(ISSUE_109_DUMP_VALUES)
        if not temperature_answers:
            for param in RECOM_TEMPERATURE_PARAMS:
                wire.values.pop(param)
        wire.reject = set(REJECTED_PARAMS)
        fan.send, fan.receive = wire.send, wire.receive
        coordinator._should_refresh_schedule_week = lambda: False

        try:
            await coordinator.async_refresh()
            assert coordinator.last_update_success, repr(coordinator.last_exception)
            assert fan.profile_key == "vento"
            hass.data["ecovent_v2"] = {entry.entry_id: coordinator}
            unsupported = Diagnostics.hardware_profile_mismatch_state(fan)[-1]
            available = {
                spec.method
                for spec in Sensors.SENSOR_SPECS
                if fan.profile_has_entity_requirements(
                    required_params=spec.required_params or (spec.method,),
                    required_capabilities=spec.required_capabilities,
                )
            }
            initial_available = available.copy()
            initial_temperature_probes = fan.profile_supports_capability(
                "temperature_probes"
            )
            batches = await _setup_sensor_platform(hass, entry)
            initial_sensor_methods = _sensor_methods(batches)
            reloads = []

            if late_temperature_answers or not temperature_answers:
                with patch.object(
                    hass,
                    "config_entries",
                    types.SimpleNamespace(async_schedule_reload=reloads.append),
                ):
                    Integration._async_register_optional_poll_entity_sync(
                        hass, entry, coordinator
                    )
                    if late_temperature_answers:
                        wire.values.update(ISSUE_109_DUMP_VALUES)
                        for _ in range(
                            2 * FanProtocol.OPTIONAL_PARAM_RETRY_BACKOFF_READS + 4
                        ):
                            await coordinator.async_refresh()
                            if fan.profile_supports_capability("temperature_probes"):
                                break
                        assert fan.profile_supports_capability("temperature_probes")
                        for _ in range(3):
                            await coordinator.async_refresh()
                    else:
                        await coordinator.async_refresh()
                    await hass.async_block_till_done()

            available = {
                spec.method
                for spec in Sensors.SENSOR_SPECS
                if fan.profile_has_entity_requirements(
                    required_params=spec.required_params or (spec.method,),
                    required_capabilities=spec.required_capabilities,
                )
            }
            registered_sensor_methods = _sensor_methods(batches)
            temperature_entities = [
                entity
                for batch in batches
                for entity in batch
                if getattr(entity, "_method", None) is not None
                and entity._method.__name__ in TEMPERATURE_METHODS
            ]
            states = {}
            if temperature_entities:
                component = EntityComponent(
                    logging.getLogger(__name__), "sensor", hass
                )
                await component.async_add_entities(temperature_entities)
                await hass.async_block_till_done()
                for entity in temperature_entities:
                    state = hass.states.get(entity.entity_id)
                    assert state is not None, entity.entity_id
                    states[entity._method.__name__] = state.state

            return {
                "available_methods": available,
                "initial_available_methods": initial_available,
                "initial_sensor_methods": initial_sensor_methods,
                "registered_sensor_methods": registered_sensor_methods,
                "registered_temperature_methods": [
                    entity._method.__name__ for entity in temperature_entities
                ],
                "initial_temperature_probes": initial_temperature_probes,
                "temperature_probes": fan.profile_supports_capability(
                    "temperature_probes"
                ),
                "reloads": reloads,
                "entry_id": entry.entry_id,
                "unsupported_rows": unsupported,
                "states": states,
                "writes": fan.audible_write_command_count,
            }
        finally:
            await _async_unload_entry_callbacks(unload_callbacks)
            await hass.async_stop()


async def _run_entry_lifecycle_fixture():
    with tempfile.TemporaryDirectory(prefix="ecovent-ha-entry-lifecycle-") as tmp:
        hass = HomeAssistant(tmp)
        device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        reloads = []
        entries = []
        coordinators = []
        wires = []
        batches = []

        try:
            with patch.object(
                hass,
                "config_entries",
                types.SimpleNamespace(async_schedule_reload=reloads.append),
            ):
                for index in range(2):
                    unload_callbacks = []
                    entry = types.SimpleNamespace(
                        data={
                            "ip_address": "192.0.2.1",
                            "password": "1111",
                            "name": f"RECOM 4 SR entry {index}",
                            "auto_clock_sync": False,
                        },
                        unique_id=None,
                        entry_id=f"issue109-entry-{index}",
                        async_on_unload=unload_callbacks.append,
                        pref_disable_polling=True,
                    )
                    coordinator = Coordinator(hass, entry)
                    fan = coordinator._fan
                    fan.id = (
                        "0123456789ABCDEF"
                        if index == 0
                        else "1123456789ABCDEF"
                    )
                    wire = ScheduleWire(fan)
                    wire.values = dict(ISSUE_109_DUMP_VALUES)
                    for param in RECOM_TEMPERATURE_PARAMS:
                        wire.values.pop(param)
                    wire.reject = set(REJECTED_PARAMS)
                    fan.send, fan.receive = wire.send, wire.receive
                    coordinator._should_refresh_schedule_week = lambda: False
                    await coordinator.async_refresh()
                    assert coordinator.last_update_success
                    assert not fan.profile_supports_capability("temperature_probes")
                    hass.data.setdefault("ecovent_v2", {})[entry.entry_id] = coordinator
                    batches.append(
                        await _setup_sensor_platform(hass, entry)
                    )
                    Integration._async_register_optional_poll_entity_sync(
                        hass, entry, coordinator
                    )
                    entries.append((entry, unload_callbacks))
                    coordinators.append(coordinator)
                    wires.append(wire)

                _unload_entity_listeners(entries[0][1], coordinators[0])

                wires[0].values.update(ISSUE_109_DUMP_VALUES)
                for _ in range(2 * FanProtocol.OPTIONAL_PARAM_RETRY_BACKOFF_READS + 4):
                    await coordinators[0].async_refresh()
                    if coordinators[0]._fan.profile_supports_capability(
                        "temperature_probes"
                    ):
                        break
                assert coordinators[0]._fan.profile_supports_capability(
                    "temperature_probes"
                )
                assert not set(TEMPERATURE_METHODS) & set(_sensor_methods(batches[0]))

                wires[1].values.update(ISSUE_109_DUMP_VALUES)
                for _ in range(2 * FanProtocol.OPTIONAL_PARAM_RETRY_BACKOFF_READS + 4):
                    await coordinators[1].async_refresh()
                    if coordinators[1]._fan.profile_supports_capability(
                        "temperature_probes"
                    ):
                        break
                assert coordinators[1]._fan.profile_supports_capability(
                    "temperature_probes"
                )
                for _ in range(3):
                    await coordinators[1].async_refresh()

                second_methods = _sensor_methods(batches[1])
                assert all(
                    second_methods.count(method) == 1
                    for method in TEMPERATURE_METHODS
                )
                assert not set(TEMPERATURE_METHODS) & set(_sensor_methods(batches[0]))
                assert reloads == []
                await hass.async_block_till_done()
        finally:
            for _, unload_callbacks in entries:
                await _async_unload_entry_callbacks(unload_callbacks)
            await hass.async_stop()


async def _run_identity_reload_fixture():
    with tempfile.TemporaryDirectory(prefix="ecovent-ha-identity-reload-") as tmp:
        hass = HomeAssistant(tmp)
        unload_callbacks = []
        entry = types.SimpleNamespace(
            data={
                "ip_address": "192.0.2.1",
                "password": "1111",
                "name": "RECOM identity reload fixture",
                "auto_clock_sync": False,
            },
            unique_id=None,
            entry_id="issue109-identity-reload",
            async_on_unload=unload_callbacks.append,
            pref_disable_polling=True,
        )
        device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        coordinator = Coordinator(hass, entry)
        fan = coordinator._fan
        fan.id = "0123456789ABCDEF"
        wire = ScheduleWire(fan)
        wire.values = dict(ISSUE_109_DUMP_VALUES)
        wire.reject = set(REJECTED_PARAMS)
        fan.send, fan.receive = wire.send, wire.receive
        coordinator._should_refresh_schedule_week = lambda: False
        reloads = []

        try:
            await coordinator.async_refresh()
            assert coordinator.last_update_success
            hass.data["ecovent_v2"] = {entry.entry_id: coordinator}
            loaded_firmware = fan.firmware
            assert loaded_firmware is not None
            with patch.object(
                hass,
                "config_entries",
                types.SimpleNamespace(async_schedule_reload=reloads.append),
            ):
                Integration._async_register_optional_poll_entity_sync(
                    hass, entry, coordinator
                )
                firmware = bytearray(wire.values[0x0086])
                firmware[1] += 1
                wire.values[0x0086] = bytes(firmware)
                await coordinator.async_refresh()
                await coordinator.async_refresh()
            assert fan.firmware != loaded_firmware
            assert reloads == [entry.entry_id]
        finally:
            await _async_unload_entry_callbacks(unload_callbacks)
            await hass.async_stop()


def test_entry_listener_isolation_and_unload_cleanup():
    asyncio.run(_run_entry_lifecycle_fixture())


def test_device_identity_reload_is_preserved():
    asyncio.run(_run_identity_reload_fixture())

def test_recom_4_sr_dump_exposes_temperatures_and_no_known_variant_repair():
    result = asyncio.run(_run_issue_fixture(temperature_answers=True))
    late_result = asyncio.run(
        _run_issue_fixture(temperature_answers=False, late_temperature_answers=True)
    )
    assert set(TEMPERATURE_METHODS) <= result["available_methods"], (
        "missing RECOM sensors",
        sorted(set(TEMPERATURE_METHODS) - result["available_methods"]),
        "Repair rows",
        sorted(result["unsupported_rows"]),
    )
    assert result["states"] == ISSUE_109_EXPECTED_STATES
    assert result["unsupported_rows"] == frozenset()
    assert result["writes"] == 0

    assert not late_result["initial_temperature_probes"]
    assert late_result["temperature_probes"]
    assert not set(TEMPERATURE_METHODS) & late_result["initial_available_methods"]
    assert not set(TEMPERATURE_METHODS) & set(late_result["initial_sensor_methods"])
    assert set(TEMPERATURE_METHODS) <= late_result["available_methods"]
    assert set(TEMPERATURE_METHODS) <= set(late_result["registered_sensor_methods"])
    assert late_result["registered_temperature_methods"].count("outdoor_temperature") == 1
    assert len(late_result["registered_temperature_methods"]) == len(TEMPERATURE_METHODS)
    assert late_result["reloads"] == []
    assert late_result["states"] == ISSUE_109_EXPECTED_STATES



def test_df270_shaped_0100_without_temperature_answers_keeps_existing_behavior():
    result = asyncio.run(_run_issue_fixture(temperature_answers=False))
    assert not set(TEMPERATURE_METHODS) & result["available_methods"]
    assert not set(TEMPERATURE_METHODS) & set(result["registered_sensor_methods"])
    assert result["reloads"] == []
    assert result["unsupported_rows"] == REJECTED_PARAMS
    assert result["writes"] == 0


if __name__ == "__main__":
    if sys.argv[1:] == ["entry-lifecycle"]:
        test_entry_listener_isolation_and_unload_cleanup()
    elif sys.argv[1:] == ["identity-reload"]:
        test_device_identity_reload_is_preserved()
    elif sys.argv[1:] == ["df270"]:
        test_df270_shaped_0100_without_temperature_answers_keeps_existing_behavior()
    else:
        test_recom_4_sr_dump_exposes_temperatures_and_no_known_variant_repair()
    print("Issue 109 fixture passed; device writes: 0")

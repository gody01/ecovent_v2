"""Replay Freshpoint soft measurement misses through production HA polling.

Run with Home Assistant installed:
    python tests/ha_issue111_smoke.py

A fixture-backed wire drives the real coordinator, protocol parser, sensor
entities, and HA states. It covers quick/full polls, partial bulk replies,
intermittent CO2/RPM omission, and recovery. No network or device writes.
"""
import asyncio
import importlib
import logging
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from ha_issue100_smoke import Wire  # noqa: E402
from ha_issues101_102_smoke import sensor_for_method  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import device_registry, entity_registry  # noqa: E402
from homeassistant.helpers.entity_component import EntityComponent  # noqa: E402

package = types.ModuleType("issue111_ecovent")
package.__path__ = [str(ROOT / "custom_components/ecovent_v2")]
sys.modules[package.__name__] = package
Coordinator = importlib.import_module(package.__name__ + ".coordinator").EcoVentCoordinator
sensors = importlib.import_module(package.__name__ + ".sensor")


async def run():
    with tempfile.TemporaryDirectory(prefix="ecovent-ha-111-") as tmp:
        hass = HomeAssistant(tmp)
        entry = types.SimpleNamespace(
            data={
                "ip_address": "192.0.2.1",
                "password": "1111",
                "name": "Freshpoint",
                "auto_clock_sync": False,
            },
            unique_id=None,
            entry_id="issue111",
            async_on_unload=lambda _: None,
            pref_disable_polling=True,
        )
        device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        coordinator = Coordinator(hass, entry)
        fan = coordinator._fan
        wire = Wire(fan)
        wire.values[0x00B9] = bytes.fromhex("1100")
        wire.values[0x0086] = bytes.fromhex("00080f03e807")
        wire.values[0x0044] = b"\x50"
        wire.values[0x004A] = wire.values[0x004B] = (1800).to_bytes(2, "little")
        wire.values[0x0027] = (1500).to_bytes(2, "little")
        wire.values[0x0002] = b"\x03"
        fan.send, fan.receive = wire.send, wire.receive
        coordinator._should_refresh_schedule_week = lambda: False
        coordinator._update_hardware_profile_mismatch_repair_issue = lambda: None
        await coordinator.async_refresh()
        assert coordinator.last_update_success, coordinator.last_exception
        assert fan.profile_key == "breezy", fan.profile_key

        hass.data["ecovent_v2"] = {entry.entry_id: coordinator}
        entities = [
            sensor_for_method(sensors, hass, entry, method)
            for method in ("fan1_speed", "fan2_speed", "co2")
        ]
        for entity in entities:
            entity._attr_entity_registry_enabled_default = True
        component = EntityComponent(logging.getLogger(__name__), "sensor", hass)
        await component.async_add_entities(entities)
        await hass.async_block_till_done()

        def states():
            return [hass.states.get(entity.entity_id).state for entity in entities]

        assert states() == ["1800", "1800", "1500"], states()
        print("initial full poll:", states())

        async def quick_poll(rpm, co2, *, bulk_gap=(), omitted=()):
            wire.values[0x004A] = wire.values[0x004B] = rpm.to_bytes(2, "little")
            wire.values[0x0027] = co2.to_bytes(2, "little")
            wire.values[0x0002] = b"\x04"  # Party/Turbo speed
            wire.values[0x0007] = b"\x02"  # Timer/boost mode
            wire.bulk_omit = set(bulk_gap)
            wire.omit = set(omitted)
            wire.calls.clear()
            fan._bulk_read_supported = True
            coordinator.updateCounter = 4  # next coordinator update is quick
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            assert coordinator.last_update_success, coordinator.last_exception

        await quick_poll(2340, 2014)
        assert states() == ["2340", "2340", "2014"], states()
        print("quick Party/Turbo values above 2000:", states())

        await quick_poll(1999, 1100, bulk_gap=(0x004B,))
        assert states() == ["1999", "1999", "1100"], states()
        assert any(0x004B in call for call in wire.calls)
        print("partial bulk fan2 retry:", states())

        # The controller values change, but transiently omits both optional
        # measurement rows in bulk and individual responses. Known values stay
        # visible instead of becoming unknown during the retry backoff.
        await quick_poll(2340, 2014, omitted=(0x004B, 0x0027))
        assert states() == ["2340", "1999", "1100"], states()
        assert 0x004B in fan.last_missing_optional_params
        assert 0x0027 in fan.last_missing_optional_params
        print("soft omission retains last good measurements:", states())

        wire.omit.clear()
        wire.bulk_omit.clear()
        coordinator.updateCounter = 3  # next coordinator update is full
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert coordinator.last_update_success, coordinator.last_exception
        assert states() == ["2340", "2340", "2014"], states()
        print("full-poll recovery:", states())
        await hass.async_stop()


asyncio.run(run())

"""Freshbox entity setup and real protocol writes for issue #120."""

import asyncio
import types
import unittest

from ecovent_test_helpers import Fan, packet_for_write_command, packet_with_payload
from test_issue116_regressions import Sensors, _sync_registry


class _Hass:
    def __init__(self, coordinator):
        self.data = {"ecovent_v2": {"entry": coordinator}}

    async def async_add_executor_job(self, function, *args):
        return function(*args)


class _Coordinator:
    last_update_success = True

    def __init__(self, fan):
        self._fan = fan
        self.listeners = []
        self.refreshes = 0

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: None

    async def async_refresh_confirmed(self):
        self.refreshes += 1
        if not self._fan._read_params("00180068008100B6", require_all_requested=True):
            raise AssertionError("Fixture failed to return all four control/status rows")
        for listener in self.listeners:
            listener()


class _Device:
    """Use real Fan setters, encoders and parsers; replace only the UDP wire."""

    def __init__(self, unit_type="0200", *, retain_writes=True):
        self.fan = Fan("192.0.2.1")
        self.fan.unit_type = unit_type
        self.fan._id = "DEFAULT_DEVICEID"
        self.fan._name = "Issue 120 device"
        self.commands = []
        self.registers = {0x18: 22, 0x68: 0, 0x81: 0, 0xB6: 0}
        self.retain_writes = retain_writes
        self.fan.send = self.send
        self.fan.receive = self.receive
        self.coordinator = _Coordinator(self.fan)
        self.hass = _Hass(self.coordinator)
        self.config = types.SimpleNamespace(
            entry_id="entry", async_on_unload=lambda callback: None
        )

    def send(self, command):
        self.commands.append(command)
        if command.startswith("03") and self.retain_writes:
            param, value = bytes.fromhex(command[2:])
            self.registers[param] = value
        return True

    def receive(self):
        command = self.commands[-1]
        if command.startswith("03"):
            return packet_for_write_command(command)
        payload = []
        for param in bytes.fromhex(command[2:]):
            payload.extend((param, self.registers[param]))
        return packet_with_payload(payload)

    def setup(self, platform):
        entities = {}

        def add_entities(new_entities):
            for entity in new_entities:
                entity.hass = self.hass
                entities[entity._ecovent_object_id_suffix] = entity

        asyncio.run(Sensors.platform_modules[platform].async_setup_entry(
            self.hass, self.config, add_entities
        ))
        return entities

    def report(self, payload, *, request=None):
        packet = packet_with_payload(payload)
        if request is None:
            success = self.fan.parse_response(packet)
        else:
            # Discovery bookkeeping belongs to polling, not bare packet parsing.
            receive = self.fan.receive
            self.fan.receive = lambda: packet
            try:
                success = self.fan._read_params(request, require_all_requested=True)
            finally:
                self.fan.receive = receive
        if not success:
            raise AssertionError("Invalid fixture response")
        for listener in self.coordinator.listeners:
            listener()


def _registry_for_entities(device, platforms):
    entries = {}
    for platform, entities in platforms.items():
        for entity in entities.values():
            entries[(platform, entity._attr_unique_id)] = types.SimpleNamespace(hidden_by=None)
    registry = types.SimpleNamespace(
        async_get_entity_id=lambda platform, domain, unique_id: (
            (platform, unique_id) if (platform, unique_id) in entries else None
        ),
        async_get=entries.get,
        async_update_entity=lambda entity_id, **changes: setattr(
            entries[entity_id], "hidden_by", changes["hidden_by"]
        ),
    )
    _sync_registry(registry, device.fan)
    return registry, entries


class Issue120EntityTest(unittest.TestCase):
    def test_setup_exposes_one_writable_setpoint_and_separate_heater_entities(self):
        device = _Device()
        numbers = device.setup("number")
        sensors = device.setup("sensor")
        switches = device.setup("switch")
        binary = device.setup("binary_sensor")
        self.assertNotIn("temperature_setpoint", sensors)
        number = numbers["temperature_setpoint"]
        self.assertEqual((number._attr_native_min_value, number._attr_native_max_value,
                          number._attr_native_step), (15, 30, 1))
        self.assertEqual(number._attr_native_unit_of_measurement, "°C")
        self.assertEqual(number._attr_device_class, "temperature")
        self.assertIn("heater_state", switches)
        self.assertEqual(binary["heater_status"]._attr_device_class, "heat")
        blowing = binary["heater_blowing_status"]
        self.assertEqual(blowing._attr_name, "Electric heater blowing")
        self.assertEqual(blowing._attr_entity_category, "diagnostic")
        self.assertFalse(blowing._attr_entity_registry_enabled_default)
        registry, entries = _registry_for_entities(device, {"sensor": sensors})
        legacy_id = ("sensor", device.fan.id + "_temperature_setpoint")
        entries[legacy_id] = types.SimpleNamespace(hidden_by=None)
        _sync_registry(registry, device.fan)
        self.assertEqual(entries[legacy_id].hidden_by, "integration")

    def test_optional_hardware_discovery_and_registry_visibility_survive(self):
        device = _Device()
        sensors = device.setup("sensor")
        binary = device.setup("binary_sensor")
        self.assertNotIn("outdoor_temperature", sensors)
        registry, entries = _registry_for_entities(device, {"binary_sensor": binary})
        status_id = ("binary_sensor", device.fan.id + "_heater_status")
        self.assertEqual(entries[status_id].hidden_by, "integration")
        device.report([0xFE, 2, 0x1F, 100, 0, 0x81, 1], request="001F0081")
        _sync_registry(registry, device.fan)
        self.assertIsNone(entries[status_id].hidden_by)
        self.assertTrue(binary["heater_status"].is_on)
        # The sensor setup listener adds newly discovered probes without a reload.
        self.assertTrue(device.fan.supports_parameter("outdoor_temperature"))
        self.assertEqual(sensors["outdoor_temperature"].native_value, 10.0)
        self.assertNotIn("temperature_setpoint", sensors)

    def test_setpoint_boundaries_write_one_raw_byte_and_confirm_refresh(self):
        device = _Device()
        number = device.setup("number")["temperature_setpoint"]
        for value in (15, 22, 30):
            with self.subTest(value=value):
                device.commands.clear()
                before = device.coordinator.refreshes
                asyncio.run(number.async_set_native_value(value))
                self.assertEqual(device.commands[0], f"0318{value:02x}")
                self.assertTrue(device.commands[1].startswith("01"))
                self.assertEqual(device.coordinator.refreshes, before + 1)
                self.assertEqual(number.native_value, value)
        for value in (14, 31):
            with self.subTest(value=value):
                device.commands.clear()
                before = device.coordinator.refreshes
                with self.assertRaisesRegex(RuntimeError, "Failed to write"):
                    asyncio.run(number.async_set_native_value(value))
                self.assertFalse(any(command.startswith("03") for command in device.commands))
                self.assertEqual(device.coordinator.refreshes, before + 1)
                self.assertEqual(number.native_value, 30)

    def test_unretained_setpoint_write_is_not_reported_as_success(self):
        device = _Device(retain_writes=False)
        number = device.setup("number")["temperature_setpoint"]
        with self.assertRaisesRegex(RuntimeError, "Device did not confirm"):
            asyncio.run(number.async_set_native_value(30))
        self.assertEqual(device.commands[0], "03181e")
        self.assertEqual(device.coordinator.refreshes, 1)
        self.assertEqual(number.native_value, 22)

    def test_regulation_switch_writes_and_refreshes_without_changing_actual_heat(self):
        device = _Device()
        switch = device.setup("switch")["heater_state"]
        active = device.setup("binary_sensor")["heater_status"]
        for enabled, expected in ((True, "036801"), (False, "036800")):
            with self.subTest(enabled=enabled):
                device.commands.clear()
                before = device.coordinator.refreshes
                asyncio.run(switch.async_turn_on() if enabled else switch.async_turn_off())
                self.assertEqual(device.commands[0], expected)
                self.assertEqual(device.coordinator.refreshes, before + 1)
                self.assertEqual(switch.is_on, enabled)
                self.assertFalse(active.is_on)
        device.report([0x68, 0, 0x81, 1, 0xB6, 0])
        self.assertFalse(switch.is_on)
        self.assertTrue(active.is_on)

    def test_unretained_switch_write_is_not_reported_as_success(self):
        device = _Device(retain_writes=False)
        switch = device.setup("switch")["heater_state"]
        with self.assertRaisesRegex(RuntimeError, "Device did not confirm"):
            asyncio.run(switch.async_turn_on())
        self.assertEqual(device.commands[0], "036801")
        self.assertEqual(device.coordinator.refreshes, 1)
        self.assertFalse(switch.is_on)

    def test_actual_heat_and_blowing_are_independent_and_preserve_unknowns(self):
        device = _Device()
        binary = device.setup("binary_sensor")
        active, blowing = binary["heater_status"], binary["heater_blowing_status"]
        self.assertIsNone(active.is_on)
        self.assertIsNone(blowing.is_on)
        for heat, blow in ((0, 1), (1, 0), (1, 1), (0, 0)):
            with self.subTest(heat=heat, blow=blow):
                device.report([0x81, heat, 0xB6, blow])
                self.assertEqual(active.is_on, bool(heat))
                self.assertEqual(blowing.is_on, bool(blow))
        device.report([0x81, 0xFF, 0xB6, 0xFF])
        self.assertIsNone(active.is_on)
        self.assertIsNone(blowing.is_on)

    def test_non_freshbox_keeps_read_only_setpoint_without_new_heater_surfaces(self):
        # Existing Recom fixture declares setpoint/probes; ordinary Vento does not.
        device = _Device("0100")
        device.report([0x18, 22, 0xFE, 2, 0x1F, 100, 0,
                       0xFE, 2, 0x20, 150, 0, 0xFE, 2, 0x21, 200, 0,
                       0xFE, 2, 0x22, 120, 0], request="0018001F002000210022")
        self.assertEqual(device.setup("sensor")["temperature_setpoint"].native_value, 22)
        self.assertNotIn("temperature_setpoint", device.setup("number"))
        for unit_type in ("0100", "1100", "0e00"):
            with self.subTest(unit_type=unit_type):
                other = _Device(unit_type)
                self.assertNotIn("temperature_setpoint", other.setup("number"))
                binary = other.setup("binary_sensor")
                self.assertFalse({"heater_status", "heater_blowing_status"} & binary.keys())
                self.assertNotIn("freshbox_recovery_efficiency", other.setup("sensor"))


if __name__ == "__main__":
    unittest.main()

"""Behavior regressions for Freshbox/Micra probes and preset confirmation."""

import ast
import logging
import asyncio
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

from ecovent_test_helpers import COMPONENT_PATH, Fan, packet_with_payload
from test_silent_fan_entity import VentoExpertFan, _CoordinatorEntity, _module


PACKAGE = "ecovent_v2_issue116_test"
PROBES = ("outdoor_temperature", "supply_temperature", "exhaust_in_temperature", "exhaust_out_temperature")


def _load_sensors():
    with patch.dict(sys.modules):
        _module("voluptuous")
        _module(
            "homeassistant.components.sensor",
            SensorEntity=type("SensorEntity", (), {}),
            SensorDeviceClass=types.SimpleNamespace(**{name: name for name in (
                "HUMIDITY", "TEMPERATURE", "ILLUMINANCE", "ENUM", "DURATION", "BATTERY"
            )}),
            SensorStateClass=types.SimpleNamespace(MEASUREMENT="measurement"),
        )
        _module("homeassistant.const", LIGHT_LUX="lx", PERCENTAGE="%",
                REVOLUTIONS_PER_MINUTE="rpm",
                EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic"),
                UnitOfTemperature=types.SimpleNamespace(CELSIUS="°C"))
        _module("homeassistant.helpers.update_coordinator", CoordinatorEntity=_CoordinatorEntity)
        package = _module(PACKAGE)
        package.__path__ = [str(COMPONENT_PATH)]
        _module(f"{PACKAGE}.const", DOMAIN="ecovent_v2")
        _module(f"{PACKAGE}.coordinator", EcoVentCoordinator=object)
        _module(f"{PACKAGE}.ecoventv2", Fan=Fan)
        _module(f"{PACKAGE}.entity_naming",
                StableObjectIdMixin=type("StableObjectIdMixin", (), {}),
                clean_object_id_suffix=lambda value: value)
        name = f"{PACKAGE}.sensor"
        spec = importlib.util.spec_from_file_location(name, COMPONENT_PATH / "sensor.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


Sensors = _load_sensors()


class _Hass:
    async def async_add_executor_job(self, function, *args):
        return function(*args)


class _Coordinator:
    silent_mode_enabled = False
    silent_preset_mode = None

    def __init__(self, fan):
        self._fan = fan
        self.listeners = []

    def set_silent_preset_mode(self, value):
        self.silent_preset_mode = value

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: None

    async def async_refresh_confirmed(self):
        # Same raw 0x0002 reply received after a successful command.
        self._fan.parse_response(packet_with_payload([1, self.state, 2, self.speed]))


def _freshbox(*, speed=1, state=1, ignore_writes=False):
    fan = Fan("192.0.2.1")
    fan.unit_type = "0200"
    fan._id = "DEFAULT_DEVICEID"
    fan._name = "Micra ERV2"
    fan.parse_response(packet_with_payload([1, state, 2, speed]))
    coordinator = _Coordinator(fan)
    coordinator.state, coordinator.speed = state, speed
    calls = []

    def send_command(function, params, value="", retries=10):
        calls.append((function, params, value))
        if not ignore_writes:
            if params == "0002":
                coordinator.speed = int(value, 16)
            elif params == "0001":
                coordinator.state = int(value, 16)
        return fan.parse_response(packet_with_payload([1, coordinator.state, 2, coordinator.speed]))

    fan.send_command = send_command
    entity = VentoExpertFan.__new__(VentoExpertFan)
    entity._fan = fan
    entity.coordinator = coordinator
    entity.hass = _Hass()
    return entity, fan, calls


def _sensor_entities(fan):
    coordinator = _Coordinator(fan)
    hass = types.SimpleNamespace(data={"ecovent_v2": {"entry": coordinator}})
    config = types.SimpleNamespace(entry_id="entry", async_on_unload=lambda callback: None)
    entities = []
    asyncio.run(Sensors.async_setup_entry(hass, config, entities.extend))
    return {entity._ecovent_object_id_suffix: entity for entity in entities}


class Issue116RegressionTest(unittest.TestCase):
    def test_freshbox_exposes_reported_probes_and_heater_without_optional_modules(self):
        _, fan, _ = _freshbox()
        payload = []
        for param, tenths in zip(range(0x1F, 0x23), (103, 186, 192, 141)):
            payload.extend([0xFE, 2, param, *tenths.to_bytes(2, "little", signed=True)])
        payload.extend([0x81, 1])
        self.assertTrue(fan.parse_response(packet_with_payload(payload)))
        entities = _sensor_entities(fan)
        for name, expected in zip(PROBES, (10.3, 18.6, 19.2, 14.1)):
            self.assertEqual(entities[name].native_value, expected)
        self.assertEqual(entities["heater_status"].native_value, "on")
        self.assertFalse({"co2", "humidity", "temperature_setpoint"} & entities.keys())
        self.assertAlmostEqual(entities["freshbox_recovery_efficiency"].native_value, 93.2584269663)

    def test_registry_hides_unreported_rows_and_restores_reported_rows(self):
        _, fan, _ = _freshbox()
        entities = _sensor_entities(fan)
        entries = {entity._attr_unique_id: types.SimpleNamespace(hidden_by=None)
                   for entity in entities.values()}
        registry = types.SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: unique_id if unique_id in entries else None,
            async_get=entries.get,
            async_update_entity=lambda entity_id, **changes: setattr(entries[entity_id], "hidden_by", changes["hidden_by"]),
        )
        tree = ast.parse((COMPONENT_PATH / "__init__.py").read_text())
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_async_update_unsupported_optional_poll_entities")
        namespace = {"__package__": PACKAGE, "DOMAIN": "ecovent_v2",
                     "Platform": types.SimpleNamespace(SENSOR="sensor", BINARY_SENSOR="binary_sensor",
                                                        SWITCH="switch", NUMBER="number", SELECT="select"),
                     "er": types.SimpleNamespace(RegistryEntryHider=types.SimpleNamespace(INTEGRATION="integration")),
                     "_LOGGER": logging.getLogger(__name__)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "__init__.py", "exec"), namespace)
        with patch.dict(sys.modules):
            _module(f"{PACKAGE}.sensor_specs", SENSOR_SPECS=Sensors.SENSOR_SPECS)
            for module, attribute in (("binary_sensor", "BINARY_SENSOR_SPECS"), ("number", "NUMBER_SPECS"),
                                      ("select", "SELECT_SPECS"), ("switch", "SWITCH_SPECS")):
                _module(f"{PACKAGE}.{module}", **{attribute: ()})
            fan.send_command = lambda *args, **kwargs: fan.parse_response(
                packet_with_payload([2, 1, 6, 0, 0xFD, 0x20, 0xFD, 0x81]))
            self.assertTrue(fan._read_params("0002000600200081", required_params=frozenset({2, 6})))
            sync = namespace["_async_update_unsupported_optional_poll_entities"]
            sync(registry, fan)
            for name in ("supply_temperature", "heater_status", "freshbox_recovery_efficiency"):
                self.assertEqual(entries[entities[name]._attr_unique_id].hidden_by, "integration")
            self.assertIsNone(entries[entities["outdoor_temperature"]._attr_unique_id].hidden_by)
            fan.send_command = lambda *args, **kwargs: fan.parse_response(
                packet_with_payload([0xFE, 2, 0x20, 186, 0, 0x81, 1]))
            self.assertTrue(fan._read_params("00200081"))
            sync(registry, fan)
            for name in ("supply_temperature", "heater_status", "freshbox_recovery_efficiency"):
                self.assertIsNone(entries[entities[name]._attr_unique_id].hidden_by)

    def test_rejected_rows_use_existing_entity_gates_and_recover(self):
        _, fan, _ = _freshbox()
        fan.send_command = lambda *args, **kwargs: fan.parse_response(
            packet_with_payload([2, 1, 6, 0, 0xFD, 0x20, 0xFD, 0x81]))
        self.assertTrue(fan._read_params("0002000600200081", required_params=frozenset({2, 6})))
        specs = {spec.method: spec for spec in Sensors.SENSOR_SPECS}
        for name in ("supply_temperature", "heater_status", "freshbox_recovery_efficiency"):
            spec = specs[name]
            self.assertFalse(fan.supports_entity(
                required_params=spec.required_params or (spec.method,),
                required_capabilities=spec.required_capabilities))
        self.assertTrue(fan.supports_entity(required_params=("outdoor_temperature",),
                                            required_capabilities=("temperature_probes",)))
        fan.send_command = lambda *args, **kwargs: fan.parse_response(
            packet_with_payload([0xFE, 2, 0x20, 186, 0, 0x81, 1]))
        self.assertTrue(fan._read_params("00200081"))
        self.assertTrue(fan.supports_entity(required_params=("supply_temperature",),
                                            required_capabilities=("temperature_probes",)))

    def test_all_five_presets_confirm_raw_readback_and_skip_true_noop(self):
        for service in ("async_set_preset_mode", "async_turn_on"):
            for speed in range(1, 6):
                with self.subTest(service=service, speed=speed):
                    entity, fan, calls = _freshbox(speed=5 if speed == 1 else 1)
                    preset = f"speed_{speed}"
                    if service == "async_turn_on":
                        asyncio.run(entity.async_turn_on(preset_mode=preset))
                    else:
                        asyncio.run(entity.async_set_preset_mode(preset))
                    self.assertEqual(entity.preset_mode, preset)
                    self.assertIn(("03", "0002", f"{speed:02x}"), calls)
                    count = len(calls)
                    asyncio.run(entity.async_set_preset_mode(preset))
                    self.assertEqual(len(calls), count)

    def test_ignored_preset_write_still_raises(self):
        for service in ("async_set_preset_mode", "async_turn_on"):
            entity, _, _ = _freshbox(ignore_writes=True)
            with self.subTest(service=service), self.assertRaisesRegex(RuntimeError, "Device did not confirm preset"):
                if service == "async_turn_on":
                    asyncio.run(entity.async_turn_on(preset_mode="speed_2"))
                else:
                    asyncio.run(entity.async_set_preset_mode("speed_2"))

    def test_freshbox_percentage_display_and_power_confirmation(self):
        entity, fan, _ = _freshbox(speed=2, state=0)
        fan.parse_response(packet_with_payload([0x3C, 40, 0x3D, 50]))
        self.assertFalse(fan.supports_percentage_control)
        asyncio.run(entity.async_turn_on())
        self.assertEqual(entity.percentage, 45)
        asyncio.run(entity.async_turn_off())
        self.assertEqual(entity.percentage, 0)
        self.assertEqual(entity.preset_mode, "off")
        asyncio.run(entity.async_set_percentage(0))
        with self.assertRaisesRegex(RuntimeError, "Failed to write speed='manual'"):
            asyncio.run(entity.async_set_percentage(45))

    def test_ignored_power_writes_still_raise(self):
        for state, service in ((0, "async_turn_on"), (1, "async_turn_off")):
            entity, _, _ = _freshbox(state=state, ignore_writes=True)
            with self.subTest(service=service), self.assertRaisesRegex(RuntimeError, "Device did not confirm power"):
                asyncio.run(getattr(entity, service)())

    def test_efficiency_guards_missing_and_near_equal_probes_without_clamping(self):
        _, fan, _ = _freshbox()
        sensor = Sensors.VentoSensor.__new__(Sensors.VentoSensor)
        sensor._fan = fan
        for values in ((None, 18.6, 19.2), (10.3, None, 19.2), (10.3, 18.6, None),
                       (10.3, 18.6, 10.3), (10.3, 18.6, 10.35)):
            fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = values
            self.assertIsNone(sensor.freshbox_recovery_efficiency())
        for values, expected in (((0, 30, 20), 150), ((30, 10, 20), 200), ((0, -10, 20), -50)):
            fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = values
            self.assertEqual(sensor.freshbox_recovery_efficiency(), expected)

    def test_vento_speed_mapping_is_unchanged(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0e00"
        for raw, expected in ((1, "low"), (2, "medium"), (3, "high"), (0xFF, "manual")):
            self.assertTrue(fan.parse_response(packet_with_payload([2, raw])))
            self.assertEqual(fan.speed, expected)

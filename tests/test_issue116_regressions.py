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
        _module("voluptuous", Optional=lambda key: key, Required=lambda key: key,
                In=lambda values: values, All=lambda *validators: validators,
                Coerce=lambda value: value, Range=lambda **bounds: bounds)
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
        _module("homeassistant.components.number",
                NumberEntity=type("NumberEntity", (), {}),
                NumberDeviceClass=types.SimpleNamespace(TEMPERATURE="temperature"),
                NumberMode=types.SimpleNamespace(AUTO="auto", BOX="box"))
        _module("homeassistant.components.binary_sensor",
                BinarySensorEntity=type("BinarySensorEntity", (), {}),
                BinarySensorDeviceClass=types.SimpleNamespace(PROBLEM="problem", HEAT="heat"))
        _module("homeassistant.components.select", SelectEntity=type("SelectEntity", (), {}))
        _module("homeassistant.components.switch",
                SwitchEntity=type("SwitchEntity", (), {}),
                SwitchDeviceClass=types.SimpleNamespace(SWITCH="switch"))
        _module("homeassistant.config_entries", ConfigEntry=object)
        _module("homeassistant.core", HomeAssistant=object)
        _module("homeassistant.helpers.device_registry", DeviceInfo=lambda **kwargs: kwargs)
        sys.modules["homeassistant.const"].EntityCategory.CONFIG = "config"
        _module("homeassistant.helpers.update_coordinator", CoordinatorEntity=_CoordinatorEntity)
        _module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object,
                async_get_current_platform=lambda: types.SimpleNamespace(
                    async_register_entity_service=lambda *args: None))
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
        module.registry_specs = {"sensor_specs": ("SENSOR_SPECS", module.SENSOR_SPECS)}
        module.platform_modules = {"sensor": module}
        for platform, attribute in (("binary_sensor", "BINARY_SENSOR_SPECS"),
                                    ("number", "NUMBER_SPECS"), ("select", "SELECT_SPECS"),
                                    ("switch", "SWITCH_SPECS")):
            platform_module = importlib.import_module(f"{PACKAGE}.{platform}")
            module.registry_specs[platform] = (attribute, getattr(platform_module, attribute))
            module.platform_modules[platform] = platform_module
        return module


Sensors = _load_sensors()


class _Hass:
    async def async_add_executor_job(self, function, *args):
        return function(*args)


class _Coordinator:
    _failed_polls = 0
    last_update_success = True
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


def _sensor_entities(fan, coordinator=None):
    coordinator = coordinator or _Coordinator(fan)
    hass = types.SimpleNamespace(data={"ecovent_v2": {"entry": coordinator}})
    config = types.SimpleNamespace(entry_id="entry", async_on_unload=lambda callback: None)
    entities = []
    asyncio.run(Sensors.async_setup_entry(hass, config, entities.extend))
    return entities


def _entities_by_suffix(fan):
    return {entity._ecovent_object_id_suffix: entity for entity in _sensor_entities(fan)}


def _read_payload(fan, payload, request, required_params=None):
    fan.send_command = lambda *args, **kwargs: fan.parse_response(packet_with_payload(payload))
    return fan._read_params(request, required_params=required_params)


# Synthetic valid values; response parameter IDs come from issue #116.
_MICRA_TEST_VALUES = {
    0x0001: b"\x01",
    0x0002: b"\x02",
    0x000B: b"\x2a\x00\x00",
    0x0032: b"\x01",
    0x0033: b"\x00",
    0x0081: b"\x01",
    0x0083: b"\x00",
    0x00A1: b"\x01",
    0x00B6: b"\x01",
}


def _encode_poll_value(param_id, value):
    if len(value) > 1:
        return [0xFE, len(value), param_id & 0xFF, *value]
    return [param_id & 0xFF, *value]


def _mock_micra_poll(fan, *, omitted=(), transport_failure=False):
    requests = []

    def send_command(function, params, value="", retries=10):
        requests.append(params)
        if transport_failure:
            return False
        payload = []
        for offset in range(0, len(params), 4):
            param_id = int(params[offset : offset + 4], 16)
            if param_id == 0x0006 or param_id in omitted:
                continue
            raw_value = _MICRA_TEST_VALUES.get(param_id)
            if raw_value is not None:
                payload.extend(_encode_poll_value(param_id, raw_value))
        if not payload:
            return False
        return fan.parse_response(packet_with_payload(payload))

    fan.send_command = send_command
    return requests


def _registry(fan):
    entries = {fan.id + spec.key: types.SimpleNamespace(hidden_by=None)
               for spec in Sensors.SENSOR_SPECS}
    registry = types.SimpleNamespace(
        async_get_entity_id=lambda platform, domain, unique_id: unique_id if unique_id in entries else None,
        async_get=entries.get,
        async_update_entity=lambda entity_id, **changes: setattr(entries[entity_id], "hidden_by", changes["hidden_by"]),
    )
    return registry, entries


def _sync_registry(registry, fan):
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
        for module, (attribute, specs) in Sensors.registry_specs.items():
            _module(f"{PACKAGE}.{module}", **{attribute: specs})
        namespace["_async_update_unsupported_optional_poll_entities"](registry, fan)


def _register_registry_sync(registry, coordinator):
    tree = ast.parse((COMPONENT_PATH / "__init__.py").read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ("_fan_identity", "_async_register_optional_poll_entity_sync")]
    namespace = {
        "HomeAssistant": object, "ConfigEntry": object, "EcoVentCoordinator": object,
        "er": types.SimpleNamespace(async_get=lambda hass: registry),
        "_LOGGER": logging.getLogger(__name__),
        "_async_update_unsupported_optional_poll_entities": _sync_registry,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "__init__.py", "exec"), namespace)
    hass = types.SimpleNamespace(config_entries=types.SimpleNamespace(
        async_schedule_reload=lambda entry_id: None))
    entry = types.SimpleNamespace(entry_id="entry", async_on_unload=lambda callback: None)
    namespace["_async_register_optional_poll_entity_sync"](hass, entry, coordinator)


class Issue116RegressionTest(unittest.TestCase):
    def test_freshbox_quick_poll_ignores_missing_boost_status_and_keeps_0032(self):
        _, fan, _ = _freshbox()
        requests = _mock_micra_poll(fan)

        self.assertTrue(fan.quick_update())
        self.assertEqual(fan.boost_switch_status, "on")
        quick_ids = {
            int(params[offset : offset + 4], 16)
            for params in requests
            for offset in range(0, len(params), 4)
        }
        self.assertNotIn(0x0006, quick_ids)
        self.assertIn(0x0032, quick_ids)

    def test_freshbox_full_poll_keeps_missing_0006_optional(self):
        _, fan, _ = _freshbox()
        requests = _mock_micra_poll(fan)

        self.assertTrue(fan.update())
        self.assertEqual(fan.boost_switch_status, "on")
        full_ids = {
            int(params[offset : offset + 4], 16)
            for params in requests
            for offset in range(0, len(params), 4)
        }
        self.assertIn(0x0006, full_ids)
        self.assertIn(0x0002, full_ids)

    def test_freshbox_full_poll_still_requires_speed_0002(self):
        _, fan, _ = _freshbox()
        _mock_micra_poll(fan, omitted={0x0002})

        self.assertFalse(fan.update())
        self.assertEqual(fan._last_missing_required_params, frozenset({0x0002}))

    def test_freshbox_full_poll_still_fails_on_transport_error(self):
        _, fan, _ = _freshbox()
        _mock_micra_poll(fan, transport_failure=True)

        self.assertFalse(fan.update())
        self.assertEqual(fan._last_missing_required_params, frozenset({0x0002}))

    def test_real_spec_registry_sync_is_stable_on_repeated_successful_polls(self):
        from test_a21_modbus import A21ModbusDevice

        devices = []
        for unit_type in ("0100", "1100", "0200"):
            fan = Fan("192.0.2.1")
            fan.unit_type = unit_type
            fan._id = "DEFAULT_DEVICEID"
            devices.append(fan)
        devices.append(A21ModbusDevice(transport="modbus_tcp", endpoint="192.0.2.1",
                                       name="A21", model="A21"))
        speed_methods = tuple(f"{direction}_speed_{level}"
                              for level in ("low", "medium", "high")
                              for direction in ("supply", "exhaust"))
        for fan in devices:
            with self.subTest(profile=fan.profile_key):
                entries = {}
                for module, (_, specs) in Sensors.registry_specs.items():
                    platform = "sensor" if module == "sensor_specs" else module
                    for spec in specs:
                        suffix = spec.method if platform == "number" else spec.key
                        entries[(platform, fan.id + suffix)] = types.SimpleNamespace(hidden_by=None)
                entries[("sensor", fan.id + "_schedule")] = types.SimpleNamespace(hidden_by=None)
                updates = []

                def update(entity_id, **changes):
                    updates.append((entity_id, changes))
                    entries[entity_id].hidden_by = changes["hidden_by"]

                registry = types.SimpleNamespace(
                    async_get_entity_id=lambda platform, domain, unique_id:
                        (platform, unique_id) if (platform, unique_id) in entries else None,
                    async_get=entries.get, async_update_entity=update)
                coordinator = _Coordinator(fan)
                _register_registry_sync(registry, coordinator)
                first_updates = [entity_id for entity_id, _ in updates]
                self.assertEqual(len(first_updates), len(set(first_updates)))
                updates.clear()
                for listener in coordinator.listeners:
                    listener()
                self.assertEqual(updates, [])
                if fan.profile_key in ("vento", "breezy"):
                    for method in speed_methods:
                        self.assertTrue(fan.supports_entity(
                            required_params=(method,),
                            required_capabilities=("three_speed_setpoints",)))
                        self.assertIsNone(entries[("number", fan.id + method)].hidden_by)

                # Failed polls must not restore even a supported persisted entry.
                supported_id = next(entity_id for entity_id, entry in entries.items()
                                    if entry.hidden_by is None)
                entries[supported_id].hidden_by = "integration"
                coordinator.last_update_success = False
                for listener in coordinator.listeners:
                    listener()
                self.assertEqual(updates, [])
                self.assertEqual(entries[supported_id].hidden_by, "integration")
                coordinator.last_update_success = True
                for listener in coordinator.listeners:
                    listener()
                self.assertEqual(updates, [(supported_id, {"hidden_by": None})])

    def test_freshbox_exposes_reported_probes_and_heater_without_optional_modules(self):
        _, fan, _ = _freshbox()
        payload = []
        for param, tenths in zip(range(0x1F, 0x23), (103, 186, 192, 141)):
            payload.extend([0xFE, 2, param, *tenths.to_bytes(2, "little", signed=True)])
        payload.extend([0x81, 1])
        self.assertTrue(_read_payload(fan, payload, "001F0020002100220081"))
        entities = _entities_by_suffix(fan)
        for name, expected in zip(PROBES, (10.3, 18.6, 19.2, 14.1)):
            self.assertEqual(entities[name].native_value, expected)
        self.assertEqual(entities["heater_status"].native_value, "on")
        self.assertFalse({"co2", "humidity", "temperature_setpoint"} & entities.keys())
        self.assertEqual(entities["freshbox_recovery_efficiency"].native_value, 93.3)

    def test_registry_hides_explicitly_rejected_rows_and_restores_reported_rows(self):
        _, fan, _ = _freshbox()
        self.assertTrue(_read_payload(fan, [0xFE, 2, 0x1F, 103, 0, 0xFE, 2, 0x21, 192, 0], "001F0021"))
        registry, entries = _registry(fan)
        self.assertTrue(_read_payload(fan, [2, 1, 6, 0, 0xFD, 0x20, 0xFD, 0x81],
                                      "0002000600200081", frozenset({2, 6})))
        _sync_registry(registry, fan)
        for name in ("supply_temperature", "heater_status", "freshbox_recovery_efficiency"):
            self.assertEqual(entries[fan.id + "_" + name].hidden_by, "integration")
        self.assertIsNone(entries[fan.id + "_outdoor_temperature"].hidden_by)
        self.assertTrue(_read_payload(fan, [0xFE, 2, 0x20, 186, 0, 0x81, 1], "00200081"))
        _sync_registry(registry, fan)
        for name in ("supply_temperature", "heater_status", "freshbox_recovery_efficiency"):
            self.assertIsNone(entries[fan.id + "_" + name].hidden_by)

    def test_silent_omissions_hide_never_observed_rows_but_keep_established_entities(self):
        _, fan, _ = _freshbox()
        request = "00020006001F0020002100220081"
        omitted = [2, 1, 6, 0]
        self.assertTrue(_read_payload(fan, omitted, request, frozenset({2, 6})))
        self.assertFalse(fan.unsupported_optional_poll_parameter_ids())
        coordinator = _Coordinator(fan)
        entities = _sensor_entities(fan, coordinator)
        optional = {*PROBES, "heater_status", "freshbox_recovery_efficiency"}
        self.assertFalse(optional & {entity._ecovent_object_id_suffix for entity in entities})
        registry, entries = _registry(fan)
        _register_registry_sync(registry, coordinator)
        for name in optional:
            self.assertEqual(entries[fan.id + "_" + name].hidden_by, "integration")

        reported = list(omitted)
        for param, tenths in zip(range(0x1F, 0x23), (103, 186, 192, 141)):
            reported.extend([0xFE, 2, param, *tenths.to_bytes(2, "little", signed=True)])
        reported.extend([0x81, 1])
        self.assertTrue(_read_payload(fan, reported, request, frozenset({2, 6})))
        for listener in coordinator.listeners:
            listener()
        by_suffix = {entity._ecovent_object_id_suffix: entity for entity in entities}
        self.assertTrue(optional <= by_suffix.keys())
        self.assertEqual(fan.unsupported_optional_poll_parameter_ids(), frozenset())
        for name in optional:
            self.assertIsNone(entries[fan.id + "_" + name].hidden_by)
        count = len(entities)
        for _ in range(8):
            self.assertTrue(_read_payload(fan, omitted, request, frozenset({2, 6})))
            for listener in coordinator.listeners:
                listener()
        self.assertEqual(len(entities), count)
        for name in optional:
            self.assertIsNone(entries[fan.id + "_" + name].hidden_by)
        self.assertIsNone(by_suffix["freshbox_recovery_efficiency"].native_value)

    def test_vento_and_breezy_persisted_probe_entries_survive_unobserved_rows(self):
        for unit_type in ("0100", "1100"):
            with self.subTest(unit_type=unit_type):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type
                fan._id = "DEFAULT_DEVICEID"
                if fan.profile_key == "vento":
                    fan._temperature_probes_detected = True
                registry, entries = _registry(fan)
                _sync_registry(registry, fan)
                for name in PROBES:
                    self.assertIsNone(entries[fan.id + "_" + name].hidden_by)
                self.assertTrue(set(PROBES) <= _entities_by_suffix(fan).keys())

    def test_estimated_efficiency_is_freshbox_only(self):
        from test_a21_modbus import A21ModbusDevice

        devices = [A21ModbusDevice(transport="modbus_tcp", endpoint="192.0.2.1",
                                  name="A21", model="A21")]
        for unit_type in ("0e00", "1100"):
            fan = Fan("192.0.2.1")
            fan.unit_type = unit_type
            fan._temperature_probes_detected = True
            devices.append(fan)
        spec = next(spec for spec in Sensors.SENSOR_SPECS if spec.method == "freshbox_recovery_efficiency")
        for fan in devices:
            with self.subTest(profile=fan.profile_key):
                self.assertFalse(fan.profile_has_entity_requirements(
                    required_params=spec.required_params,
                    required_capabilities=spec.required_capabilities))
                registry, entries = _registry(fan)
                _sync_registry(registry, fan)
                self.assertEqual(entries[fan.id + spec.key].hidden_by, "integration")

    def test_rejected_rows_use_existing_entity_gates_and_recover(self):
        _, fan, _ = _freshbox()
        self.assertTrue(_read_payload(fan, [0xFE, 2, 0x1F, 103, 0], "001F"))
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

    def test_freshbox_efficiency_clamps_and_preserves_unknowns(self):
        _, fan, _ = _freshbox()
        sensor = Sensors.VentoSensor.__new__(Sensors.VentoSensor)
        sensor._fan = fan
        for values in ((None, 18.6, 19.2), (10.3, None, 19.2), (10.3, 18.6, None),
                       (10.3, 18.6, 10.3), (10.3, 18.6, 10.35)):
            fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = values
            self.assertIsNone(sensor.freshbox_recovery_efficiency())
        fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = (16.3, 19.2, 18.0)
        self.assertEqual(sensor.freshbox_recovery_efficiency(), 100.0)
        fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = (10.0, 15.0, 20.0)
        self.assertEqual(sensor.freshbox_recovery_efficiency(), 50.0)
        fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = (10.0, 5.0, 20.0)
        self.assertEqual(sensor.freshbox_recovery_efficiency(), 0.0)

    def test_efficiency_rounds_to_one_decimal(self):
        _, fan, _ = _freshbox()
        sensor = Sensors.VentoSensor.__new__(Sensors.VentoSensor)
        sensor._fan = fan
        fan._outdoor_temperature, fan._supply_temperature, fan._exhaust_in_temperature = (10.0, 11.0, 13.0)
        self.assertEqual(sensor.freshbox_recovery_efficiency(), 33.3)

    def test_vento_speed_mapping_is_unchanged(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0e00"
        for raw, expected in ((1, "low"), (2, "medium"), (3, "high"), (0xFF, "manual")):
            self.assertTrue(fan.parse_response(packet_with_payload([2, raw])))
            self.assertEqual(fan.speed, expected)

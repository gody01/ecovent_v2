"""Behavior tests for the Home Assistant silent-mode fan facade."""

from __future__ import annotations

from enum import IntFlag
from pathlib import Path
import importlib.util
import sys
import types
import unittest

from ecovent_test_helpers import Fan, packet_with_payload


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
PACKAGE_NAME = "ecovent_v2_fan_entity_test"


class _Feature(IntFlag):
    PRESET_MODE = 1
    TURN_OFF = 2
    TURN_ON = 4
    SET_SPEED = 8
    OSCILLATE = 16
    DIRECTION = 32


class _CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class _FakeCoordinator:
    silent_mode_enabled = True
    silent_preset_mode = None

    def set_silent_preset_mode(self, preset_mode):
        self.silent_preset_mode = preset_mode


def _module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_homeassistant_stubs():
    _module("homeassistant")
    _module("homeassistant.components")
    _module(
        "homeassistant.components.fan",
        FanEntity=object,
        FanEntityFeature=_Feature,
    )
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module("homeassistant.core", HomeAssistant=object)
    _module("homeassistant.helpers")
    _module(
        "homeassistant.helpers.device_registry",
        DeviceInfo=lambda **kwargs: kwargs,
    )
    _module(
        "homeassistant.helpers.entity_platform",
        AddEntitiesCallback=object,
        async_get_current_platform=lambda: None,
    )
    _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=_CoordinatorEntity,
    )


def _load_fan_entity_class():
    _install_homeassistant_stubs()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(COMPONENT_PATH)]
    sys.modules[PACKAGE_NAME] = package
    _module(f"{PACKAGE_NAME}.coordinator", EcoVentCoordinator=object)

    module_name = f"{PACKAGE_NAME}.fan"
    spec = importlib.util.spec_from_file_location(
        module_name,
        COMPONENT_PATH / "fan.py",
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = PACKAGE_NAME
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.VentoExpertFan


VentoExpertFan = _load_fan_entity_class()


def _silent_entity(*, speed="manual", man_speed=63):
    fan = Fan("192.0.2.1")
    fan._state = "on"
    fan._speed = speed
    fan._man_speed = man_speed
    fan._airflow = "ventilation"
    fan._supply_speed_low = 30
    fan._exhaust_speed_low = 30
    fan._supply_speed_medium = 50
    fan._exhaust_speed_medium = 50
    fan._supply_speed_high = 63
    fan._exhaust_speed_high = 63
    fan.extra_write_parameters_callback = lambda: {
        "rtc_time": "1e2d13",
        "rtc_date": "1704041a",
    }

    calls = []
    fan.send = lambda data: calls.append(data) or True
    fan.receive = lambda: packet_with_payload([])

    entity = VentoExpertFan.__new__(VentoExpertFan)
    entity._fan = fan
    entity.coordinator = _FakeCoordinator()
    return entity, fan, calls


class SilentFanEntityTest(unittest.TestCase):
    def test_entering_silent_manual_mode_allows_one_audible_mode_write(self):
        entity, fan, calls = _silent_entity(speed="high", man_speed=30)

        entity.set_preset_mode("high")

        self.assertEqual(fan.audible_write_command_count, 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("0302ff44a1", calls[0])
        self.assertIn("fe036f1e2d13", calls[0])

    def test_steady_state_silent_preset_change_writes_only_manual_speed(self):
        entity, fan, calls = _silent_entity(speed="manual", man_speed=63)

        entity.set_preset_mode("medium")

        self.assertEqual(fan.audible_write_command_count, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("034480", calls[0])
        self.assertNotIn("02ff", calls[0])
        self.assertNotIn("fe036f", calls[0])

    def test_silent_preset_uses_fallback_when_device_has_no_setpoints(self):
        entity, fan, calls = _silent_entity(speed="manual", man_speed=63)
        fan._supply_speed_low = None
        fan._exhaust_speed_low = None
        fan._supply_speed_medium = None
        fan._exhaust_speed_medium = None
        fan._supply_speed_high = None
        fan._exhaust_speed_high = None

        entity.set_preset_mode("medium")

        self.assertEqual(fan.audible_write_command_count, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("0344a9", calls[0])
        self.assertNotIn("02ff", calls[0])
        self.assertNotIn("fe036f", calls[0])
        self.assertEqual(entity.coordinator.silent_preset_mode, "medium")

    def test_entering_manual_percentage_allows_one_audible_mode_write(self):
        entity, fan, calls = _silent_entity(speed="high", man_speed=30)

        entity.set_percentage(63)

        self.assertEqual(fan.audible_write_command_count, 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("0302ff44a1", calls[0])
        self.assertIn("fe036f1e2d13", calls[0])
        self.assertEqual(entity.coordinator.silent_preset_mode, "manual")

    def test_steady_state_silent_percentage_writes_only_manual_speed(self):
        entity, fan, calls = _silent_entity(speed="manual", man_speed=63)

        entity.set_percentage(50)

        self.assertEqual(fan.audible_write_command_count, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("034480", calls[0])
        self.assertNotIn("02ff", calls[0])
        self.assertNotIn("fe036f", calls[0])
        self.assertEqual(entity.coordinator.silent_preset_mode, "manual")

    def test_steady_state_silent_zero_percentage_keeps_manual_mode_on(self):
        entity, fan, calls = _silent_entity(speed="manual", man_speed=11)

        entity.set_percentage(0)

        self.assertEqual(fan.audible_write_command_count, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("034400", calls[0])
        self.assertNotIn("02ff", calls[0])
        self.assertNotIn("fe036f", calls[0])
        self.assertEqual(entity.coordinator.silent_preset_mode, "manual")

    def test_steady_state_silent_airflow_change_is_allowed_but_audible(self):
        entity, fan, calls = _silent_entity(speed="manual", man_speed=63)

        entity.set_airflow_mode("air_supply")

        self.assertEqual(fan.audible_write_command_count, 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("03b702", calls[0])
        self.assertNotIn("fe036f", calls[0])

    def test_missing_airflow_reports_unknown_direction_and_oscillation(self):
        entity, fan, _calls = _silent_entity(speed="low", man_speed=63)
        fan._airflow = None

        self.assertIsNone(entity.current_direction)
        self.assertIsNone(entity.oscillating)

    def test_unmapped_airflow_reports_unknown_direction_and_oscillation(self):
        entity, fan, _calls = _silent_entity(speed="low", man_speed=63)
        fan._airflow = "Unknown airflow 3"

        self.assertIsNone(entity.current_direction)
        self.assertIsNone(entity.oscillating)

    def test_breezy_extract_airflow_reports_no_direction_non_oscillating(self):
        entity, fan, _calls = _silent_entity(speed="low", man_speed=63)
        fan._airflow = "extract"

        self.assertIsNone(entity.current_direction)
        self.assertFalse(entity.oscillating)

    def test_missing_preset_setpoints_do_not_report_manual_speed_percentage(self):
        entity, fan, _calls = _silent_entity(speed="low", man_speed=63)
        fan._airflow = "ventilation"
        fan._supply_speed_low = None
        fan._exhaust_speed_low = None

        self.assertIsNone(entity.percentage)

    def test_manual_mode_still_reports_manual_speed_percentage(self):
        entity, _fan, _calls = _silent_entity(speed="manual", man_speed=63)

        self.assertEqual(entity.percentage, 63)


if __name__ == "__main__":
    unittest.main()

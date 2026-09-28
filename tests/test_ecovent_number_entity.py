"""Runtime tests for profile-specific EcoVent Number metadata."""

from __future__ import annotations

from pathlib import Path
import asyncio
import importlib.util
import sys
import types
import unittest

from ecovent_test_helpers import Fan


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
PACKAGE_NAME = "ecovent_v2_number_entity_test"
DOMAIN = "ecovent_v2"


class _CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class _NumberDeviceClass:
    TEMPERATURE = "temperature"


class _NumberMode:
    AUTO = "auto"
    BOX = "box"


class _EntityCategory:
    CONFIG = "config"


class _UnitOfTemperature:
    CELSIUS = "°C"


def _module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_number_entity_class():
    _module("homeassistant")
    _module("homeassistant.components")
    _module(
        "homeassistant.components.number",
        NumberDeviceClass=_NumberDeviceClass,
        NumberEntity=type("NumberEntity", (), {}),
        NumberMode=_NumberMode,
    )
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module(
        "homeassistant.const",
        EntityCategory=_EntityCategory,
        PERCENTAGE="%",
        UnitOfTemperature=_UnitOfTemperature,
    )
    _module("homeassistant.core", HomeAssistant=object)
    _module("homeassistant.helpers")
    _module(
        "homeassistant.helpers.device_registry",
        DeviceInfo=lambda **kwargs: kwargs,
    )
    _module(
        "homeassistant.helpers.entity_platform",
        AddEntitiesCallback=object,
    )
    _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=_CoordinatorEntity,
    )

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(COMPONENT_PATH)]
    sys.modules[PACKAGE_NAME] = package
    _module(f"{PACKAGE_NAME}.const", DOMAIN=DOMAIN)
    _module(f"{PACKAGE_NAME}.coordinator", EcoVentCoordinator=object)
    _module(f"{PACKAGE_NAME}.ecoventv2", Fan=Fan)
    _module(
        f"{PACKAGE_NAME}.entity_naming",
        StableObjectIdMixin=type("StableObjectIdMixin", (), {}),
        clean_object_id_suffix=lambda value: value,
    )

    module_name = f"{PACKAGE_NAME}.number"
    spec = importlib.util.spec_from_file_location(
        module_name, COMPONENT_PATH / "number.py"
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = PACKAGE_NAME
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.VentoNumber


VentoNumber = _load_number_entity_class()


class _Config:
    entry_id = "entry"


class _Coordinator:
    def __init__(self, fan):
        self._fan = fan


def _entity(fan, method, *, minimum=1, maximum=999, step=1):
    fan._id = "DEVICE-000000001"
    fan._name = "EcoVent"
    hass = types.SimpleNamespace(
        data={DOMAIN: {_Config.entry_id: _Coordinator(fan)}}
    )
    return VentoNumber(
        hass,
        _Config(),
        method=method,
        native_min_value=minimum,
        native_max_value=maximum,
        native_step=step,
    )


class NumberEntityMetadataTest(unittest.TestCase):
    def test_profile_number_bounds_and_step_reach_entity(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"
        fan._filter_timer_setpoint = "70 d"
        timer = _entity(fan, "filter_timer_setpoint")
        self.assertEqual(timer._attr_native_min_value, 70)
        self.assertEqual(timer._attr_native_max_value, 365)
        self.assertEqual(timer._attr_native_step, 5)

        fan._supply_speed_low = 0
        speed = _entity(fan, "supply_speed_low")
        self.assertEqual(speed._attr_native_min_value, 0)
        self.assertEqual(speed._attr_native_max_value, 100)

        fan.unit_type = "1100"
        fan._man_speed = 10
        manual = _entity(fan, "man_speed")
        self.assertEqual(manual._attr_native_min_value, 10)
        self.assertEqual(manual._attr_native_max_value, 100)

        fan.unit_type = "0d00"
        fan._temperature_treshold = "18"
        temperature = _entity(fan, "temperature_treshold")
        self.assertEqual(temperature._attr_native_min_value, 18)
        self.assertEqual(temperature._attr_native_max_value, 36)

    def test_three_speed_numbers_are_not_created_without_profile_capability(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0d00"
        fan._id = "DEVICE-000000001"
        fan._name = "EcoVent"
        hass = types.SimpleNamespace(
            data={DOMAIN: {_Config.entry_id: _Coordinator(fan)}}
        )
        entities = []
        number_module = sys.modules[f"{PACKAGE_NAME}.number"]

        asyncio.run(
            number_module.async_setup_entry(
                hass, _Config(), entities.extend
            )
        )

        speed_parameters = {
            "supply_speed_low",
            "exhaust_speed_low",
            "supply_speed_medium",
            "exhaust_speed_medium",
            "supply_speed_high",
            "exhaust_speed_high",
        }
        self.assertFalse(fan.profile_supports_capability("three_speed_setpoints"))
        self.assertFalse(
            speed_parameters & {entity._func for entity in entities}
        )


if __name__ == "__main__":
    unittest.main()

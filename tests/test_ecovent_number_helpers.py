"""Regression tests for EcoVent number setpoint helpers."""

import ast
import unittest

from ecovent_test_helpers import COMPONENT_PATH, Fan  # noqa: F401  Sets module path.
from number_helpers import encode_raw_number, encode_speed_percent


NUMBER_PATH = COMPONENT_PATH / "number.py"


def _number_spec_calls():
    tree = ast.parse(NUMBER_PATH.read_text())
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "NumberSpec"
    ]


def _constant_arg(call, index):
    return call.args[index].value


def _keyword_value(call, name):
    for keyword in call.keywords:
        if keyword.arg == name:
            return ast.literal_eval(keyword.value)
    return None


class NumberHelperTest(unittest.TestCase):
    def test_speed_percent_encoder_respects_profile_scale(self):
        self.assertEqual(encode_speed_percent(50, "byte"), "80")
        self.assertEqual(encode_speed_percent(50, "percent"), "32")

    def test_raw_number_encoder_keeps_little_endian_multibyte_values(self):
        self.assertEqual(encode_raw_number(45), "2d")
        self.assertEqual(encode_raw_number(365, 2), "6d01")

    def test_manual_speed_number_is_visible_configuration_entity(self):
        manual_specs = [
            call
            for call in _number_spec_calls()
            if _constant_arg(call, 1) == "man_speed"
        ]

        self.assertEqual(len(manual_specs), 1)
        self.assertEqual(_constant_arg(manual_specs[0], 0), "Speed manual")
        self.assertIs(_constant_arg(manual_specs[0], 3), True)
        self.assertEqual(
            _keyword_value(manual_specs[0], "write_mode"),
            "manual_speed_percent",
        )

    def test_preset_speed_numbers_are_disabled_by_default(self):
        speed_specs = [
            call
            for call in _number_spec_calls()
            if _constant_arg(call, 1).startswith(("supply_speed", "exhaust_speed"))
        ]

        self.assertEqual(len(speed_specs), 16)
        self.assertTrue(all(_constant_arg(call, 3) is False for call in speed_specs))
        self.assertTrue(
            all(
                _keyword_value(call, "write_mode") == "speed_percent"
                for call in speed_specs
            )
        )

    def test_speed_setpoint_capabilities_split_three_and_five_speed_profiles(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.supports_capability("three_speed_setpoints"))
        self.assertFalse(fan.supports_capability("five_speed_setpoints"))
        self.assertTrue(
            fan.supports_entity(
                required_params=("supply_speed_low",),
                required_capabilities=("three_speed_setpoints",),
            )
        )

        fan.unit_type = "0200"
        self.assertEqual(fan.profile_key, "freshbox")
        self.assertFalse(fan.supports_capability("three_speed_setpoints"))
        self.assertTrue(fan.supports_capability("five_speed_setpoints"))
        self.assertTrue(
            fan.supports_entity(
                required_params=("supply_speed_5",),
                required_capabilities=("five_speed_setpoints",),
            )
        )

        fan.unit_type = "0600"
        self.assertEqual(fan.profile_key, "extract_fan")
        self.assertFalse(fan.supports_capability("three_speed_setpoints"))
        self.assertFalse(fan.supports_capability("five_speed_setpoints"))
        self.assertTrue(
            fan.supports_entity(
                required_params=("max_speed_setpoint",),
                required_capabilities=("speed_setpoints",),
            )
        )


if __name__ == "__main__":
    unittest.main()

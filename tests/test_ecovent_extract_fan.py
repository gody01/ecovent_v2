"""Regression tests for extract-fan profile behavior."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload


class ExtractFanCapabilityTest(unittest.TestCase):
    def test_parse_response_uses_extract_fan_profile(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [
                        0xFE,
                        0x02,
                        0xB9,
                        0x06,
                        0x00,
                        0x01,
                        0x01,
                        0x02,
                        0x01,
                        0x03,
                        0x01,
                        0xFE,
                        0x02,
                        0x04,
                        0xB0,
                        0x04,
                        0x18,
                        0x64,
                        0x2E,
                        0x37,
                        0x31,
                        0x16,
                    ]
                )
            )
        )

        self.assertEqual(fan.profile_key, "extract_fan")
        self.assertTrue(fan.uses_operating_mode_presets)
        self.assertFalse(fan.supports_direction)
        self.assertEqual(fan.unit_type, Fan.device_models[0x0600].display_name)
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan.battery_status, "normal")
        self.assertEqual(fan.speed, "all_day")
        self.assertEqual(fan.fan1_speed, "1200")
        self.assertEqual(fan.max_speed_setpoint, 100)
        self.assertEqual(fan.humidity, "55")
        self.assertEqual(fan.temperature, "22")
        self.assertNotIn(0x0002, fan.unknown_params)

    def test_entity_capabilities_follow_active_profile(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.supports_entity(
                required_params=("fan1_speed", "fan2_speed"),
            )
        )
        self.assertFalse(
            fan.supports_entity(required_capabilities=("speed_setpoints",))
        )

        fan.unit_type = "0600"
        self.assertTrue(
            fan.supports_entity(
                required_params=("max_speed_setpoint",),
                required_capabilities=("speed_setpoints",),
            )
        )
        self.assertFalse(
            fan.supports_entity(required_params=("fan2_speed",))
        )

        fan.unit_type = "1400"
        self.assertTrue(
            fan.supports_entity(
                required_params=("co2",),
                required_capabilities=("co2",),
            )
        )
        self.assertTrue(
            fan.supports_entity(
                required_params=("screen_brightness",),
                required_capabilities=("breezy_screen",),
            )
        )
        self.assertFalse(
            fan.supports_entity(required_params=("analogV",))
        )

    def test_runtime_capability_probe_requires_beeper_off_to_survive_command(self):
        fan = Fan("192.0.2.1")
        fan.beeper = "02"
        fan.state = "01"
        fan.speed = "01"
        fan.beeper_probe_settle_seconds = 0
        calls = []

        def set_param(param, value):
            calls.append(("set", param, value))
            setattr(fan, f"_{param}", value)
            return True

        def get_param(param):
            calls.append(("get", param))
            return True

        fan.set_param = set_param
        fan.get_param = get_param

        fan.detect_runtime_capabilities()

        self.assertTrue(fan.supports_capability("beeper_control"))
        self.assertEqual(fan.beeper, "silent")
        self.assertEqual(
            calls,
            [
                ("set", "beeper", "off"),
                ("set", "state", "on"),
                ("get", "beeper"),
                ("get", "beeper"),
                ("get", "beeper"),
                ("set", "beeper", "silent"),
                ("get", "beeper"),
            ],
        )

    def test_runtime_capability_probe_rejects_beeper_turning_on_after_command(self):
        fan = Fan("192.0.2.1")
        fan.beeper = "01"
        fan.state = "01"
        fan.speed = "01"
        fan.beeper_probe_settle_seconds = 0

        def set_param(param, value):
            if param == "beeper":
                fan._beeper = value
            if param == "state":
                fan._beeper = "on"
            return True

        def get_param(param):
            return True

        fan.set_param = set_param
        fan.get_param = get_param

        fan.detect_runtime_capabilities()

        self.assertFalse(fan.supports_capability("beeper_control"))

    def test_runtime_capability_probe_rejects_delayed_beeper_reset(self):
        fan = Fan("192.0.2.1")
        fan.beeper = "01"
        fan.state = "01"
        fan.speed = "01"
        fan.beeper_probe_settle_seconds = 0
        reads = 0

        def set_param(param, value):
            if param == "beeper":
                fan._beeper = value
            return True

        def get_param(param):
            nonlocal reads
            reads += 1
            if param == "beeper" and reads == 2:
                fan._beeper = "on"
            return True

        fan.set_param = set_param
        fan.get_param = get_param

        fan.detect_runtime_capabilities()

        self.assertFalse(fan.supports_capability("beeper_control"))

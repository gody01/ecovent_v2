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

    def test_extract_fan_three_byte_durations_are_total_seconds(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"

        fan.boost_timer_countdown = "100e00"
        fan.silent_mode_start_time = "4d0e00"
        fan.silent_mode_end_time = "805101"
        fan.rtc_time = "4d0e00"

        self.assertEqual(fan.boost_timer_countdown, "1h 0m 0s ")
        self.assertEqual(fan.silent_mode_start_time, "1h 1m 1s ")
        self.assertEqual(fan.silent_mode_end_time, "24h 0m 0s ")
        self.assertEqual(fan.rtc_time, "01:01:01")

        for attribute in (
            "boost_timer_countdown",
            "silent_mode_start_time",
            "silent_mode_end_time",
        ):
            with self.subTest(attribute=attribute):
                with self.assertRaisesRegex(ValueError, "duration"):
                    setattr(fan, attribute, "905f01")

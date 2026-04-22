"""Regression tests for EcoVent profile response parsing."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload


class ProfileParseTest(unittest.TestCase):
    def test_parse_response_names_shared_oxxify_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x0E, 0x00])))
        self.assertEqual(fan.unit_type, Fan.device_models[0x0E00].display_name)

    def test_parse_response_names_breezy_freshpoint_relabels(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x14, 0x00]))
        )
        self.assertEqual(fan.unit_type, Fan.device_models[0x1400].display_name)
        self.assertEqual(fan.profile_key, "breezy")

    def test_parse_response_uses_breezy_freshpoint_profile(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [
                        0xFE,
                        0x02,
                        0xB9,
                        0x14,
                        0x00,
                        0x02,
                        0x04,
                        0x3A,
                        0x50,
                        0x3B,
                        0x45,
                        0x44,
                        0x55,
                        0xFE,
                        0x02,
                        0x1A,
                        0xE8,
                        0x03,
                        0xFE,
                        0x02,
                        0x1F,
                        0xE1,
                        0x00,
                        0xFE,
                        0x02,
                        0x20,
                        0x7F,
                        0xFF,
                        0xFE,
                        0x02,
                        0x27,
                        0xDC,
                        0x05,
                        0xFE,
                        0x05,
                        0x84,
                        0x01,
                        0x00,
                        0x00,
                        0x00,
                        0x01,
                        0xFF,
                        0x01,
                        0x29,
                        0x56,
                        0xFF,
                        0x03,
                        0x15,
                        0x01,
                        0xFF,
                        0x03,
                        0xFE,
                        0x02,
                        0x1F,
                        0xC8,
                        0x00,
                        0xFF,
                        0x03,
                        0xFE,
                        0x02,
                        0x20,
                        0x2C,
                        0x01,
                        0xFF,
                        0x04,
                        0x00,
                        0x64,
                        0xFF,
                        0x04,
                        0x02,
                        0x01,
                        0xFF,
                        0x04,
                        0x03,
                        0x02,
                        0xFF,
                        0x04,
                        0x04,
                        0x01,
                        0xFF,
                        0x04,
                        0x05,
                        0x02,
                        0xFF,
                        0x04,
                        0x06,
                        0x01,
                        0xFF,
                        0x04,
                        0x07,
                        0x02,
                        0xFF,
                        0x04,
                        0xFE,
                        0x02,
                        0x08,
                        0x1E,
                        0x16,
                        0xFF,
                        0x04,
                        0xFE,
                        0x02,
                        0x09,
                        0x00,
                        0x07,
                    ]
                )
            )
        )

        self.assertEqual(fan.profile_key, "breezy")
        self.assertEqual(fan.speed, "speed_4")
        self.assertEqual(fan.supply_speed_low, 80)
        self.assertEqual(fan.exhaust_speed_low, 69)
        self.assertEqual(fan.man_speed, 85)
        self.assertEqual(fan.co2_treshold, 1000)
        self.assertEqual(fan.outdoor_temperature, 22.5)
        self.assertEqual(fan.supply_temperature, -12.9)
        self.assertEqual(fan.co2, 1500)
        self.assertEqual(
            fan.air_quality_status,
            "humidity:over_setpoint, co2:normal, reserved_1:normal, reserved_2:normal, voc:over_setpoint",
        )
        self.assertEqual(fan.recovery_efficiency, 86)
        self.assertEqual(fan.voc_sensor_state, "on")
        self.assertEqual(fan.voc_treshold, 200)
        self.assertEqual(fan.voc, 300)
        self.assertEqual(fan.screen_brightness, 100)
        self.assertEqual(fan.screen_backlight_mode, "manual")
        self.assertEqual(fan.screen_temperature_source, "extract_air")
        self.assertEqual(fan.screen_air_quality_source, "co2")
        self.assertEqual(fan.screen_display_mode, "temperature_humidity")
        self.assertEqual(fan.screen_standby_time_state, "on")
        self.assertEqual(fan.screen_display_state, "off_interval")
        self.assertEqual(fan.screen_off_start_time, "22:30")
        self.assertEqual(fan.screen_off_end_time, "07:00")

    def test_vento_profile_keeps_byte_scaled_speed_values(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0x3A, 0x50])))
        self.assertEqual(fan.profile_key, "vento")
        self.assertEqual(fan.supply_speed_low, 31)

    def test_beeper_value_follows_active_profile_enum(self):
        fan = Fan("192.0.2.1")
        fan.beeper = "02"
        self.assertEqual(fan.beeper, "silent")

        fan.unit_type = "1400"
        fan.beeper = "02"
        self.assertEqual(fan.beeper, "toggle")

    def test_parse_response_names_newer_atmo_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x1A, 0x00]))
        )
        self.assertEqual(fan.unit_type, Fan.device_models[0x1A00].display_name)

    def test_parse_response_names_twinfresh_atmo_160_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x1C, 0x00]))
        )
        self.assertEqual(fan.unit_type, Fan.device_models[0x1C00].display_name)

    def test_parse_response_names_freshbox_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x02, 0x00]))
        )
        self.assertEqual(fan.unit_type, Fan.device_models[0x0200].display_name)
        self.assertEqual(fan.profile_key, "freshbox")

    def test_parse_response_uses_arc_smart_profile(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [
                        0xFE,
                        0x02,
                        0xB9,
                        0x0D,
                        0x00,
                        0x06,
                        0x01,
                        0x07,
                        0x00,
                        0x0F,
                        0x02,
                        0x19,
                        0x2D,
                        0xFE,
                        0x02,
                        0x21,
                        0xE1,
                        0x00,
                        0xFE,
                        0x02,
                        0x24,
                        0xE4,
                        0x0C,
                        0x25,
                        0x32,
                        0xFE,
                        0x02,
                        0x4B,
                        0xB0,
                        0x04,
                        0x83,
                        0x01,
                        0xFF,
                        0x03,
                        0x04,
                        0x01,
                        0xFF,
                        0x03,
                        0x0D,
                        0x01,
                        0xFF,
                        0x03,
                        0x0E,
                        0x01,
                        0xFF,
                        0x03,
                        0x0F,
                        0x00,
                        0xFF,
                        0x03,
                        0x12,
                        0x01,
                        0xFF,
                        0x03,
                        0x13,
                        0x01,
                        0xFF,
                        0x03,
                        0x14,
                        0x00,
                        0xFF,
                        0x03,
                        0x15,
                        0x02,
                        0xFF,
                        0x03,
                        0x16,
                        0x01,
                        0xFF,
                        0x03,
                        0x17,
                        0x00,
                        0xFF,
                        0x03,
                        0xFE,
                        0x03,
                        0x18,
                        0x00,
                        0x1E,
                        0x16,
                        0xFF,
                        0x03,
                        0xFE,
                        0x03,
                        0x19,
                        0x00,
                        0x00,
                        0x07,
                        0xFF,
                        0x03,
                        0x1A,
                        0x04,
                        0xFF,
                        0x03,
                        0x1B,
                        0x02,
                        0xFF,
                        0x03,
                        0x1C,
                        0x05,
                        0xFF,
                        0x03,
                        0x1D,
                        0x03,
                        0xFF,
                        0x03,
                        0x1E,
                        0x01,
                        0xFF,
                        0x03,
                        0xFE,
                        0x02,
                        0x1F,
                        0xC8,
                        0x00,
                        0xFF,
                        0x03,
                        0xFE,
                        0x02,
                        0x20,
                        0x2C,
                        0x01,
                        0xFF,
                        0x03,
                        0x23,
                        0x01,
                        0xFF,
                        0x03,
                        0x24,
                        0x01,
                        0xFF,
                        0x03,
                        0x25,
                        0x18,
                        0xFF,
                        0x03,
                        0x2F,
                        0x04,
                    ]
                )
            )
        )

        self.assertEqual(fan.profile_key, "arc")
        self.assertEqual(fan.unit_type, Fan.device_models[0x0D00].display_name)
        self.assertEqual(fan.fan_preset_modes, [])
        self.assertFalse(fan.supports_percentage_control)
        self.assertFalse(fan.supports_parameter("state"))
        self.assertFalse(fan.supports_parameter("speed"))
        self.assertEqual(fan.boost_status, "on")
        self.assertEqual(fan.timer_status, "off")
        self.assertEqual(fan.humidity_sensor_state, "manual")
        self.assertEqual(fan.humidity_treshold, "45")
        self.assertEqual(fan.room_temperature, 22.5)
        self.assertEqual(fan.battery_voltage, "3300 mV")
        self.assertEqual(fan.humidity, "50")
        self.assertEqual(fan.fan1_speed, "1200")
        self.assertEqual(fan.low_battery_status, "on")
        self.assertEqual(fan.humidity_status, "on")
        self.assertEqual(fan.all_day_mode, "on")
        self.assertEqual(fan.light_status, "on")
        self.assertEqual(fan.motion_status, "off")
        self.assertEqual(fan.air_quality_status, "on")
        self.assertEqual(fan.light_sensor_state, "on")
        self.assertEqual(fan.motion_sensor_state, "off")
        self.assertEqual(fan.air_quality_sensor_state, "manual")
        self.assertEqual(fan.interval_ventilation_state, "on")
        self.assertEqual(fan.silent_mode_state, "off")
        self.assertEqual(fan.silent_mode_start_time, "22h 30m 0s ")
        self.assertEqual(fan.silent_mode_end_time, "7h 0m 0s ")
        self.assertEqual(fan.humidity_airflow, "90_m3h")
        self.assertEqual(fan.motion_light_airflow, "40_m3h")
        self.assertEqual(fan.air_quality_airflow, "115_m3h")
        self.assertEqual(fan.interval_ventilation_airflow, "60_m3h")
        self.assertEqual(fan.all_day_airflow, "20_m3h")
        self.assertEqual(fan.air_quality_treshold, 200)
        self.assertEqual(fan.air_quality, 300)
        self.assertEqual(fan.temperature_status, "on")
        self.assertEqual(fan.temperature_sensor_state, "on")
        self.assertEqual(fan.temperature_treshold, "24")
        self.assertEqual(fan.temperature_airflow, "90_m3h")
        self.assertEqual(
            fan.parameter_options("air_quality_sensor_state"),
            ["off", "automatic", "manual"],
        )
        self.assertEqual(
            fan.parameter_options("humidity_airflow"),
            ["60_m3h", "90_m3h", "115_m3h"],
        )
        self.assertEqual(
            fan.parameter_options("interval_ventilation_airflow"),
            ["20_m3h", "40_m3h", "60_m3h"],
        )

    def test_parse_response_uses_freshbox_profile(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [
                        0xFE,
                        0x02,
                        0xB9,
                        0x02,
                        0x00,
                        0x02,
                        0x05,
                        0x3A,
                        0x28,
                        0x3B,
                        0x32,
                        0x40,
                        0x46,
                        0x41,
                        0x50,
                        0x42,
                        0x5A,
                        0x43,
                        0x64,
                        0xFE,
                        0x02,
                        0x1F,
                        0xE1,
                        0x00,
                        0x32,
                        0x01,
                        0x33,
                        0x00,
                        0x93,
                        0x01,
                        0xA1,
                        0x00,
                        0xB6,
                        0x01,
                    ]
                )
            )
        )

        self.assertEqual(fan.profile_key, "freshbox")
        self.assertEqual(fan.speed, "speed_5")
        self.assertEqual(
            fan.fan_preset_modes,
            ["off", "speed_1", "speed_2", "speed_3", "speed_4", "speed_5"],
        )
        self.assertFalse(fan.supports_percentage_control)
        self.assertEqual(
            fan.parameter_options("speed"),
            ["speed_1", "speed_2", "speed_3", "speed_4", "speed_5"],
        )
        self.assertEqual(fan.supply_speed_low, 40)
        self.assertEqual(fan.exhaust_speed_low, 50)
        self.assertEqual(fan.supply_speed_4, 70)
        self.assertEqual(fan.exhaust_speed_4, 80)
        self.assertEqual(fan.supply_speed_5, 90)
        self.assertEqual(fan.exhaust_speed_5, 100)
        self.assertEqual(fan.outdoor_temperature, 22.5)
        self.assertEqual(fan.boost_switch_status, "on")
        self.assertEqual(fan.fire_alarm_status, "off")
        self.assertEqual(fan.wifi_module_status, "on")
        self.assertEqual(fan.wifi_connection_status, "off")
        self.assertEqual(fan.heater_blowing_status, "on")
        self.assertEqual(fan.preset_speed_percent("speed_5"), 95)
        self.assertEqual(fan.preset_speed_percent("speed_1"), 45)

"""Regression tests for the vendored EcoVent V2 protocol client."""

from pathlib import Path
import importlib.util
import json
import socket
import sys
import unittest
from unittest.mock import patch


COMPONENT_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
MODULE_PATH = COMPONENT_PATH / "ecoventv2.py"
PROTOCOL_REFERENCE_PATH = COMPONENT_PATH.parents[1] / "protocol.md"
sys.path.insert(0, str(COMPONENT_PATH))
SPEC = importlib.util.spec_from_file_location("vendored_ecoventv2", MODULE_PATH)
ecoventv2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ecoventv2)
Fan = ecoventv2.Fan


def packet_with_payload(payload):
    body = (
        bytes([0x02, 0x10]) + b"DEFAULT_DEVICEID" + bytes([0x00, 0x06]) + bytes(payload)
    )
    checksum = sum(body) & 0xFFFF
    return b"\xfd\xfd" + body + checksum.to_bytes(2, byteorder="little")


class ParseResponseTest(unittest.TestCase):
    def test_entity_platforms_do_not_branch_on_profile_names(self):
        for filename in (
            "binary_sensor.py",
            "number.py",
            "select.py",
            "sensor.py",
            "switch.py",
        ):
            source = (COMPONENT_PATH / filename).read_text()
            self.assertNotIn('profile_key == "extract_fan"', source)
            self.assertNotIn('profile_key != "extract_fan"', source)
            self.assertNotIn('profile_key == "breezy"', source)
            self.assertNotIn('profile_key != "breezy"', source)

    def test_entity_platforms_keep_model_names_out_of_capabilities(self):
        for filename in (
            "binary_sensor.py",
            "ecoventv2.py",
            "fan.py",
            "number.py",
            "sensor.py",
            "switch.py",
        ):
            source = (COMPONENT_PATH / filename).read_text()
            self.assertNotIn("smart_", source)
            self.assertNotIn("Smart Wi-Fi", source)
            self.assertNotIn("dual_fan_speed", source)

    def test_fan_preset_labels_and_icons_cover_all_profiles(self):
        strings = json.loads((COMPONENT_PATH / "strings.json").read_text())
        icons = json.loads((COMPONENT_PATH / "icons.json").read_text())

        labels = strings["entity"]["fan"]["vent"]["state_attributes"][
            "preset_mode"
        ]["state"]
        preset_icons = icons["entity"]["fan"]["vent"]["state_attributes"][
            "preset_mode"
        ]["state"]

        expected_modes = {
            mode
            for profile in Fan.device_profiles.values()
            for mode in profile.preset_modes
        }
        for mode in expected_modes:
            self.assertIn(mode, labels)
            self.assertIn(mode, preset_icons)

    def test_unit_type_metadata_selects_device_profiles(self):
        self.assertEqual(
            Fan.device_models[0x1A00].name,
            "TwinFresh Atmo / newer Blauberg Vento",
        )
        self.assertEqual(Fan.device_models[0x1A00].profile_key, "vento")
        self.assertEqual(
            Fan.device_models[0x0E00].display_name,
            "TwinFresh Style Wifi V.2 / Oxxify smart 50",
        )
        self.assertEqual(
            Fan.device_models[0x1100].display_name,
            "Breezy 160 / Freshpoint 160 / Vents Breezy 160-E",
        )
        self.assertEqual(Fan.device_models[0x1100].profile_key, "breezy")
        self.assertEqual(
            Fan.device_models[0x1400].display_name,
            "Breezy Eco 160 / Freshpoint Eco 160",
        )
        self.assertEqual(Fan.device_models[0x1400].profile_key, "breezy")
        self.assertEqual(
            Fan.device_models[0x1600].display_name,
            "Breezy 200 / Freshpoint 200",
        )
        self.assertEqual(
            Fan.device_models[0x1800].display_name,
            "Breezy Eco 200 / Freshpoint Eco 200",
        )
        self.assertEqual(Fan.device_models[0x1C00].name, "TwinFresh Atmo 160")
        self.assertEqual(Fan.device_models[0x1C00].profile_key, "vento")
        self.assertEqual(
            Fan.device_models[0x1B00].display_name,
            "Vento inHome S11 W / TwinFresh Atmo 100",
        )
        self.assertEqual(Fan.device_models[0x1B00].profile_key, "vento")
        self.assertEqual(Fan.device_models[0x0600].profile_key, "extract_fan")
        self.assertEqual(
            Fan.unit_types[0x0600],
            "Blauberg Smart Wi-Fi extract fan",
        )

    def test_unit_type_metadata_keeps_source_documents_with_models(self):
        self.assertIn(
            "https://blaubergventilatoren.net/download/vento-inhome-manual-14758.pdf",
            Fan.device_models[0x0300].source_documents,
        )
        self.assertIn(
            "https://ventilation-system.com/download/twinfresh-style-wi-fi-manual-19765.pdf",
            Fan.device_models[0x0E00].source_documents,
        )
        self.assertIn(
            "https://ventilation-system.com/download/twinfresh-style-wi-fi-mini-manual-19765.pdf",
            Fan.device_models[0x1C00].source_documents,
        )
        self.assertEqual(
            Fan.device_models[0x1400].source_documents,
            (
                "https://ventilation-system.com/download/breezy-eco-manual-21433.pdf",
                "https://blaubergventilatoren.net/download/freshpoint-manual-16999.pdf",
            ),
        )
        self.assertEqual(
            Fan.device_models[0x0600].source_documents,
            (
                "https://blaubergventilatoren.net/download/smart-wi-fi-manual-8533.pdf",
            ),
        )
        self.assertEqual(Fan.device_models[0x0200].name, "Freshbox 100 WiFi")
        self.assertEqual(Fan.device_models[0x0200].profile_key, "freshbox")
        self.assertEqual(
            Fan.device_models[0x0200].source_documents,
            (
                "https://blaubergventilatoren.net/download/freshbox-100-wifi-datasheet-7508.pdf",
            ),
        )

    def test_protocol_reference_documents_extract_fan_param_map(self):
        reference = PROTOCOL_REFERENCE_PATH.read_text()
        params = {
            **Fan.extract_fan_params,
            **Fan.extract_fan_write_params,
        }

        for param_id, (field, _values) in sorted(params.items()):
            with self.subTest(param_id=param_id, field=field):
                self.assertIn(f"| 0x{param_id:04X} | `{field}` |", reference)

    def test_protocol_reference_documents_breezy_feature_param_map(self):
        reference = PROTOCOL_REFERENCE_PATH.read_text()
        feature_param_ids = (
            0x0011,
            0x001A,
            0x001F,
            0x0020,
            0x0021,
            0x0022,
            0x0027,
            0x0068,
            0x007F,
            0x0081,
            0x0084,
            0x0129,
            0x0306,
            0x030B,
            0x0315,
            0x031F,
            0x0320,
            0x0400,
            0x0401,
            0x0402,
            0x0403,
            0x0404,
            0x0405,
            0x0406,
            0x0407,
            0x0408,
            0x0409,
        )

        for param_id in feature_param_ids:
            field = Fan.breezy_params[param_id][0]
            with self.subTest(param_id=param_id, field=field):
                self.assertIn(f"| 0x{param_id:04X} | `{field}` |", reference)

    def test_parse_response_names_shared_oxxify_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x0E, 0x00])))
        self.assertEqual(fan.unit_type, "TwinFresh Style Wifi V.2 / Oxxify smart 50")

    def test_parse_response_names_breezy_freshpoint_relabels(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x14, 0x00]))
        )
        self.assertEqual(fan.unit_type, "Breezy Eco 160 / Freshpoint Eco 160")
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
        self.assertEqual(fan.unit_type, "TwinFresh Atmo / newer Blauberg Vento")

    def test_parse_response_names_twinfresh_atmo_160_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x1C, 0x00]))
        )
        self.assertEqual(fan.unit_type, "TwinFresh Atmo 160")

    def test_parse_response_names_freshbox_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x02, 0x00]))
        )
        self.assertEqual(fan.unit_type, "Freshbox 100 WiFi")
        self.assertEqual(fan.profile_key, "freshbox")

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
        self.assertEqual(fan.unit_type, "Blauberg Smart Wi-Fi extract fan")
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

    def test_parse_response_skips_unknown_parameter_ids(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFF, 0x12, 0x34, 0xAB, 0x01, 0x01])
            )
        )
        self.assertEqual(fan.unknown_params, {0x1234: "ab"})
        self.assertEqual(fan.state, "on")

    def test_parse_response_rejects_bad_header_and_checksum(self):
        fan = Fan("192.0.2.1")
        good_packet = packet_with_payload([0x01, 0x01])
        bad_header = b"\x00\x00" + good_packet[2:]
        bad_checksum = good_packet[:-1] + bytes([good_packet[-1] ^ 0xFF])

        self.assertFalse(fan.parse_response(bad_header))
        self.assertIsNone(fan.state)
        self.assertFalse(fan.parse_response(bad_checksum))
        self.assertIsNone(fan.state)

    def test_parse_response_rejects_short_packet(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(b"\xfd\xfd"))

    def test_parse_response_keeps_unknown_enum_values(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0x02, 0x99, 0xB7, 0x44])))
        self.assertEqual(fan.speed, "Unknown speed 153")
        self.assertEqual(fan.airflow, "Unknown airflow 68")

    def test_heater_status_setter_does_not_recurse(self):
        fan = Fan("192.0.2.1")
        fan.heater_status = "01"
        self.assertEqual(fan.heater_status, "on")

    def test_parse_response_reads_filter_timer_setpoint(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0x63, 0x6D, 0x01]))
        )
        self.assertEqual(fan.filter_timer_setpoint, "365 d")

    def test_parse_response_reads_four_byte_filter_timer_countdown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x04, 0x64, 0x11, 0x08, 0x48, 0x00])
            )
        )
        self.assertEqual(fan.filter_timer_countdown, "72d 8h 17m ")

    def test_parse_response_reads_padded_filter_timer_countdown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x05, 0x64, 0x00, 0x11, 0x08, 0x48, 0x00])
            )
        )
        self.assertEqual(fan.filter_timer_countdown, "72d 8h 17m ")

    def test_parse_response_rejects_dangling_extended_marker(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(packet_with_payload([0xFF])))

    def test_parse_response_keeps_known_params_with_bad_value_as_unknown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x03, 0x24, 0x01, 0x02, 0x03, 0x01, 0x01])
            )
        )
        self.assertEqual(fan.unknown_params, {0x0024: "010203"})
        self.assertEqual(fan.state, "on")

    def test_parse_response_skips_no_value_parameter_markers(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0xFD, 0x65, 0x01, 0x01])))
        self.assertEqual(fan.unknown_params, {})
        self.assertEqual(fan.state, "on")


class PacketBuilderTest(unittest.TestCase):
    def test_builds_default_discovery_packet(self):
        fan = Fan("192.0.2.1")
        packet = fan.build_packet(
            fan.func["read"] + fan.encode_params("007c"),
            fan_id="DEFAULT_DEVICEID",
        )
        self.assertEqual(
            packet.upper(),
            "FDFD021044454641554C545F44455649434549440431313131017CF805",
        )

    def test_checksum_wraps_to_16_bits_little_endian(self):
        fan = Fan("192.0.2.1")
        payload = "ff" * 300
        checksum = (0xFF * 300) & 0xFFFF
        self.assertEqual(fan.chksum(payload), checksum.to_bytes(2, "little").hex())

    def test_encodes_extended_and_multibyte_params(self):
        fan = Fan("192.0.2.1")
        self.assertEqual(fan.encode_params("0302"), "ff0302")
        self.assertEqual(fan.encode_params("00b9", "0e00"), "fe02b90e00")
        self.assertEqual(fan.encode_params("0302", "0102"), "ff03fe02020102")

    def test_update_does_not_read_write_only_reset_params(self):
        fan = Fan("192.0.2.1")
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((func, param, value))
            return True

        fan.do_func = do_func
        self.assertTrue(fan.update())
        _, params, _ = calls[0]
        self.assertNotIn("0065", params)
        self.assertNotIn("0080", params)

    def test_update_falls_back_to_individual_reads_after_bulk_failure(self):
        fan = Fan("192.0.2.1")
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((param, retries))
            return len(param) == 4 and param == "0001"

        fan.params = {0x0001: ["state", fan.states], 0x0002: ["speed", fan.speeds]}
        fan.do_func = do_func

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0001", 1), ("0002", 1)])
        self.assertFalse(fan._bulk_read_supported)

    def test_vento_update_reads_humidity_in_bulk_request(self):
        fan = Fan("192.0.2.1")
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.do_func = do_func

        self.assertTrue(fan.update())
        self.assertIn("0025", calls[0][0])

    def test_extract_fan_update_uses_profile_specific_parameters(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.do_func = do_func

        self.assertTrue(fan.update())
        params, retries = calls[0]
        self.assertEqual(retries, 3)
        self.assertIn("002e", params)
        self.assertIn("0031", params)
        self.assertIn("00b9", params)
        self.assertNotIn("0064", params)
        self.assertNotIn("0306", params)

    def test_extract_fan_speed_writes_pdf_setpoints(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((param, value))
            return True

        fan.do_func = do_func
        fan.set_speed_setpoint_percent(45)

        self.assertEqual(
            calls,
            [
                ("0018", "2d"),
                ("001b", "2d"),
                ("0003", "01"),
                ("001e", "00"),
            ],
        )

    def test_extract_fan_preset_writes_one_operating_mode_packet(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((func, param, value))
            return True

        fan.do_func = do_func
        fan.set_operating_mode_preset("silent")

        self.assertEqual(len(calls), 1)
        func, params, value = calls[0]
        self.assertEqual(func, fan.func["write_return"])
        self.assertEqual(value, "")
        self.assertIn("001e01", params)
        self.assertIn("000300", params)
        self.assertIn("000f00", params)
        self.assertIn("000500", params)

    def test_extract_fan_boost_invert_value_stays_in_declared_options(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan.boost_status = "02"

        self.assertEqual(fan.boost_status, "toggle")


class DiscoveryTest(unittest.TestCase):
    def test_search_devices_times_out_cleanly_without_mutating_host(self):
        fan = Fan(None)

        class TimeoutSocket:
            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

            def settimeout(self, *args):
                pass

            def sendto(self, *args):
                pass

            def recvfrom(self, *args):
                raise socket.timeout()

            def close(self):
                self.closed = True

        sock = TimeoutSocket()
        with patch("socket.socket", return_value=sock):
            self.assertEqual(fan.search_devices(), [])
        self.assertIsNone(fan.host)


class TransportTest(unittest.TestCase):
    def test_receive_before_send_returns_false(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.receive())

    def test_do_func_retries_invalid_packet_before_success(self):
        fan = Fan("192.0.2.1")
        good_packet = packet_with_payload([0x01, 0x01])
        bad_packet = good_packet[:-1] + bytes([good_packet[-1] ^ 0xFF])
        responses = [bad_packet, good_packet]
        sent = []

        def send(data):
            sent.append(data)

        def receive():
            return responses.pop(0)

        fan.send = send
        fan.receive = receive

        self.assertTrue(fan.do_func(fan.func["read"], "0001"))
        self.assertEqual(len(sent), 2)
        self.assertEqual(fan.state, "on")


if __name__ == "__main__":
    unittest.main()

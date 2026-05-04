"""Regression tests for EcoVent packet building and writes."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload


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

        def send_command(func, param, value="", retries=10):
            calls.append((func, param, value))
            return True

        fan.send_command = send_command
        self.assertTrue(fan.update())
        _, params, _ = calls[0]
        self.assertNotIn("0065", params)
        self.assertNotIn("0080", params)

    def test_update_does_not_poll_weekly_schedule_setup(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x11, 0x00]))
        )
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((func, param, value))
            return True

        fan.send_command = send_command
        self.assertTrue(fan.update())
        _, params, _ = calls[0]
        self.assertIn("0072", params)
        self.assertNotIn("0077", params)

    def test_update_falls_back_to_individual_reads_after_bulk_failure(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return len(param) == 4 and param == "0001"

        fan.params = {0x0001: ["state", fan.states], 0x0002: ["speed", fan.speeds]}
        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0001", 1), ("0002", 1)])
        self.assertFalse(fan._bulk_read_supported)

    def test_vento_update_reads_humidity_in_bulk_request(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertIn("0025", calls[0][0])

    def test_extract_fan_update_uses_profile_specific_parameters(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.send_command = send_command

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

        def send_command(func, param, value="", retries=10):
            calls.append((param, value))
            return True

        fan.send_command = send_command
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

    def test_manual_speed_and_airflow_can_be_batched_in_one_write(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_encoded_command(func, encoded_params, retries=10):
            calls.append((func, encoded_params))
            return True

        fan.send_encoded_command = send_encoded_command
        fan.set_parameters(
            {
                "speed": "manual",
                "man_speed": "73",
                "airflow": "air_supply",
            }
        )

        self.assertEqual(
            calls,
            [
                (
                    fan.func["write_return"],
                    "02ff4473b702",
                )
            ],
        )

    def test_extract_fan_preset_writes_one_operating_mode_packet(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def send_encoded_command(func, encoded_params, retries=10):
            calls.append((func, encoded_params))
            return True

        fan.send_encoded_command = send_encoded_command
        fan.set_operating_mode_preset("silent")

        self.assertEqual(len(calls), 1)
        func, params = calls[0]
        self.assertEqual(func, fan.func["write_return"])
        self.assertIn("1e01", params)
        self.assertIn("0300", params)
        self.assertIn("0f00", params)
        self.assertIn("0500", params)

    def test_extract_fan_boost_invert_value_stays_in_declared_options(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan.boost_status = "02"

        self.assertEqual(fan.boost_status, "toggle")

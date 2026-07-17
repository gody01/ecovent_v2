"""Regression tests for EcoVent packet building and writes."""

from datetime import datetime
import unittest

from ecovent_test_helpers import Fan, packet_with_payload
from fan_protocol import MAX_BULK_READ_PARAMS


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
        params = "".join(call[1] for call in calls)
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
        params = "".join(call[1] for call in calls)
        self.assertIn("0072", params)
        self.assertNotIn("0077", params)

    def test_update_bounds_bulk_reads_to_protocol_safe_chunks(self):
        fan = Fan("192.0.2.1")
        calls = []
        fan.params = {
            param: ["state", fan.states]
            for param in range(1, MAX_BULK_READ_PARAMS * 2 + 2)
        }

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            fan._last_response_param_ids = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual([len(param) // 4 for param, _ in calls], [12, 12, 1])
        self.assertEqual(
            "".join(param for param, _ in calls),
            "".join(f"{param:04x}" for param in fan.params),
        )

    def test_update_retries_params_missing_from_valid_bulk_response(self):
        fan = Fan("192.0.2.1")
        calls = []
        fan.params = {
            0x0001: ["state", fan.states],
            0x0002: ["speed", fan.speeds],
            0x0025: ["humidity", None],
        }

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            if len(param) > 4:
                fan._last_response_param_ids = {0x0001}
            else:
                fan._last_response_param_ids = {int(param, 16)}
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(
            calls,
            [("000100020025", 3), ("0002", 1), ("0025", 1)],
        )
        self.assertTrue(fan._bulk_read_supported)

    def test_update_falls_back_to_individual_reads_after_bulk_failure(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return len(param) == 4

        fan.params = {0x0001: ["state", fan.states], 0x0002: ["speed", fan.speeds]}
        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0001", 1), ("0002", 1)])
        self.assertFalse(fan._bulk_read_supported)

    def test_update_fails_when_missing_param_retry_fails(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            if len(param) > 4:
                fan._last_response_param_ids = {0x0001}
                return True
            return False

        fan.params = {0x0001: ["state", fan.states], 0x0002: ["speed", fan.speeds]}
        fan.send_command = send_command

        self.assertFalse(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0002", 1)])

    def test_freshpoint_update_allows_missing_variant_only_sensor_params(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        optional = fan.device_profile.optional_read_params
        self.assertEqual(
            optional,
            {0x0011, 0x001A, 0x0027, 0x0315, 0x031F, 0x0320},
        )
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - optional
                return True
            param_id = int(param, 16)
            if param_id not in optional:
                fan._last_response_param_ids = {param_id}
                return True
            return False

        fan.send_command = send_command

        self.assertTrue(fan.update())
        retried = {int(param, 16) for param, retries in calls if retries == 1}
        self.assertIn(0x0027, retried)
        self.assertIn(0x0320, retried)

    def test_freshpoint_update_still_fails_when_required_sensor_is_missing(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        optional = fan.device_profile.optional_read_params

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            returned = requested - optional - {0x0025}
            fan._last_response_param_ids = returned
            return bool(returned) or len(param) > 4

        fan.send_command = send_command

        self.assertFalse(fan.update())

    def test_freshpoint_non_poll_read_still_requires_every_requested_param(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"

        def send_command(func, param, value="", retries=10):
            if len(param) > 4:
                fan._last_response_param_ids = {0x003A}
                return True
            return False

        fan.send_command = send_command

        self.assertFalse(fan.update_preset_speed_settings())

    def test_vento_update_reads_humidity_in_bulk_request(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertIn("0025", "".join(param for param, _ in calls))

    def test_breezy_quick_update_reads_humidity_and_all_four_temperatures(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.send_command = send_command

        self.assertTrue(fan.quick_update())
        requested = "".join(param for param, _ in calls)
        for param in ("001f", "0020", "0021", "0022", "0025"):
            self.assertIn(param, requested.lower())

    def test_extract_fan_update_uses_profile_specific_parameters(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        params = "".join(param for param, _ in calls)
        self.assertTrue(all(retries == 3 for _, retries in calls))
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

        def send_encoded_command(
            func, encoded_params, retries=10, include_extra_write_parameters=True
        ):
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

    def test_manual_speed_only_write_is_counted_as_quiet(self):
        fan = Fan("192.0.2.1")
        calls = []

        def send(data):
            calls.append(data)
            return True

        fan.send = send
        fan.receive = lambda: packet_with_payload([])

        fan.set_man_speed_percent(73)

        self.assertEqual(len(calls), 1)
        self.assertIn("0344bb", calls[0])
        self.assertEqual(fan.audible_write_command_count, 0)

    def test_manual_speed_zero_write_reaches_device(self):
        fan = Fan("192.0.2.1")
        calls = []
        fan.send = lambda data: calls.append(data) or True
        fan.receive = lambda: packet_with_payload([])

        fan.set_man_speed_percent(0)

        self.assertEqual(len(calls), 1)
        self.assertIn("034400", calls[0])
        self.assertEqual(fan.audible_write_command_count, 0)

    def test_read_commands_do_not_increment_audible_write_count(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda data: True
        fan.receive = lambda: packet_with_payload([])

        self.assertTrue(fan.get_param("state"))

        self.assertEqual(fan.audible_write_command_count, 0)

    def test_mode_write_increments_audible_write_count(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda data: True
        fan.receive = lambda: packet_with_payload([])

        self.assertTrue(fan.set_param("state", "on"))

        self.assertEqual(fan.audible_write_command_count, 1)

    def test_clock_rows_make_manual_speed_batch_audible(self):
        fan = Fan("192.0.2.1")
        fan.extra_write_parameters_callback = lambda: {
            "rtc_time": "1e2d13",
            "rtc_date": "1704041a",
        }
        fan.send = lambda data: True
        fan.receive = lambda: packet_with_payload([])

        self.assertTrue(fan.set_parameters({"man_speed": "73"}))

        self.assertEqual(fan.audible_write_command_count, 1)

    def test_opportunistic_clock_sync_is_batched_into_existing_writes(self):
        fan = Fan("192.0.2.1")
        calls = []
        fan.extra_write_parameters_callback = lambda: {
            "rtc_time": "1e2d13",
            "rtc_date": "1704041a",
        }

        def send(data):
            calls.append(data)
            return True

        fan.send = send
        fan.receive = lambda: packet_with_payload([])

        self.assertTrue(fan.set_param("state", "on"))

        self.assertEqual(len(calls), 1)
        self.assertIn("030101fe036f1e2d13fe04701704041a", calls[0])

    def test_explicit_clock_sync_does_not_reappend_opportunistic_clock_rows(self):
        fan = Fan("192.0.2.1")
        calls = []
        fan.extra_write_parameters_callback = lambda: {
            "rtc_time": "000000",
            "rtc_date": "01010101",
        }

        def send(data):
            calls.append(data)
            return True

        fan.send = send
        fan.receive = lambda: packet_with_payload([])

        self.assertTrue(fan.set_rtc_datetime(datetime(2026, 4, 23, 19, 45, 30)))

        self.assertEqual(len(calls), 1)
        self.assertIn("03fe036f1e2d13fe04701704041a", calls[0])
        self.assertNotIn("000000", calls[0])

    def test_extract_fan_preset_writes_one_operating_mode_packet(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        calls = []

        def send_encoded_command(
            func, encoded_params, retries=10, include_extra_write_parameters=True
        ):
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

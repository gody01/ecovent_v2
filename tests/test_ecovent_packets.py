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
            fan._last_response_param_ids = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
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
            fan._last_response_param_ids = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
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
            if len(param) == 4:
                fan._last_response_param_ids = {int(param, 16)}
                return True
            return False

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

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0002", 1)])
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, {0x0002})

    def test_update_logs_missing_required_param_addresses(self):
        fan = Fan("192.0.2.1", name="Freshpoint MBR")
        fan.params = {
            0x0001: ["state", fan.states],
            0x0002: ["speed", fan.speeds],
            0x0025: ["humidity", None],
        }

        def send_command(func, param, value="", retries=10):
            if len(param) > 4:
                fan._last_response_param_ids = {0x0001}
                return True
            return False

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="WARNING") as logs:
            self.assertFalse(fan._read_params("000100020025", read_name="setup poll"))

        messages = "\n".join(logs.output)
        self.assertIn("EcoVent setup poll incomplete", messages)
        self.assertIn("requested parameters: 0x0001, 0x0002, 0x0025", messages)
        self.assertIn("required availability parameters: 0x0001, 0x0002, 0x0025", messages)
        self.assertIn("received parameters: 0x0001", messages)
        self.assertIn("missing required parameters: 0x0002, 0x0025", messages)
        self.assertIn("no-response individual retries: 0x0002, 0x0025", messages)
        self.assertIn("result: unavailable", messages)
        self.assertIn("Freshpoint MBR", messages)

    def test_freshpoint_update_allows_missing_noncritical_poll_params(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        required = fan.device_profile.poll_required_params
        self.assertEqual(
            required,
            {
                0x0001,
                0x0002,
                0x0044,
            },
        )
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested & required
                return True
            param_id = int(param, 16)
            if param_id in required:
                fan._last_response_param_ids = {param_id}
                return True
            return False

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.update())
        retried = {int(param, 16) for param, retries in calls if retries == 1}
        for param_id in (0x001F, 0x0020, 0x0021, 0x0022, 0x0025):
            self.assertIn(param_id, retried)
        self.assertIn(0x0027, retried)
        self.assertIn(0x0084, retried)
        self.assertIn(0x0129, retried)
        self.assertIn(0x030B, retried)
        self.assertIn(0x0320, retried)
        self.assertIn(0x0400, retried)
        self.assertIn(0x0409, retried)
        messages = "\n".join(logs.output)
        self.assertIn("missing required parameters: none", messages)
        self.assertIn("optional unavailable parameters:", messages)
        self.assertIn("0x000F", messages)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertIn(0x0025, fan.last_missing_optional_params)

        calls.clear()
        self.assertTrue(fan.update())
        self.assertEqual(
            [param for param, retries in calls if retries == 1],
            [],
        )
        self.assertIn(0x0025, fan.last_missing_optional_params)

    def test_freshbox_update_allows_missing_alarm_list_param(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"
        required = fan.device_profile.poll_required_params
        self.assertEqual(
            required,
            {
                0x0002,
                0x0006,
            },
        )
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - {0x0001, 0x007F}
                return True
            if requested <= {0x0001, 0x007F}:
                return False
            fan._last_response_param_ids = requested
            return True

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.update())

        retried = {int(param, 16) for param, retries in calls if retries == 1}
        self.assertIn(0x007F, retried)
        self.assertIn(0x0001, retried)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, {0x0001, 0x007F})
        messages = "\n".join(logs.output)
        self.assertIn("profile=freshbox", messages)
        self.assertIn("missing required parameters: none", messages)
        self.assertIn("optional unavailable parameters: 0x0001, 0x007F", messages)
        self.assertIn("result: available", messages)

    def test_freshbox_init_device_allows_missing_noncritical_poll_params(self):
        fan = Fan("192.0.2.1")
        missing_optional = {0x0001, 0x007F}
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if requested == {0x007C}:
                fan.device_search = "4d494352412d4944"
                fan._last_response_param_ids = requested
                return True
            if requested == {0x00B9}:
                fan.unit_type = "0200"
                fan._last_response_param_ids = requested
                return True
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            if requested <= missing_optional:
                return False
            fan._last_response_param_ids = requested
            return True

        fan.send_command = send_command

        self.assertTrue(fan.init_device())
        self.assertEqual(fan.id, "MICRA-ID")
        self.assertEqual(fan.profile_key, "freshbox")
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, missing_optional)
        self.assertEqual(calls[:2], [("007c", 10), ("00b9", 10)])

    def test_freshbox_full_and_quick_polls_fail_when_core_rows_are_absent(self):
        for method_name, missing_param in (
            ("update", 0x0002),
            ("update", 0x0006),
            ("quick_update", 0x0006),
        ):
            with self.subTest(method=method_name, missing=f"0x{missing_param:04X}"):
                fan = Fan("192.0.2.1")
                fan.unit_type = "0200"

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16)
                        for i in range(0, len(param), 4)
                    }
                    if len(param) == 4 and missing_param in requested:
                        return False
                    fan._last_response_param_ids = requested - {missing_param}
                    return bool(fan._last_response_param_ids) or len(param) > 4

                fan.send_command = send_command

                self.assertFalse(getattr(fan, method_name)())
                self.assertEqual(fan.last_missing_required_params, {missing_param})

    def test_freshpoint_update_clears_optional_unsupported_param_without_retrying(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.params = {
            0x0001: ["state", fan.states],
            0x0002: ["speed", fan.speeds],
            0x0044: ["man_speed", None],
            0x0025: ["humidity", None],
        }
        fan.humidity = "2a"
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            fan._last_response_param_ids = requested - {0x0025}
            fan._last_unsupported_param_ids = requested & {0x0025}
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("0001000200440025", 3)])
        self.assertIsNone(fan.humidity)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, {0x0025})
        self.assertEqual(fan.last_unsupported_params, {0x0025})

        calls.clear()
        self.assertTrue(fan.update())
        self.assertEqual(calls, [("000100020044", 3)])
        self.assertEqual(fan.last_missing_optional_params, set())
        self.assertEqual(fan.last_unsupported_params, set())

    def test_freshpoint_poll_skips_issue74_unsupported_sensor_rows(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        issue74_sensor_rows = {
            0x001F,
            0x0020,
            0x0021,
            0x0022,
            0x0025,
            0x0027,
            0x0129,
            0x0320,
        }
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            fan._last_response_param_ids = requested - issue74_sensor_rows
            fan._last_unsupported_param_ids = requested & issue74_sensor_rows
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertLessEqual(issue74_sensor_rows, fan.last_unsupported_params)
        calls.clear()

        self.assertTrue(fan.update())
        requested_after_learning = {
            int(param[i : i + 4], 16)
            for param, _ in calls
            for i in range(0, len(param), 4)
        }
        self.assertFalse(issue74_sensor_rows & requested_after_learning)
        self.assertLessEqual({0x0001, 0x0002, 0x0044}, requested_after_learning)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_unsupported_params, set())

    def test_unsupported_optional_poll_rows_hide_generated_entities(self):
        fan = Fan("192.0.2.1")
        fan._set_device_profile("breezy")
        fan._unsupported_optional_poll_params = {0x001F, 0x0027, 0x0320}

        self.assertFalse(fan.supports_parameter("outdoor_temperature"))
        self.assertFalse(
            fan.supports_entity(
                required_params=("outdoor_temperature",),
                required_capabilities=("temperature_probes",),
            )
        )
        self.assertTrue(fan.supports_parameter("co2_treshold"))
        self.assertFalse(fan.supports_capability("co2"))
        self.assertFalse(
            fan.supports_entity(
                required_params=("co2_treshold",),
                required_capabilities=("co2",),
            )
        )
        self.assertFalse(
            fan.supports_entity(
                required_params=("co2_sensor_state",),
                required_capabilities=("co2",),
            )
        )
        self.assertTrue(fan.supports_parameter("voc_treshold"))
        self.assertFalse(fan.supports_capability("voc"))
        self.assertFalse(
            fan.supports_entity(
                required_params=("voc_treshold",),
                required_capabilities=("voc",),
            )
        )
        self.assertFalse(
            fan.supports_entity(
                required_params=("voc_sensor_state",),
                required_capabilities=("voc",),
            )
        )
        self.assertTrue(fan.supports_parameter("state"))
        self.assertTrue(
            fan.supports_entity(
                required_params=("state", "speed", "man_speed"),
            )
        )

    def test_unsupported_single_temperature_probe_keeps_sibling_probe_entities(self):
        fan = Fan("192.0.2.1")
        fan._set_device_profile("breezy")
        fan._unsupported_optional_poll_params = {0x001F}

        self.assertFalse(
            fan.supports_entity(
                required_params=("outdoor_temperature",),
                required_capabilities=("temperature_probes",),
            )
        )
        self.assertTrue(
            fan.supports_entity(
                required_params=("supply_temperature",),
                required_capabilities=("temperature_probes",),
            )
        )

    def test_freshpoint_optional_param_recovers_from_bulk_read_during_backoff(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.params = {
            0x0001: ["state", fan.states],
            0x0002: ["speed", fan.speeds],
            0x0044: ["man_speed", None],
            0x0025: ["humidity", None],
        }
        calls = []
        recovered = False

        def send_command(func, param, value="", retries=10):
            nonlocal recovered
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if not recovered:
                if len(param) > 4:
                    fan._last_response_param_ids = requested - {0x0025}
                    return True
                return False

            fan._last_response_param_ids = requested
            if 0x0025 in requested:
                fan.humidity = "37"
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertIsNone(fan.humidity)
        self.assertIn(0x0025, fan.last_missing_optional_params)
        calls.clear()

        recovered = True
        self.assertTrue(fan.update())
        self.assertEqual(calls, [("0001000200440025", 3)])
        self.assertEqual(fan.humidity, "55")
        self.assertEqual(fan.last_missing_optional_params, set())

    def test_freshpoint_optional_state_rows_clear_and_recover(self):
        rows = {
            0x0025: ("humidity", "2a", "37", "55"),
            0x0083: ("alarm_status", "00", "01", "alarm"),
            0x0072: ("weekly_schedule_state", "01", "00", "off"),
            0x00B7: ("airflow", "02", "01", "heat_recovery"),
        }
        for param_id, (attr, old_value, recovered_value, expected) in rows.items():
            with self.subTest(param=f"0x{param_id:04X}", attr=attr):
                fan = Fan("192.0.2.1")
                fan.unit_type = "1100"
                fan.params = {
                    0x0001: ["state", fan.states],
                    0x0002: ["speed", fan.speeds],
                    0x0044: ["man_speed", None],
                    param_id: [attr, fan.params[param_id][1]],
                }
                setattr(fan, attr, old_value)
                recovered = False

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16)
                        for i in range(0, len(param), 4)
                    }
                    if not recovered:
                        if len(param) > 4:
                            fan._last_response_param_ids = requested - {param_id}
                            return True
                        return False

                    fan._last_response_param_ids = requested
                    if param_id in requested:
                        setattr(fan, attr, recovered_value)
                    return True

                fan.send_command = send_command

                self.assertTrue(fan.update())
                self.assertIsNone(getattr(fan, attr))
                self.assertEqual(fan.last_missing_optional_params, {param_id})

                recovered = True
                self.assertTrue(fan.update())
                self.assertEqual(getattr(fan, attr), expected)
                self.assertEqual(fan.last_missing_optional_params, set())

    def test_targeted_read_bypasses_optional_poll_backoff(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.params = {
            0x0001: ["state", fan.states],
            0x0002: ["speed", fan.speeds],
            0x0044: ["man_speed", None],
            0x0025: ["humidity", None],
        }
        calls = []
        targeted = False

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if targeted:
                fan._last_response_param_ids = requested
                fan.humidity = "37"
                return True
            if len(param) > 4:
                fan._last_response_param_ids = requested - {0x0025}
                return True
            return False

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertIn(0x0025, fan.last_missing_optional_params)
        calls.clear()

        targeted = True
        self.assertTrue(fan._read_params("0025"))
        self.assertEqual(calls, [("0025", 3)])
        self.assertEqual(fan.humidity, "55")
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, set())

    def test_freshpoint_full_and_quick_polls_fail_when_core_rows_are_absent(self):
        for method_name in ("update", "quick_update"):
            for missing_param in (0x0001, 0x0002, 0x0044):
                with self.subTest(method=method_name, missing=f"0x{missing_param:04X}"):
                    fan = Fan("192.0.2.1")
                    fan.unit_type = "1100"

                    def send_command(func, param, value="", retries=10):
                        requested = {
                            int(param[i : i + 4], 16)
                            for i in range(0, len(param), 4)
                        }
                        if len(param) == 4 and missing_param in requested:
                            return False
                        fan._last_response_param_ids = requested - {missing_param}
                        return True

                    fan.send_command = send_command

                    self.assertFalse(getattr(fan, method_name)())
                    self.assertEqual(fan.last_missing_required_params, {missing_param})
                    self.assertEqual(fan.last_unsupported_params, set())

    def test_freshpoint_full_and_quick_polls_fail_when_core_rows_are_unsupported(self):
        for method_name in ("update", "quick_update"):
            for unsupported_param in (0x0001, 0x0002, 0x0044):
                with self.subTest(
                    method=method_name, unsupported=f"0x{unsupported_param:04X}"
                ):
                    fan = Fan("192.0.2.1")
                    fan.unit_type = "1100"
                    calls = []

                    def send_command(func, param, value="", retries=10):
                        calls.append((param, retries))
                        requested = {
                            int(param[i : i + 4], 16)
                            for i in range(0, len(param), 4)
                        }
                        fan._last_response_param_ids = requested - {unsupported_param}
                        fan._last_unsupported_param_ids = requested & {
                            unsupported_param
                        }
                        return True

                    fan.send_command = send_command

                    self.assertFalse(getattr(fan, method_name)())
                    self.assertEqual(
                        fan.last_missing_required_params, {unsupported_param}
                    )
                    self.assertEqual(fan.last_unsupported_params, {unsupported_param})
                    self.assertFalse(
                        [
                            param
                            for param, retries in calls
                            if retries == 1 and int(param, 16) == unsupported_param
                        ]
                    )

    def test_freshpoint_update_still_fails_when_core_poll_param_is_missing(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            returned = requested - {0x0002}
            fan._last_response_param_ids = returned
            return bool(returned) or len(param) > 4

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertFalse(fan.update())

        messages = "\n".join(logs.output)
        self.assertIn("missing required parameters: 0x0002", messages)
        self.assertEqual(fan.last_missing_required_params, {0x0002})
        self.assertNotIn(0x0002, fan.last_missing_optional_params)

    def test_freshpoint_quick_update_allows_missing_issue63_sensor_rows(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.humidity = "2a"
        missing_issue63_sensors = {0x001F, 0x0020, 0x0021, 0x0022, 0x0025, 0x0027}
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            returned = requested - missing_issue63_sensors
            fan._last_response_param_ids = returned
            return bool(returned)

        fan.send_command = send_command

        self.assertTrue(fan.quick_update())
        retried = {int(param, 16) for param, retries in calls if retries == 1}
        self.assertLessEqual(missing_issue63_sensors, retried)
        self.assertIsNone(fan.humidity)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(missing_issue63_sensors, fan.last_missing_optional_params)

    def test_freshpoint_soft_missing_identity_rows_keep_active_profile(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        unit_type = fan.unit_type

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            returned = requested & fan.device_profile.poll_required_params
            fan._last_response_param_ids = returned
            return bool(returned) or len(param) > 4

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(fan.unit_type, unit_type)
        self.assertEqual(fan.profile_key, "breezy")
        self.assertIn(0x00B9, fan.last_missing_optional_params)

    def test_freshpoint_quick_update_fails_when_core_poll_param_is_missing(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            returned = requested - {0x0044}
            fan._last_response_param_ids = returned
            return bool(returned) or len(param) > 4

        fan.send_command = send_command

        self.assertFalse(fan.quick_update())
        self.assertEqual(fan.last_missing_required_params, {0x0044})

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
            fan._last_response_param_ids = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertIn("0025", "".join(param for param, _ in calls))

    def test_vento_update_allows_missing_optional_poll_params(self):
        fan = Fan("192.0.2.1")
        required = fan.device_profile.poll_required_params
        self.assertEqual(required, frozenset())
        missing_optional = {0x0025, 0x0083, 0x0304, 0x0305}
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            param_id = int(param, 16)
            if param_id in missing_optional:
                return False
            fan._last_response_param_ids = {param_id}
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        retried = {int(param, 16) for param, retries in calls if retries == 1}
        self.assertLessEqual(missing_optional, retried)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(missing_optional, fan.last_missing_optional_params)

    def test_vento_quick_update_allows_missing_optional_poll_params(self):
        fan = Fan("192.0.2.1")
        missing_optional = {0x0006, 0x002D, 0x0304, 0x0305}
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            param_id = int(param, 16)
            if param_id in missing_optional:
                return False
            fan._last_response_param_ids = {param_id}
            return True

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.quick_update())

        messages = "\n".join(logs.output)
        self.assertIn("EcoVent quick poll incomplete", messages)
        self.assertIn("profile=vento", messages)
        self.assertIn("required availability parameters: none", messages)
        self.assertIn("optional unavailable parameters: 0x0006, 0x002D, 0x0304, 0x0305", messages)
        self.assertIn("missing from bulk response: 0x0006, 0x002D, 0x0304, 0x0305", messages)
        self.assertIn("individual retries attempted: 0x0006, 0x002D, 0x0304, 0x0305", messages)
        self.assertIn("result: available", messages)
        retried = {int(param, 16) for param, retries in calls if retries == 1}
        self.assertLessEqual(missing_optional, retried)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(missing_optional, fan.last_missing_optional_params)

    def test_vento_optional_backoff_diagnostics_do_not_claim_retry(self):
        fan = Fan("192.0.2.1")
        missing_optional = {0x0006}

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            return False

        fan.send_command = send_command

        self.assertTrue(fan.quick_update())
        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.quick_update())

        messages = "\n".join(logs.output)
        self.assertIn("missing from bulk response: 0x0006", messages)
        self.assertIn("individual retries attempted: none", messages)
        self.assertIn("Optional parameter 0x0006 still unavailable", messages)

    def test_vento_init_device_allows_missing_optional_poll_params(self):
        fan = Fan("192.0.2.1")
        missing_optional = {0x0025, 0x0083, 0x0304, 0x0305}
        calls = []

        def send_command(func, param, value="", retries=10):
            calls.append((param, retries))
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if requested == {0x007C}:
                fan.device_search = "56454e544f2d4944"
                fan._last_response_param_ids = requested
                return True
            if requested == {0x00B9}:
                fan.unit_type = "0300"
                fan._last_response_param_ids = requested
                return True
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            param_id = int(param, 16)
            if param_id in missing_optional:
                return False
            fan._last_response_param_ids = {param_id}
            return True

        fan.send_command = send_command

        self.assertTrue(fan.init_device())
        self.assertEqual(fan.id, "VENTO-ID")
        self.assertEqual(fan.profile_key, "vento")
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(missing_optional, fan.last_missing_optional_params)
        self.assertEqual(calls[:2], [("007c", 10), ("00b9", 10)])

    def test_vento_update_allows_unsupported_optional_poll_params(self):
        fan = Fan("192.0.2.1")
        unsupported_optional = {0x0025, 0x0083, 0x0304, 0x0305}

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            fan._last_response_param_ids = requested - unsupported_optional
            fan._last_unsupported_param_ids = requested & unsupported_optional
            return True

        fan.send_command = send_command

        self.assertTrue(fan.update())
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(unsupported_optional, fan.last_missing_optional_params)
        self.assertLessEqual(unsupported_optional, fan.last_unsupported_params)

    def test_vento_update_allows_issue78_and_issue80_optional_rows(self):
        unsupported_optional = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0063,
        }

        for unit_type in ("0300", "0400"):
            with self.subTest(unit_type=unit_type):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16) for i in range(0, len(param), 4)
                    }
                    fan._last_response_param_ids = requested - unsupported_optional
                    fan._last_unsupported_param_ids = requested & unsupported_optional
                    return True

                fan.send_command = send_command

                with self.assertLogs("fan_protocol", level="DEBUG") as logs:
                    self.assertTrue(fan.update())

                messages = "\n".join(logs.output)
                self.assertIn("required availability parameters: none", messages)
                self.assertIn("unsupported parameters: 0x003A", messages)
                self.assertIn("missing required parameters: none", messages)
                self.assertIn("result: available", messages)
                self.assertEqual(fan.last_missing_required_params, set())
                self.assertLessEqual(
                    unsupported_optional, fan.last_missing_optional_params
                )
                self.assertLessEqual(unsupported_optional, fan.last_unsupported_params)

    def test_vento_update_allows_issue90_a30_optional_rows(self):
        unsupported_optional = {
            0x0016,
            0x002D,
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x004B,
            0x0063,
            0x00B8,
            0x0305,
        }
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan._firmware = "0.3 2020-08-26"

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            fan._last_response_param_ids = requested - unsupported_optional
            fan._last_unsupported_param_ids = requested & unsupported_optional
            return True

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.update())

        messages = "\n".join(logs.output)
        self.assertIn("required availability parameters: none", messages)
        self.assertIn("unsupported parameters: 0x0016", messages)
        self.assertIn("missing required parameters: none", messages)
        self.assertIn("result: available", messages)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(unsupported_optional, fan.last_missing_optional_params)
        self.assertLessEqual(unsupported_optional, fan.last_unsupported_params)

    def test_vento_update_allows_issue76_missing_state_and_speed_rows(self):
        fan = Fan("192.0.2.1")
        missing_optional = {0x0001, 0x0002}

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            if len(param) > 4:
                fan._last_response_param_ids = requested - missing_optional
                return True
            param_id = int(param, 16)
            if param_id in missing_optional:
                return False
            fan._last_response_param_ids = {param_id}
            return True

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.update())

        messages = "\n".join(logs.output)
        self.assertIn("required availability parameters: none", messages)
        self.assertIn("optional unavailable parameters: 0x0001, 0x0002", messages)
        self.assertIn("missing required parameters: none", messages)
        self.assertIn("result: available", messages)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(missing_optional, fan.last_missing_optional_params)

    def test_vento_update_accepts_an_unsupported_row_when_other_rows_return(self):
        for unsupported_param in (0x0044,):
            with self.subTest(unsupported=f"0x{unsupported_param:04X}"):
                fan = Fan("192.0.2.1")

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16)
                        for i in range(0, len(param), 4)
                    }
                    fan._last_response_param_ids = requested - {unsupported_param}
                    fan._last_unsupported_param_ids = requested & {unsupported_param}
                    return True

                fan.send_command = send_command

                self.assertTrue(fan.update())
                self.assertEqual(fan.last_missing_required_params, set())
                self.assertEqual(fan.last_unsupported_params, {unsupported_param})

    def test_vento_full_and_quick_polls_accept_missing_individual_rows(self):
        for method_name, missing_param in (
            ("update", 0x0044),
            ("quick_update", 0x0044),
        ):
            with self.subTest(method=method_name, missing=f"0x{missing_param:04X}"):
                fan = Fan("192.0.2.1")

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16)
                        for i in range(0, len(param), 4)
                    }
                    if len(param) == 4 and missing_param in requested:
                        return False
                    fan._last_response_param_ids = requested - {missing_param}
                    return bool(fan._last_response_param_ids) or len(param) > 4

                fan.send_command = send_command

                self.assertTrue(getattr(fan, method_name)())
                self.assertEqual(fan.last_missing_required_params, set())

    def test_vento_poll_rejects_untracked_response_without_any_rows(self):
        fan = Fan("192.0.2.1")

        def send_command(func, param, value="", retries=10):
            fan._last_response_param_ids = None
            fan._last_unsupported_param_ids = None
            return True

        fan.send_command = send_command

        self.assertFalse(fan.quick_update())
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertEqual(fan.last_missing_optional_params, set())

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
        for param in ("0001", "0002", "001f", "0020", "0021", "0022", "0025", "0044"):
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

    def test_extract_fan_update_allows_unsupported_motion_rows(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        unsupported_optional = {0x000B, 0x0012}

        def send_command(func, param, value="", retries=10):
            requested = {
                int(param[i : i + 4], 16) for i in range(0, len(param), 4)
            }
            fan._last_response_param_ids = requested - unsupported_optional
            fan._last_unsupported_param_ids = requested & unsupported_optional
            return True

        fan.send_command = send_command

        with self.assertLogs("fan_protocol", level="DEBUG") as logs:
            self.assertTrue(fan.update())

        messages = "\n".join(logs.output)
        self.assertIn("profile=extract_fan", messages)
        self.assertIn("required availability parameters: 0x0001, 0x0004", messages)
        self.assertIn("unsupported parameters: 0x000B, 0x0012", messages)
        self.assertIn("missing required parameters: none", messages)
        self.assertIn("result: available", messages)
        self.assertEqual(fan.last_missing_required_params, set())
        self.assertLessEqual(unsupported_optional, fan.last_missing_optional_params)
        self.assertLessEqual(unsupported_optional, fan.last_unsupported_params)

    def test_extract_fan_update_fails_when_core_rows_are_unsupported(self):
        for unsupported_param in (0x0001, 0x0004):
            with self.subTest(unsupported=f"0x{unsupported_param:04X}"):
                fan = Fan("192.0.2.1")
                fan.unit_type = "0600"

                def send_command(func, param, value="", retries=10):
                    requested = {
                        int(param[i : i + 4], 16) for i in range(0, len(param), 4)
                    }
                    fan._last_response_param_ids = requested - {unsupported_param}
                    fan._last_unsupported_param_ids = requested & {unsupported_param}
                    return True

                fan.send_command = send_command

                self.assertFalse(fan.update())
                self.assertEqual(
                    fan.last_missing_required_params, {unsupported_param}
                )
                self.assertEqual(fan.last_unsupported_params, {unsupported_param})

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

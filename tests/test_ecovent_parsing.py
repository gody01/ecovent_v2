"""Regression tests for robust EcoVent packet parsing."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload


class ParseRobustnessTest(unittest.TestCase):
    def test_parse_response_skips_unknown_parameter_ids(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0xFF, 0x12, 0x34, 0xAB, 0xFF, 0x00, 0x01, 0x01]
                )
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

    def test_parse_response_rejects_wrong_function(self):
        fan = Fan("192.0.2.1")

        self.assertFalse(fan.parse_response(packet_with_payload([], function=0x01)))
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([], function=int(fan.func["resp"], 16))
            )
        )

    def test_parse_response_rejects_invalid_envelope_fields(self):
        fan = Fan("192.0.2.1")

        self.assertFalse(fan.parse_response(packet_with_payload([], packet_type=0x01)))
        self.assertFalse(
            fan.parse_response(packet_with_payload([], device_id=b"X" * 17))
        )
        self.assertFalse(
            fan.parse_response(packet_with_payload([], password=b"X" * 9))
        )

    def test_parse_response_correlates_configured_device_id(self):
        configured_id = "KNOWN_DEVICE_ID!"
        fan = Fan("192.0.2.1", fan_id=configured_id)

        self.assertFalse(
            fan.parse_response(
                packet_with_payload(
                    [0x01, 0x01], device_id=b"OTHER_DEVICE_ID!"
                )
            )
        )
        self.assertIsNone(fan.state)
        self.assertIsNone(fan._last_response_device_id)

        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0x01, 0x01], device_id=configured_id.encode()
                )
            )
        )
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan._last_response_device_id, configured_id)

    def test_discovery_can_accept_an_unconfigured_device_id(self):
        fan = Fan("192.0.2.1", fan_id="KNOWN_DEVICE_ID!")

        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0x01, 0x01], device_id=b"OTHER_DEVICE_ID!"
                ),
                allow_any_device_id=True,
            )
        )
        self.assertEqual(fan._last_response_device_id, "OTHER_DEVICE_ID!")

    def test_parse_response_rejects_short_packet(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(b"\xfd\xfd"))

    def test_parse_response_keeps_unknown_enum_values(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0x02, 0x99, 0xB7, 0x44]))
        )
        self.assertEqual(fan.speed, "Unknown speed 153")
        self.assertEqual(fan.airflow, "Unknown airflow 68")

    def test_default_airflow_enum_three_stays_unknown(self):
        fan = Fan("192.0.2.1")
        fan.airflow = "03"
        self.assertEqual(fan.airflow, "Unknown airflow 3")

    def test_beeper_unknown_enum_value_is_stable_sensor_state(self):
        fan = Fan("192.0.2.1")
        fan.beeper = "03"
        self.assertEqual(fan.beeper, "Unknown beeper 3")

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

    def test_filter_timer_rows_reject_unbounded_padding(self):
        malformed_rows = (
            (0x63, [0x00, 0x6D, 0x01], "365 d"),
            (0x64, [0x00, 0x00, 0x11, 0x08, 0x48, 0x00], "72d 8h 17m "),
            (0x64, [0x01, 0x11, 0x08, 0x48, 0x00], "72d 8h 17m "),
        )

        for parameter, malformed, previous in malformed_rows:
            with self.subTest(parameter=parameter, malformed=malformed):
                fan = Fan("192.0.2.1")
                fan.filter_timer_setpoint = "6d01"
                fan.filter_timer_countdown = "11084800"
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [0xFE, len(malformed), parameter, *malformed]
                        )
                    )
                )
                attribute = (
                    fan.filter_timer_setpoint
                    if parameter == 0x63
                    else fan.filter_timer_countdown
                )
                self.assertEqual(attribute, previous)
                self.assertEqual(
                    fan.unknown_params, {parameter: bytes(malformed).hex()}
                )
                self.assertEqual(fan._last_response_param_ids, set())

    def test_parse_response_rejects_dangling_extended_marker(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(packet_with_payload([0xFF])))

    def test_parse_response_rejects_nested_or_unsupported_markers(self):
        fan = Fan("192.0.2.1")
        malformed_payloads = (
            [0xFE, 0x02, 0xFE, 0x02, 0x63, 0x6D, 0x01],
            [0xFD, 0xFE, 0x02, 0x63, 0x6D, 0x01],
            [0xFC, 0x01, 0x01, 0x01],
        )

        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(fan.parse_response(packet_with_payload(payload)))
                self.assertIsNone(fan.filter_timer_setpoint)
                self.assertIsNone(fan._last_response_param_values)

    def test_invalid_payload_does_not_apply_valid_prefix(self):
        fan = Fan("192.0.2.1")

        self.assertFalse(fan.parse_response(packet_with_payload([0x01, 0x01, 0xFF])))
        self.assertIsNone(fan.state)
        self.assertIsNone(fan._last_response_param_ids)

        self.assertTrue(fan.parse_response(packet_with_payload([0x01, 0x01])))
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan._last_response_param_values, {0x0001: b"\x01"})

    def test_parse_response_rejects_duplicate_or_conflicting_parameter_status(self):
        malformed_payloads = (
            [0x01, 0x00, 0x01, 0x01],
            [0xFD, 0x01, 0x01, 0x01],
            [0xFD, 0x01, 0xFD, 0x01],
        )

        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                fan = Fan("192.0.2.1")

                self.assertFalse(fan.parse_response(packet_with_payload(payload)))
                self.assertIsNone(fan.state)
                self.assertIsNone(fan._last_response_param_ids)
                self.assertIsNone(fan._last_unsupported_param_ids)

    def test_parse_response_keeps_known_params_with_bad_value_as_unknown(self):
        fan = Fan("192.0.2.1")
        fan.battery_voltage = "3412"
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x03, 0x24, 0x01, 0x02, 0x03, 0x01, 0x01])
            )
        )
        self.assertEqual(fan.unknown_params, {0x0024: "010203"})
        self.assertEqual(fan.battery_voltage, "4660 mV")
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan._last_raw_response_param_ids, {0x0024, 0x0001})
        self.assertEqual(fan._last_response_param_ids, {0x0001})

    def test_alarm_list_rejects_an_unpaired_trailing_byte(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x02, 0x7F, 0x01, 0x02])
            )
        )
        self.assertEqual(fan.alarm_list, "1:warning")

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x03, 0x7F, 0x01, 0x02, 0x03])
            )
        )
        self.assertEqual(fan.alarm_list, "1:warning")
        self.assertEqual(fan.unknown_params, {0x007F: "010203"})
        self.assertEqual(fan._last_raw_response_param_ids, {0x007F})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_air_quality_status_rejects_noncanonical_multi_byte_length(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        valid = [0x00, 0x01, 0x00, 0x00, 0x01]

        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, len(valid), 0x84, *valid]))
        )
        previous = fan.air_quality_status

        malformed = [*valid, 0x00]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(malformed), 0x84, *malformed])
            )
        )
        self.assertEqual(fan.air_quality_status, previous)
        self.assertEqual(fan.unknown_params, {0x0084: bytes(malformed).hex()})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_firmware_rejects_noncanonical_length(self):
        fan = Fan("192.0.2.1")
        valid = [0x00, 0x03, 0x1A, 0x08, 0xE4, 0x07]

        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, len(valid), 0x86, *valid]))
        )
        self.assertEqual(fan.firmware, "0.3 2020-08-26")

        malformed = [0x00, *valid]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(malformed), 0x86, *malformed])
            )
        )
        self.assertEqual(fan.firmware, "0.3 2020-08-26")
        self.assertEqual(fan.unknown_params, {0x0086: bytes(malformed).hex()})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_weekly_schedule_rejects_noncanonical_length(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        valid = [0x01, 0x01, 0x01, 0x00, 0x00, 0x06]

        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, len(valid), 0x77, *valid]))
        )
        previous = fan.weekly_schedule_setup

        malformed = [0x00, *valid]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(malformed), 0x77, *malformed])
            )
        )
        self.assertEqual(fan.weekly_schedule_setup, previous)
        self.assertEqual(fan.unknown_params, {0x0077: bytes(malformed).hex()})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_machine_hours_decodes_two_byte_day_counter(self):
        fan = Fan("192.0.2.1")
        valid = [0x11, 0x08, 0x2C, 0x01]

        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, len(valid), 0x7E, *valid]))
        )
        self.assertEqual(fan.machine_hours, "300d 8h 17m ")

        malformed = [0x00, *valid]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(malformed), 0x7E, *malformed])
            )
        )
        self.assertEqual(fan.machine_hours, "300d 8h 17m ")
        self.assertEqual(fan.unknown_params, {0x007E: bytes(malformed).hex()})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_parse_response_skips_no_value_parameter_markers(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFD, 0x65, 0x01, 0x01]))
        )
        self.assertEqual(fan.unknown_params, {})
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan._last_response_param_ids, {0x0001})
        self.assertEqual(fan._last_unsupported_param_ids, {0x0065})

    def test_parse_response_records_present_and_unsupported_parameter_ids_separately(self):
        fan = Fan("192.0.2.1")

        self.assertTrue(
            fan.parse_response(packet_with_payload([0x25, 0x32, 0xFD, 0x27]))
        )

        self.assertEqual(fan.humidity, "50")
        self.assertEqual(fan._last_response_param_ids, {0x0025})
        self.assertEqual(fan._last_unsupported_param_ids, {0x0027})

    def test_parse_response_applies_page_to_unsupported_parameter_id(self):
        fan = Fan("192.0.2.1")

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFF, 0x01, 0xFD, 0x01, 0x04, 0x05])
            )
        )

        self.assertEqual(fan._last_raw_response_param_ids, {0x0104})
        self.assertEqual(fan._last_response_param_ids, set())
        self.assertEqual(fan._last_unsupported_param_ids, {0x0101})

    def test_parse_response_keeps_page_for_following_parameters(self):
        fan = Fan("192.0.2.1")

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFF, 0x01, 0x04, 0x05, 0x05, 0x06])
            )
        )

        self.assertEqual(fan.unknown_params, {0x0104: "05", 0x0105: "06"})
        self.assertEqual(fan._last_raw_response_param_ids, {0x0104, 0x0105})
        self.assertEqual(fan._last_response_param_ids, set())

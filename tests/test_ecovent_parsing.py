"""Regression tests for robust EcoVent packet parsing."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload


class ParseRobustnessTest(unittest.TestCase):
    def test_direct_parse_response_keeps_eager_store_behavior(self):
        fan = Fan("192.0.2.1")

        self.assertTrue(
            fan.parse_response(packet_with_payload([0x01, 0x01, 0x02, 0x03]))
        )
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan.speed, "high")

    def test_profile_rows_decode_after_unit_type_regardless_of_wire_order(self):
        payloads = (
            bytes.fromhex("fe02b906001437"),
            bytes.fromhex("1437fe02b90600"),
        )

        for payload in payloads:
            with self.subTest(payload=payload.hex()):
                fan = Fan("192.0.2.1")
                fan.unit_type = "0500"

                self.assertTrue(fan.parse_response(packet_with_payload(payload)))
                self.assertEqual(fan.profile_key, "extract_fan")
                self.assertEqual(fan.humidity_treshold, "55")
                self.assertIsNone(fan.relay_sensor_state)
                self.assertEqual(fan._last_response_param_ids, {0x0014, 0x00B9})

        vento = Fan("192.0.2.1")
        vento.unit_type = "0500"
        self.assertTrue(vento.parse_response(packet_with_payload([0x14, 0x01])))
        self.assertEqual(vento.profile_key, "vento")
        self.assertEqual(vento.relay_sensor_state, "on")

    def test_malformed_profile_row_rejects_all_rows_from_the_response(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"

        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0xFE, 0x03, 0xB9, 0x00, 0x06, 0x00, 0x14, 0x01]
                )
            )
        )

        self.assertEqual(fan.profile_key, "vento")
        self.assertIsNone(fan.relay_sensor_state)
        self.assertIsNone(fan.humidity_treshold)
        self.assertEqual(fan.unknown_params, {0x00B9: "000600"})
        self.assertEqual(fan._last_response_param_ids, set())

    def test_breezy_screen_off_times_reject_invalid_clock_components(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"

        for param, attribute in (
            (0x08, "screen_off_start_time"),
            (0x09, "screen_off_end_time"),
        ):
            with self.subTest(param=param):
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [0xFF, 0x04, 0xFE, 0x02, param, 0x3B, 0x17]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), "23:59")

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [0xFF, 0x04, 0xFE, 0x02, param, 0x3C, 0x17]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), "23:59")
                self.assertEqual(fan.unknown_params[0x0400 + param], "3c17")
                self.assertNotIn(0x0400 + param, fan._last_response_param_ids)

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

    def test_enum_rows_reject_noncanonical_value_width(self):
        cases = (
            (0x0001, "state", "on"),
            (0x0002, "speed", "low"),
            (0x00B7, "airflow", "heat_recovery"),
        )

        for parameter, attribute, expected in cases:
            with self.subTest(parameter=parameter):
                fan = Fan("192.0.2.1")
                low_byte = parameter & 0xFF
                prefix = [0xFF, parameter >> 8] if parameter > 0xFF else []
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([*prefix, low_byte, 0x01])
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [*prefix, 0xFE, 0x02, low_byte, 0x00, 0x01]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)
                self.assertEqual(fan.unknown_params, {parameter: "0001"})
                self.assertEqual(fan._last_response_param_ids, set())

    def test_scalar_rows_reject_noncanonical_value_width(self):
        cases = (
            (0x0019, "humidity_treshold", 55, "55"),
            (0x0044, "man_speed", 128, 50),
            (0x0066, "boost_time", 15, "15 m"),
            (0x00B8, "analogV_treshold", 50, "50"),
        )

        for parameter, attribute, value, expected in cases:
            with self.subTest(parameter=parameter):
                fan = Fan("192.0.2.1")
                low_byte = parameter & 0xFF
                prefix = [0xFF, parameter >> 8] if parameter > 0xFF else []
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([*prefix, low_byte, value])
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [*prefix, 0xFE, 0x02, low_byte, 0x01, 0x01]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)
                self.assertEqual(fan.unknown_params, {parameter: "0101"})
                self.assertEqual(fan._last_response_param_ids, set())

    def test_profile_scalars_reject_noncanonical_value_width(self):
        cases = (
            ("1100", 0x001A, "co2_treshold", [0x20, 0x03], 800),
            ("1100", 0x0129, "recovery_efficiency", [0x58], 88),
            ("0d00", 0x031F, "air_quality_treshold", [0xC8, 0x00], 200),
        )

        for unit_type, parameter, attribute, value, expected in cases:
            with self.subTest(parameter=parameter):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type
                low_byte = parameter & 0xFF
                prefix = [0xFF, parameter >> 8] if parameter > 0xFF else []
                encoded_value = (
                    [*prefix, low_byte, *value]
                    if len(value) == 1
                    else [*prefix, 0xFE, len(value), low_byte, *value]
                )
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(encoded_value)
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)

                malformed = [0x00, *value]
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [*prefix, 0xFE, len(malformed), low_byte, *malformed]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), expected)
                self.assertEqual(
                    fan.unknown_params, {parameter: bytes(malformed).hex()}
                )
                self.assertEqual(fan._last_response_param_ids, set())

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

    def test_filter_countdown_rejects_days_beyond_profile_limit(self):
        cases = (
            ("0500", [0, 0, 181], [0, 0, 182], "181d 0h 0m "),
            ("1100", [0, 0, 0x6D, 0x01], [0, 0, 0x6E, 0x01], "365d 0h 0m "),
            ("0200", [0, 0, 0x6D, 0x01], [0, 0, 0x6E, 0x01], "365d 0h 0m "),
        )

        for unit_type, valid, invalid, expected in cases:
            with self.subTest(unit_type=unit_type):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([0xFE, len(valid), 0x64, *valid])
                    )
                )
                self.assertEqual(fan.filter_timer_countdown, expected)

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([0xFE, len(invalid), 0x64, *invalid])
                    )
                )
                self.assertEqual(fan.filter_timer_countdown, expected)
                self.assertEqual(fan.unknown_params, {0x0064: bytes(invalid).hex()})
                self.assertEqual(fan._last_response_param_ids, set())

    def test_filter_countdown_rejects_wrong_width_after_profile_discovery(self):
        cases = (
            ("0500", [0, 0, 181], [0, 0, 181, 0], "181d 0h 0m "),
            ("1100", [0, 0, 181, 0], [0, 0, 181], "181d 0h 0m "),
            ("0200", [0, 0, 181, 0], [0, 0, 181], "181d 0h 0m "),
        )

        for unit_type, valid, invalid, expected in cases:
            with self.subTest(unit_type=unit_type):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([0xFE, len(valid), 0x64, *valid])
                    )
                )
                self.assertEqual(fan.filter_timer_countdown, expected)

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([0xFE, len(invalid), 0x64, *invalid])
                    )
                )
                self.assertEqual(fan.filter_timer_countdown, expected)
                self.assertEqual(fan.unknown_params, {0x0064: bytes(invalid).hex()})
                self.assertEqual(fan._last_response_param_ids, set())

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

    def test_valid_known_param_clears_its_stale_malformed_diagnostic(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x03, 0x24, 0x01, 0x02, 0x03])
            )
        )
        self.assertEqual(fan.unknown_params, {0x0024: "010203"})

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x02, 0x24, 0x54, 0x0D])
            )
        )
        self.assertEqual(fan.battery_voltage, "3412 mV")
        self.assertEqual(fan.unknown_params, {})

    def test_documented_scalar_ranges_reject_invalid_device_values(self):
        cases = (
            ("0500", 0x0019, "humidity_treshold", [40], [39], "40"),
            (
                "0500",
                0x0024,
                "battery_voltage",
                [0x88, 0x13],
                [0x89, 0x13],
                "5000 mV",
            ),
            ("0500", 0x0025, "humidity", [100], [101], "100"),
            ("0500", 0x002D, "analogV", [100], [101], "100"),
            (
                "0500",
                0x0063,
                "filter_timer_setpoint",
                [0x6D, 0x01],
                [0x6E, 0x01],
                "365 d",
            ),
            ("0500", 0x0066, "boost_time", [60], [61], "60 m"),
            ("0500", 0x00B8, "analogV_treshold", [5], [4], "5"),
            ("0500", 0x003A, "supply_speed_low", [10], [9], 4),
            ("0600", 0x0018, "max_speed_setpoint", [30], [29], 30),
            ("0600", 0x001A, "silent_speed_setpoint", [100], [101], 100),
            (
                "0600",
                0x001B,
                "interval_ventilation_speed_setpoint",
                [30],
                [29],
                30,
            ),
            (
                "0600",
                0x0004,
                "fan1_speed",
                [0x70, 0x17],
                [0x71, 0x17],
                "6000",
            ),
            ("0600", 0x0014, "humidity_treshold", [80], [81], "80"),
            ("0600", 0x0016, "temperature_treshold", [36], [37], "36"),
            ("0600", 0x0023, "boost_time", [3], [1], "15 m"),
            ("0600", 0x0024, "turn_on_delay_timer", [2], [3], "5 m"),
            ("1100", 0x0019, "humidity_treshold", [80], [81], "80"),
            (
                "1100",
                0x001A,
                "co2_treshold",
                [0xD0, 0x07],
                [0xD1, 0x07],
                2000,
            ),
            ("1100", 0x0027, "co2", [0xD0, 0x07], [0xD1, 0x07], 2000),
            ("1100", 0x003A, "supply_speed_low", [10], [9], 10),
            ("1100", 0x0044, "man_speed", [10], [9], 10),
            (
                "1100",
                0x004A,
                "fan1_speed",
                [0x88, 0x13],
                [0x89, 0x13],
                "5000",
            ),
            (
                "1100",
                0x0063,
                "filter_timer_setpoint",
                [70, 0],
                [69, 0],
                "70 d",
            ),
            ("1100", 0x0129, "recovery_efficiency", [100], [101], 100),
            ("1100", 0x031F, "voc_treshold", [250, 0], [251, 0], 250),
            ("1100", 0x0320, "voc", [0xF4, 0x01], [0xF5, 0x01], 500),
            ("1100", 0x0400, "screen_brightness", [100], [101], 100),
            ("0d00", 0x0019, "humidity_treshold", [80], [81], "80"),
            (
                "0d00",
                0x004B,
                "fan1_speed",
                [0x88, 0x13],
                [0x89, 0x13],
                "5000",
            ),
            (
                "0d00",
                0x031F,
                "air_quality_treshold",
                [0xF4, 0x01],
                [0xF5, 0x01],
                500,
            ),
            ("0d00", 0x0320, "air_quality", [0xF4, 0x01], [0xF5, 0x01], 500),
            ("0d00", 0x0325, "temperature_treshold", [36], [37], "36"),
            ("0200", 0x003A, "supply_speed_low", [100], [101], 100),
            ("0200", 0x0040, "supply_speed_4", [100], [101], 100),
            (
                "0200",
                0x0063,
                "filter_timer_setpoint",
                [70, 0],
                [71, 0],
                "70 d",
            ),
            ("0200", 0x0063, "filter_timer_setpoint", [0, 0], [5, 0], "0 d"),
            ("0200", 0x0066, "boost_time", [60], [61], "60 m"),
        )

        for unit_type, parameter, attribute, valid, invalid, expected in cases:
            with self.subTest(parameter=parameter):
                fan = Fan("192.0.2.1")
                fan.unit_type = unit_type
                prefix = [0xFF, parameter >> 8] if parameter > 0xFF else []
                low_byte = parameter & 0xFF

                def row(value):
                    if len(value) == 1:
                        return [*prefix, low_byte, *value]
                    return [*prefix, 0xFE, len(value), low_byte, *value]

                self.assertTrue(
                    fan.parse_response(packet_with_payload(row(valid)))
                )
                self.assertEqual(getattr(fan, attribute), expected)

                self.assertTrue(
                    fan.parse_response(packet_with_payload(row(invalid)))
                )
                self.assertEqual(getattr(fan, attribute), expected)
                self.assertEqual(
                    fan.unknown_params,
                    {parameter: bytes(invalid).hex()},
                )
                self.assertEqual(fan._last_response_param_ids, set())

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

        invalid_date = [0x00, 0x03, 0x1F, 0x04, 0xEA, 0x07]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0xFE, len(invalid_date), 0x86, *invalid_date]
                )
            )
        )
        self.assertEqual(fan.firmware, "0.3 2020-08-26")
        self.assertEqual(fan.unknown_params, {0x0086: bytes(invalid_date).hex()})
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

    def test_weekly_schedule_rejects_semantically_invalid_fields(self):
        invalid_values = (
            [0x00, 0x01, 0x01, 0x00, 0x00, 0x06],
            [0x08, 0x01, 0x01, 0x00, 0x00, 0x06],
            [0x01, 0x00, 0x01, 0x00, 0x00, 0x06],
            [0x01, 0x05, 0x01, 0x00, 0x00, 0x06],
            [0x01, 0x01, 0xFF, 0x00, 0x00, 0x06],
            [0x01, 0x01, 0x01, 0x00, 0x3C, 0x06],
            [0x01, 0x01, 0x01, 0x00, 0x00, 0x18],
        )

        for malformed in invalid_values:
            with self.subTest(value=bytes(malformed).hex()):
                fan = Fan("192.0.2.1")
                fan.unit_type = "1100"

                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [0xFE, len(malformed), 0x77, *malformed]
                        )
                    )
                )
                self.assertIsNone(fan.weekly_schedule_setup)
                self.assertEqual(
                    fan.unknown_params, {0x0077: bytes(malformed).hex()}
                )
                self.assertEqual(fan._last_response_param_ids, set())

        valid = [0x01, 0x01, 0x01, 0x00, 0x00, 0x06]
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x06, 0x77, *valid]))
        )
        self.assertEqual(
            fan._weekly_schedule_setup_record.end_time.isoformat(), "06:00:00"
        )

    def test_vento_schedule_rejects_profile_speed_and_final_end_mismatches(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        valid = [0x01, 0x01, 0x03, 0x00, 0x00, 0x06]
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x06, 0x77, *valid]))
        )
        previous = fan.weekly_schedule_setup

        for malformed in (
            [0x01, 0x01, 0x05, 0x00, 0x00, 0x06],
            [0x01, 0x04, 0x03, 0x00, 0x00, 0x06],
        ):
            with self.subTest(value=bytes(malformed).hex()):
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload([0xFE, 0x06, 0x77, *malformed])
                    )
                )
                self.assertEqual(fan.weekly_schedule_setup, previous)
                self.assertEqual(
                    fan.unknown_params, {0x0077: bytes(malformed).hex()}
                )
                self.assertEqual(fan._last_response_param_ids, set())

    def test_compound_timers_reject_out_of_range_clock_fields(self):
        cases = (
            (0x000B, [0x3B, 0x3B, 0x17], [0x3C, 0x00, 0x00], "timer_counter"),
            (
                0x0064,
                [0x11, 0x08, 0x48],
                [0x3C, 0x00, 0x00],
                "filter_timer_countdown",
            ),
            (
                0x007E,
                [0x11, 0x08, 0x2C, 0x01],
                [0x3C, 0x00, 0x00, 0x00],
                "machine_hours",
            ),
        )
        for parameter, valid, malformed, attribute in cases:
            with self.subTest(parameter=f"0x{parameter:04X}"):
                fan = Fan("192.0.2.1")
                for value in (valid, malformed):
                    payload = []
                    if parameter > 0xFF:
                        payload.extend([0xFF, parameter >> 8])
                    payload.extend(
                        [0xFE, len(value), parameter & 0xFF, *value]
                    )
                    self.assertTrue(fan.parse_response(packet_with_payload(payload)))

                expected = {
                    "timer_counter": "23h 59m 59s ",
                    "filter_timer_countdown": "72d 8h 17m ",
                    "machine_hours": "300d 8h 17m ",
                }[attribute]
                self.assertEqual(getattr(fan, attribute), expected)
                self.assertEqual(
                    fan.unknown_params, {parameter: bytes(malformed).hex()}
                )
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

    def test_identity_rows_reject_noncanonical_lengths(self):
        fan = Fan("192.0.2.1")
        controller_id = b"VENTO-ID-0000000"

        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x10, 0x7C, *controller_id])
            )
        )
        self.assertEqual(fan.device_search, controller_id.decode())

        short_id = controller_id[:-1]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(short_id), 0x7C, *short_id])
            )
        )
        self.assertEqual(fan.device_search, controller_id.decode())
        self.assertEqual(fan.unknown_params, {0x007C: short_id.hex()})

        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x06, 0x00]))
        )
        self.assertEqual(fan.profile_key, "extract_fan")

        malformed_type = [0x00, 0x06, 0x00]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0xFE, len(malformed_type), 0xB9, *malformed_type]
                )
            )
        )
        self.assertEqual(fan.profile_key, "extract_fan")
        self.assertEqual(fan.unknown_params[0x00B9], bytes(malformed_type).hex())
        self.assertEqual(fan._last_response_param_ids, set())

    def test_extract_rtc_rejects_noncanonical_length(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan.rtc_time = "4d0e00"

        malformed = [0xFF, 0xFF, 0xFF, 0xFF]
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, len(malformed), 0x21, *malformed])
            )
        )
        self.assertEqual(fan.rtc_time, "01:01:01")
        self.assertEqual(fan.unknown_params, {0x0021: bytes(malformed).hex()})
        self.assertEqual(fan._last_response_param_ids, set())

        invalid_seconds = (
            list((24 * 60 * 60).to_bytes(3, byteorder="little")),
            [0x90, 0x5F, 0x01],
        )
        for invalid in invalid_seconds:
            self.assertTrue(
                fan.parse_response(
                    packet_with_payload([0xFE, len(invalid), 0x21, *invalid])
                )
            )
            self.assertEqual(fan.rtc_time, "01:01:01")
            self.assertEqual(fan.unknown_params, {0x0021: bytes(invalid).hex()})
            self.assertEqual(fan._last_response_param_ids, set())

    def test_vento_rtc_rejects_invalid_clock_and_calendar_fields(self):
        invalid_rows = (
            (0x006F, [0x3C, 0x00, 0x00]),
            (0x006F, [0x00, 0x3C, 0x00]),
            (0x006F, [0x00, 0x00, 0x18]),
            (0x0070, [0x00, 0x01, 0x01, 0x1A]),
            (0x0070, [0x01, 0x00, 0x01, 0x1A]),
            (0x0070, [0x01, 0x08, 0x01, 0x1A]),
            (0x0070, [0x1F, 0x01, 0x04, 0x1A]),
            (0x0070, [0x17, 0x01, 0x04, 0x1A]),
        )

        for parameter, value in invalid_rows:
            with self.subTest(parameter=parameter, value=bytes(value).hex()):
                fan = Fan("192.0.2.1")
                fan.unit_type = "0500"
                payload = [0xFE, len(value), parameter & 0xFF, *value]

                self.assertTrue(fan.parse_response(packet_with_payload(payload)))
                self.assertEqual(
                    fan.unknown_params, {parameter: bytes(value).hex()}
                )
                self.assertEqual(fan._last_response_param_ids, set())

        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [
                        0xFE,
                        0x03,
                        0x6F,
                        0x1E,
                        0x2D,
                        0x13,
                        0xFE,
                        0x04,
                        0x70,
                        0x17,
                        0x04,
                        0x04,
                        0x1A,
                    ]
                )
            )
        )
        self.assertEqual(fan.rtc_time, "19:45:30")
        self.assertEqual(fan.rtc_date, "2026-04-23")

    def test_vento_mode_timers_reject_invalid_clock_fields(self):
        for parameter in (0x0302, 0x0303):
            with self.subTest(parameter=f"0x{parameter:04X}"):
                fan = Fan("192.0.2.1")
                valid = [0x3B, 0x17]
                valid_payload = [
                    0xFF,
                    parameter >> 8,
                    0xFE,
                    len(valid),
                    parameter & 0xFF,
                    *valid,
                ]
                self.assertTrue(fan.parse_response(packet_with_payload(valid_payload)))
                attribute = (
                    "night_mode_timer" if parameter == 0x0302 else "party_mode_timer"
                )
                self.assertEqual(getattr(fan, attribute), "23h 59m")

                for malformed in ([0x3C, 0x00], [0x00, 0x18]):
                    malformed_payload = [
                        0xFF,
                        parameter >> 8,
                        0xFE,
                        len(malformed),
                        parameter & 0xFF,
                        *malformed,
                    ]
                    self.assertTrue(
                        fan.parse_response(packet_with_payload(malformed_payload))
                    )
                    self.assertEqual(getattr(fan, attribute), "23h 59m")
                    self.assertEqual(
                        fan.unknown_params, {parameter: bytes(malformed).hex()}
                    )
                    self.assertEqual(fan._last_response_param_ids, set())

    def test_arc_silent_times_reject_invalid_clock_fields(self):
        for parameter, attribute in (
            (0x0318, "silent_mode_start_time"),
            (0x0319, "silent_mode_end_time"),
        ):
            with self.subTest(parameter=f"0x{parameter:04X}"):
                fan = Fan("192.0.2.1")
                fan.unit_type = "0D00"
                valid = [0x3B, 0x3B, 0x17]
                self.assertTrue(
                    fan.parse_response(
                        packet_with_payload(
                            [0xFF, 0x03, 0xFE, 0x03, parameter & 0xFF, *valid]
                        )
                    )
                )
                self.assertEqual(getattr(fan, attribute), "23h 59m 59s ")

                for malformed in (
                    [0x3C, 0x00, 0x00],
                    [0x00, 0x3C, 0x00],
                    [0x00, 0x00, 0x18],
                ):
                    self.assertTrue(
                        fan.parse_response(
                            packet_with_payload(
                                [
                                    0xFF,
                                    0x03,
                                    0xFE,
                                    0x03,
                                    parameter & 0xFF,
                                    *malformed,
                                ]
                            )
                        )
                    )
                    self.assertEqual(getattr(fan, attribute), "23h 59m 59s ")
                    self.assertEqual(
                        fan.unknown_params, {parameter: bytes(malformed).hex()}
                    )
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

    def test_parse_response_tracks_present_and_unsupported_ids_separately(self):
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

"""Tests for EcoVent protocol diagnostics helpers."""

from urllib.parse import parse_qs, urlparse
import unittest

from ecovent_test_helpers import Fan

from protocol_diagnostics import (
    _report_version,
    hardware_profile_mismatch_state,
    hardware_profile_mismatch_issue_body,
    hardware_profile_mismatch_issue_url,
    reportable_hardware_profile_mismatch_param_ids,
    unsupported_optional_poll_parameter_details,
    unsupported_optional_poll_parameter_summary,
)


class ProtocolDiagnosticsTest(unittest.TestCase):
    def test_firmware_change_resets_only_previous_identity_capabilities(self):
        fan = Fan("192.0.2.1")
        fan._unsupported_optional_poll_params = {0x003A, 0x0063}
        fan._optional_read_backoff = {0x003A: 7}
        fan._bulk_read_supported = False

        fan.firmware = "00031A08E407"
        self.assertEqual(fan._unsupported_optional_poll_params, {0x003A, 0x0063})
        self.assertEqual(fan._optional_read_backoff, {0x003A: 7})
        self.assertFalse(fan._bulk_read_supported)

        fan.firmware = "00031A08E407"
        self.assertEqual(fan._unsupported_optional_poll_params, {0x003A, 0x0063})
        self.assertEqual(fan._optional_read_backoff, {0x003A: 7})
        self.assertFalse(fan._bulk_read_supported)

        fan.firmware = "00040101EA07"
        self.assertEqual(fan.firmware, "0.4 2026-01-01")
        self.assertEqual(fan._unsupported_optional_poll_params, set())
        self.assertEqual(fan._optional_read_backoff, {})
        self.assertIsNone(fan._bulk_read_supported)

    def test_unit_type_change_resets_same_profile_capabilities(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._unsupported_optional_poll_params = {0x003A, 0x0063}
        fan._optional_read_backoff = {0x003A: 7}
        fan._bulk_read_supported = False

        fan.unit_type = "0300"
        self.assertEqual(fan._unsupported_optional_poll_params, {0x003A, 0x0063})
        self.assertEqual(fan._optional_read_backoff, {0x003A: 7})
        self.assertFalse(fan._bulk_read_supported)

        fan.unit_type = "0500"
        self.assertEqual(fan.profile_key, "vento")
        self.assertEqual(fan._unsupported_optional_poll_params, set())
        self.assertEqual(fan._optional_read_backoff, {})
        self.assertIsNone(fan._bulk_read_supported)

    def test_profile_change_resets_learned_capabilities(self):
        fan = Fan("192.0.2.1")
        fan._unsupported_optional_poll_params = {0x003A, 0x0063}
        fan._optional_read_backoff = {0x003A: 7}
        fan._bulk_read_supported = False

        fan._set_device_profile("breezy")
        self.assertEqual(fan.profile_key, "breezy")
        self.assertEqual(fan._unsupported_optional_poll_params, set())
        self.assertEqual(fan._optional_read_backoff, {})
        self.assertIsNone(fan._bulk_read_supported)

    def test_repair_state_changes_with_identity_even_when_rows_match(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan.firmware = "00031A08E407"
        fan._unsupported_optional_poll_params = {0x0083}

        old_state = hardware_profile_mismatch_state(fan)
        self.assertEqual(
            old_state,
            ("vento", 0x0500, "0.3 2020-08-26", frozenset({0x0083})),
        )

        fan.firmware = "00040101EA07"
        fan._unsupported_optional_poll_params = {0x0083}
        new_state = hardware_profile_mismatch_state(fan)

        self.assertNotEqual(old_state, new_state)
        self.assertEqual(new_state[-1], old_state[-1])

    def test_unsupported_optional_details_are_public_safe(self):
        fan = Fan("192.0.2.1", password="secret", fan_id="known-device")
        fan._set_device_profile("breezy")
        fan._unit_type_id = 0x1400
        fan._unit_type = Fan.device_models[0x1400].display_name
        fan._firmware = "1.2.3"
        fan._unsupported_optional_poll_params = {0x001F, 0x0027, 0x0320}

        self.assertEqual(
            unsupported_optional_poll_parameter_details(fan),
            (
                {"id": "0x001F", "name": "outdoor_temperature"},
                {"id": "0x0027", "name": "co2"},
                {"id": "0x0320", "name": "voc"},
            ),
        )
        self.assertEqual(
            unsupported_optional_poll_parameter_summary(fan),
            "0x001F (outdoor_temperature), 0x0027 (co2), 0x0320 (voc)",
        )

        body = hardware_profile_mismatch_issue_body(fan)
        self.assertIn("Integration profile: `breezy`", body)
        self.assertIn(
            f"EcoVent V2 integration version: `{_report_version()}`", body
        )
        self.assertNotIn("loc_", body)
        self.assertIn("Firmware: `1.2.3`", body)
        self.assertIn("`0x0027` `co2`", body)
        self.assertIn("this one EcoVent config entry", body)
        self.assertIn("distinct model, firmware, and unsupported-register set", body)
        self.assertIn("Device id: `known`", body)
        self.assertNotIn("secret", body)
        self.assertNotIn("192.0.2.1", body)
        self.assertNotIn("known-device", body)

        url = hardware_profile_mismatch_issue_url(fan)
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "github.com")
        self.assertEqual(parsed.path, "/gody01/ecovent_v2/issues/new")
        self.assertIn("Hardware profile mismatch", query["title"][0])
        self.assertIn("0x1400 firmware 1.2.3", query["title"][0])
        self.assertIn("`0x0320` `voc`", query["body"][0])

    def test_issue78_vento_a50_rows_do_not_request_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan.firmware = "0004140CE307"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0063,
        }

        self.assertEqual(fan.firmware, "0.4 2019-12-20")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue82_vento_a50_humidity_variant_is_known(self):
        """The reported 0x0300 firmware variant must not reopen a Repair."""
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan.firmware = "0007040AE507"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0063,
        }

        self.assertEqual(fan.firmware, "0.7 2021-10-04")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue84_newer_vento_firmware_only_rejects_speed_rows(self):
        """The newer reported firmware keeps the filter timer supported."""
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._firmware = "0.9 2024-07-08"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue94_vento_old_firmware_filter_timer_row_is_known(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._firmware = "0.6 2021-05-17"
        fan._unsupported_optional_poll_params = {0x0063}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue94_vento_old_firmware_extra_row_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._firmware = "0.6 2021-05-17"
        fan._unsupported_optional_poll_params = {0x0063, 0x00B7}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x00B7})
        )

    def test_issue97_vento_old_firmware_speed_rows_are_known(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan.firmware = "00061105E507"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
        }

        self.assertEqual(fan.firmware, "0.6 2021-05-17")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue97_vento_old_firmware_extra_row_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan.firmware = "00061105E507"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0083,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )

    def test_unknown_filter_timer_rejection_still_requests_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._firmware = "0.9 2024-07-08"
        fan._unsupported_optional_poll_params = {0x0063}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0063})
        )

    def test_issue88_freshpoint_160e_standard_rows_do_not_request_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.firmware = "000C0109E907"
        fan._unsupported_optional_poll_params = {
            0x0011,
            0x001A,
            0x0025,
            0x0027,
            0x0129,
            0x0315,
            0x031F,
            0x0320,
            0x0403,
            0x0404,
            0x0405,
        }

        self.assertEqual(fan.firmware, "0.12 2025-09-01")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_freshpoint_160e_unknown_firmware_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan._firmware = "0.13 2026-01-01"
        fan._unsupported_optional_poll_params = {
            0x0011,
            0x001A,
            0x0025,
            0x0027,
            0x0129,
            0x0315,
            0x031F,
            0x0320,
            0x0403,
            0x0404,
            0x0405,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan),
            frozenset(fan._unsupported_optional_poll_params),
        )

    def test_freshpoint_160e_extra_rejection_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan._firmware = "0.12 2025-09-01"
        fan._unsupported_optional_poll_params = {
            0x0011,
            0x001A,
            0x0025,
            0x0027,
            0x0129,
            0x0315,
            0x031F,
            0x0320,
            0x0403,
            0x0404,
            0x0405,
            0x00B7,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x00B7})
        )

    def test_issue90_vento_a30_mini_air_rows_do_not_request_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan.firmware = "00031A08E407"
        fan._unsupported_optional_poll_params = {
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

        self.assertEqual(fan.firmware, "0.3 2020-08-26")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue95_vento_a30_firmware_05_rows_do_not_request_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan.firmware = "0005040AE507"
        fan._unsupported_optional_poll_params = {
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

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_issue95_vento_a30_extra_row_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan.firmware = "0005040AE507"
        fan._unsupported_optional_poll_params = {
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
            0x0083,
            0x00B8,
            0x0305,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )

    def test_issue92_extract_fan_motion_rows_do_not_request_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan.firmware = "02021006E607"
        fan._unsupported_optional_poll_params = {0x000B, 0x0012}

        self.assertEqual(fan.firmware, "2.2 2022-06-16")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_vento_a30_mini_air_unknown_firmware_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan._firmware = "0.4 2026-01-01"
        fan._unsupported_optional_poll_params = {
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

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan),
            frozenset(fan._unsupported_optional_poll_params),
        )

    def test_vento_a30_mini_air_extra_rejection_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0500"
        fan._firmware = "0.3 2020-08-26"
        fan._unsupported_optional_poll_params = {
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
            0x0083,
            0x00B8,
            0x0305,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )

    def test_extract_fan_unknown_firmware_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan._firmware = "2.3 2026-01-01"
        fan._unsupported_optional_poll_params = {0x000B, 0x0012}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan),
            frozenset({0x000B, 0x0012}),
        )

    def test_extract_fan_extra_rejection_still_requests_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0600"
        fan._firmware = "2.2 2022-06-16"
        fan._unsupported_optional_poll_params = {0x000B, 0x0012, 0x000C}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x000C})
        )

    def test_issue80_vento_duo_a30_rows_do_not_request_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0400"
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0063,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_unknown_unit_type_still_requests_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan._set_device_profile("vento")
        fan._unsupported_optional_poll_params = {
            0x003A,
            0x003B,
            0x003C,
            0x003D,
            0x003E,
            0x003F,
            0x0063,
        }

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan),
            frozenset({0x003A, 0x003B, 0x003C, 0x003D, 0x003E, 0x003F, 0x0063}),
        )

    def test_unknown_extra_unsupported_rows_still_request_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0300"
        fan._unsupported_optional_poll_params = {0x003A, 0x0083}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )
        self.assertEqual(
            unsupported_optional_poll_parameter_summary(fan, frozenset({0x0083})),
            "0x0083 (alarm_status)",
        )

"""Tests for EcoVent protocol diagnostics helpers."""

from urllib.parse import parse_qs, urlparse
import unittest

from ecovent_test_helpers import Fan

from protocol_diagnostics import (
    hardware_profile_mismatch_issue_body,
    hardware_profile_mismatch_issue_url,
    reportable_hardware_profile_mismatch_param_ids,
    unsupported_optional_poll_parameter_details,
    unsupported_optional_poll_parameter_summary,
)


class ProtocolDiagnosticsTest(unittest.TestCase):
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
        self.assertIn("Firmware: `1.2.3`", body)
        self.assertIn("`0x0027` `co2`", body)
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
        self.assertIn("`0x0320` `voc`", query["body"][0])

    def test_issue78_vento_a50_rows_do_not_request_mismatch_report(self):
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
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_unknown_unsupported_rows_still_request_mismatch_report(self):
        fan = Fan("192.0.2.1")
        fan._set_device_profile("vento")
        fan._unsupported_optional_poll_params = {0x003A, 0x0083}

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )
        self.assertEqual(
            unsupported_optional_poll_parameter_summary(fan, frozenset({0x0083})),
            "0x0083 (alarm_status)",
        )

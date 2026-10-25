"""Regression tests for PR #127: RTC rows in the breezy profile.

Freshpoint 160-E (0x1100) answers 0x006F/0x0070, which enables the existing
automatic clock synchronization for breezy devices. The profile must declare
both rows so supports_parameter/set_rtc_datetime work, matching the vento
profile behavior.
"""

import unittest
from datetime import datetime

from ecovent_test_helpers import Fan, packet_with_payload

BREEZY_UNIT_TYPE_PROBE = [0xFE, 0x02, 0xB9, 0x11, 0x00]


def _breezy_fan():
    fan = Fan("192.0.2.1")
    assert fan.parse_response(packet_with_payload(BREEZY_UNIT_TYPE_PROBE))
    assert fan.profile_key == "breezy"
    return fan


class BreezyRtcParamsTest(unittest.TestCase):
    def test_breezy_profile_declares_rtc_rows(self):
        fan = _breezy_fan()
        self.assertTrue(fan.profile_supports_parameter("rtc_time"))
        self.assertTrue(fan.profile_supports_parameter("rtc_date"))

    def test_breezy_profile_supports_rtc_before_any_rejection(self):
        fan = _breezy_fan()
        self.assertTrue(fan.supports_parameter("rtc_time"))
        self.assertTrue(fan.supports_parameter("rtc_date"))

    def test_breezy_rejected_rtc_disables_sync_probe(self):
        fan = _breezy_fan()
        fan._unsupported_optional_poll_params = {0x006F, 0x0070}
        self.assertFalse(fan.supports_parameter("rtc_time"))
        self.assertFalse(fan.supports_parameter("rtc_date"))
        self.assertFalse(fan.set_rtc_datetime(datetime(2026, 4, 23, 19, 45, 30)))

    def test_breezy_profile_can_write_rtc_datetime(self):
        fan = _breezy_fan()
        calls = []

        def fake_send_encoded_command(
            command,
            encoded_params,
            retries=10,
            include_extra_write_parameters=True,
        ):
            calls.append((command, encoded_params, retries))
            return True

        fan.send_encoded_command = fake_send_encoded_command

        self.assertTrue(fan.set_rtc_datetime(datetime(2026, 4, 23, 19, 45, 30)))
        self.assertEqual(
            calls,
            [(fan.func["write_return"], "fe036f1e2d13fe04701704041a", 10)],
        )


if __name__ == "__main__":
    unittest.main()

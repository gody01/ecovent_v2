"""Regression tests for the Breezy Eco 160 firmware reported in issue #139."""

import unittest

from ecovent_test_helpers import Fan, packet_with_payload
from protocol_diagnostics import reportable_hardware_profile_mismatch_param_ids

ISSUE139_REJECTED_ROWS = frozenset(
    {
        0x0011,
        0x001A,
        0x0025,
        0x0027,
        0x0315,
        0x031F,
        0x0320,
        0x0403,
        0x0404,
        0x0405,
    }
)


def _issue139_fan(
    rejected=ISSUE139_REJECTED_ROWS,
    *,
    unit_type="1100",
    firmware="0.7 2023-10-02",
):
    fan = Fan("192.0.2.1")
    fan._set_device_profile("breezy")
    fan.unit_type = unit_type
    fan._firmware = firmware
    fan._unsupported_optional_poll_params = set(rejected)
    return fan


class Issue139BreezyEco160Test(unittest.TestCase):
    def test_exact_rejected_rows_do_not_request_a_report(self):
        fan = _issue139_fan()

        self.assertEqual(fan._unit_type_id, 0x1100)
        self.assertEqual(fan.firmware, "0.7 2023-10-02")
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )
        self.assertEqual(
            fan.unsupported_optional_poll_parameter_ids(), ISSUE139_REJECTED_ROWS
        )
        # 0x0129 is supported by this firmware and must keep its entity available.
        self.assertNotIn(0x0129, fan.unsupported_optional_poll_parameter_ids())
        self.assertTrue(fan.supports_parameter("recovery_efficiency"))
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFF, 0x01, 0x29, 76]))
        )
        self.assertEqual(fan.recovery_efficiency, 76)

    def test_unexpected_recovery_efficiency_rejection_still_requests_a_report(self):
        fan = _issue139_fan(ISSUE139_REJECTED_ROWS | {0x0129})

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0129})
        )

    def test_extra_rejection_still_requests_a_report(self):
        fan = _issue139_fan(ISSUE139_REJECTED_ROWS | {0x0083})

        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )

    def test_unknown_firmware_or_unit_type_still_requests_a_report(self):
        for fan in (
            _issue139_fan(firmware="0.8 2023-10-02"),
            _issue139_fan(unit_type="1200"),
        ):
            with self.subTest(unit_type=fan._unit_type_id, firmware=fan.firmware):
                self.assertEqual(
                    reportable_hardware_profile_mismatch_param_ids(fan),
                    ISSUE139_REJECTED_ROWS,
                )


if __name__ == "__main__":
    unittest.main()

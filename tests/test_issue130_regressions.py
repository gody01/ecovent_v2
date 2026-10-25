"""Regression tests for issue #130 Freshpoint 200 0x1600 fw 0.12 optional rows."""

import unittest

from ecovent_test_helpers import Fan

from protocol_diagnostics import (
    hardware_profile_mismatch_state,
    reportable_hardware_profile_mismatch_param_ids,
)

ISSUE130_REJECTED_ROWS = frozenset(
    {
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
)


def _issue130_fan(rejected):
    fan = Fan("192.0.2.1")
    fan.unit_type = "1600"
    fan.firmware = "000c0109e907"
    fan._unsupported_optional_poll_params = set(rejected)
    return fan


class Issue130Freshpoint200Test(unittest.TestCase):
    def test_identity_decodes_to_breezy_1600(self):
        fan = _issue130_fan(set())
        self.assertEqual(fan.profile_key, "breezy")
        self.assertEqual(fan._unit_type_id, 0x1600)
        self.assertEqual(fan.firmware, "0.12 2025-09-01")

    def test_exact_rejected_set_requests_no_report(self):
        fan = _issue130_fan(ISSUE130_REJECTED_ROWS)
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )
        self.assertEqual(hardware_profile_mismatch_state(fan)[-1], frozenset())
        # Entities stay hidden via the unsupported set; only the Repair is quiet.
        self.assertEqual(
            fan.unsupported_optional_poll_parameter_ids(), ISSUE130_REJECTED_ROWS
        )

    def test_extra_rejection_still_requests_report(self):
        fan = _issue130_fan(ISSUE130_REJECTED_ROWS | {0x0083})
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan),
            frozenset({0x0083}),
        )

    def test_device_answering_rows_requests_no_report(self):
        fan = _issue130_fan(set())
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )
        self.assertEqual(hardware_profile_mismatch_state(fan)[-1], frozenset())


if __name__ == "__main__":
    unittest.main()

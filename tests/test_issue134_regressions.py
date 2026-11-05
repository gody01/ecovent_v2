"""Regression tests for issue #134 VENTO Expert A30 0x0500 firmware 0.4."""

import unittest

from ecovent_test_helpers import Fan
from protocol_diagnostics import reportable_hardware_profile_mismatch_param_ids

ISSUE134_REJECTED_ROWS = frozenset(
    {
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
)
FW_0_4 = "00041105E507"  # 0.4 2021-05-17
FW_0_9 = "00091105E507"


def _fan(unit_type, firmware, rejected):
    fan = Fan("192.0.2.1")
    fan.unit_type = unit_type
    fan.firmware = firmware
    fan._unsupported_optional_poll_params = set(rejected)
    return fan


class Issue134VentoExpertA30Test(unittest.TestCase):
    def test_identity_decodes_to_vento_0500_fw_0_4(self):
        fan = _fan("0500", FW_0_4, set())
        self.assertEqual(fan.profile_key, "vento")
        self.assertEqual(fan._unit_type_id, 0x0500)
        self.assertEqual(fan.firmware, "0.4 2021-05-17")

    def test_exact_rejected_set_requests_no_report(self):
        fan = _fan("0500", FW_0_4, ISSUE134_REJECTED_ROWS)
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset()
        )

    def test_extra_rejection_still_requests_report(self):
        fan = _fan("0500", FW_0_4, ISSUE134_REJECTED_ROWS | {0x0083})
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(fan), frozenset({0x0083})
        )

    def test_other_firmware_and_unit_types_unchanged(self):
        other_fw = _fan("0500", FW_0_9, ISSUE134_REJECTED_ROWS)
        self.assertEqual(
            reportable_hardware_profile_mismatch_param_ids(other_fw),
            ISSUE134_REJECTED_ROWS,
        )
        other_type = _fan("0400", FW_0_4, ISSUE134_REJECTED_ROWS)
        self.assertNotEqual(
            reportable_hardware_profile_mismatch_param_ids(other_type), frozenset()
        )

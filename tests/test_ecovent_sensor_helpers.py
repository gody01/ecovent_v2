"""Regression tests for Home Assistant sensor helper behavior."""

import unittest

from ecovent_test_helpers import COMPONENT_PATH  # noqa: F401  Ensures sys.path setup.
from sensor_helpers import enum_options_with_value


class SensorEnumOptionsTest(unittest.TestCase):
    def test_keeps_known_enum_options_unchanged(self):
        self.assertEqual(
            enum_options_with_value(["off", "on"], "on"),
            ["off", "on"],
        )

    def test_adds_unknown_current_enum_value(self):
        self.assertEqual(
            enum_options_with_value(["off", "on"], "Unknown beeper 3"),
            ["off", "on", "Unknown beeper 3"],
        )

    def test_preserves_non_enum_without_options(self):
        self.assertIsNone(enum_options_with_value(None, "Unknown beeper 3"))


if __name__ == "__main__":
    unittest.main()

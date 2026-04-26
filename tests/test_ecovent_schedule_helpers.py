"""Regression tests for EcoVent weekly schedule write planning."""

import unittest

from ecovent_test_helpers import COMPONENT_PATH  # noqa: F401  Ensures sys.path setup.
from schedule_helpers import WeeklyScheduleRecord, changed_schedule_records


def schedule_records(day=1):
    """Return one normal four-period day as cached device records."""
    return {
        1: WeeklyScheduleRecord(day, 1, "medium", 6, 0),
        2: WeeklyScheduleRecord(day, 2, "low", 9, 0),
        3: WeeklyScheduleRecord(day, 3, "low", 19, 0),
        4: WeeklyScheduleRecord(day, 4, "low", 0, 0),
    }


class WeeklyScheduleWritePlanTest(unittest.TestCase):
    def test_empty_payload_writes_nothing(self):
        self.assertEqual(changed_schedule_records(1, schedule_records(), []), [])

    def test_unchanged_partial_payload_writes_nothing(self):
        self.assertEqual(
            changed_schedule_records(
                1,
                schedule_records(),
                [{"period": 1, "speed": "Medium", "end": "06:00"}],
            ),
            [],
        )

    def test_single_speed_change_writes_only_that_period(self):
        records = changed_schedule_records(
            1,
            schedule_records(),
            [{"period": 2, "speed": "High"}],
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].period, 2)
        self.assertEqual(records[0].speed, "high")
        self.assertEqual((records[0].end_hour, records[0].end_minute), (9, 0))

    def test_single_time_change_writes_only_that_period(self):
        records = changed_schedule_records(
            1,
            schedule_records(),
            [{"period": 1, "end": "07:00"}],
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].period, 1)
        self.assertEqual(records[0].speed, "medium")
        self.assertEqual((records[0].end_hour, records[0].end_minute), (7, 0))

    def test_multiple_changes_preserve_payload_order_independent_diff(self):
        records = changed_schedule_records(
            1,
            schedule_records(),
            [
                {"period": 3, "speed": "High"},
                {"period": 1, "speed": "Low"},
            ],
        )

        self.assertEqual([(record.period, record.speed) for record in records], [
            (1, "low"),
            (3, "high"),
        ])

    def test_missing_cached_period_fails_before_any_device_write_plan(self):
        current_records = schedule_records()
        del current_records[4]

        with self.assertRaisesRegex(ValueError, "Schedule records not available"):
            changed_schedule_records(
                1,
                current_records,
                [{"period": 1, "speed": "Low"}],
            )

    def test_invalid_chronology_fails_before_any_device_write_plan(self):
        with self.assertRaisesRegex(ValueError, "chronological order"):
            changed_schedule_records(
                1,
                schedule_records(),
                [{"period": 1, "end": "10:00"}],
            )

    def test_invalid_period_fails_before_any_device_write_plan(self):
        with self.assertRaisesRegex(ValueError, "Invalid schedule period"):
            changed_schedule_records(
                1,
                schedule_records(),
                [{"period": 5, "speed": "Low"}],
            )


if __name__ == "__main__":
    unittest.main()

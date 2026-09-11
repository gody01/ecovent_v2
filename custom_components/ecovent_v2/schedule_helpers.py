"""Helpers for EcoVent weekly schedule editing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time


SCHEDULE_DAY_LABELS = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}

SCHEDULE_DAY_OPTIONS = [SCHEDULE_DAY_LABELS[index] for index in range(1, 8)]
SCHEDULE_DAY_TO_INDEX = {label: index for index, label in SCHEDULE_DAY_LABELS.items()}

SCHEDULE_SPEED_LABELS = {
    "standby": "Standby",
    "speed_1": "Speed 1",
    "speed_2": "Speed 2",
    "speed_3": "Speed 3",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "speed_4": "Speed 4",
    "speed_5": "Speed 5",
}

SCHEDULE_SPEED_OPTIONS = list(SCHEDULE_SPEED_LABELS.values())
SCHEDULE_OPTION_TO_SPEED = {
    label: speed for speed, label in SCHEDULE_SPEED_LABELS.items()
}
SCHEDULE_SPEED_TO_OPTION = {
    speed: label for label, speed in SCHEDULE_OPTION_TO_SPEED.items()
}
SCHEDULE_SPEED_ICONS = {
    "standby": "mdi:power-sleep",
    "speed_1": "mdi:fan-speed-1",
    "low": "mdi:fan-speed-1",
    "speed_2": "mdi:fan-speed-2",
    "medium": "mdi:fan-speed-2",
    "speed_3": "mdi:fan-speed-3",
    "high": "mdi:fan-speed-3",
    "speed_4": "mdi:fan-plus",
    "speed_5": "mdi:fan-plus",
}
SCHEDULE_SPEED_TO_VALUE = {
    "standby": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "speed_4": 4,
    "speed_5": 5,
}

BGCP_FINAL_PERIOD_ENDS = frozenset({(0, 0), (23, 59)})


@dataclass(frozen=True)
class WeeklyScheduleRecord:
    """One weekly schedule period on the device."""

    day: int
    period: int
    speed: str
    end_hour: int
    end_minute: int
    reserved: int = 0

    @property
    def day_label(self) -> str:
        """Return the human-friendly day label."""
        return SCHEDULE_DAY_LABELS.get(self.day, f"Day {self.day}")

    @property
    def speed_option(self) -> str:
        """Return the UI label for the current speed."""
        return SCHEDULE_SPEED_TO_OPTION.get(self.speed, self.speed)

    @property
    def end_time(self) -> time:
        """Return the end time as a datetime.time object."""
        return time(self.end_hour, self.end_minute)

    def to_hex_payload(self) -> str:
        """Encode the schedule record to the 0x0077 payload bytes."""
        validate_bgcp_schedule_record(self)
        speed_value = SCHEDULE_SPEED_TO_VALUE[self.speed]
        payload = bytes(
            [
                self.day,
                self.period,
                speed_value,
                self.reserved,
                self.end_minute,
                self.end_hour,
            ]
        )
        return payload.hex()

    def summary(self, start_hour: int, start_minute: int) -> str:
        """Format one schedule row as a compact time range summary."""
        return (
            f"{start_hour:02d}:{start_minute:02d}-"
            f"{self.end_hour:02d}:{self.end_minute:02d} {self.speed_option}"
        )

    def as_dict(self) -> dict[str, object]:
        """Serialize one schedule row for Home Assistant attributes."""
        data: dict[str, object] = {
            "period": self.period,
            "speed": self.speed_option,
            "editable_end": self.period < 4,
            "end": f"{self.end_hour:02d}:{self.end_minute:02d}",
        }
        return data


def build_schedule_record(
    day: int,
    period_data: dict[str, object],
    current: WeeklyScheduleRecord | None,
) -> WeeklyScheduleRecord:
    """Build one validated schedule record from a partial service payload."""
    try:
        period = int(period_data["period"])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("Schedule payload period must be an integer") from err
    if period not in range(1, 5):
        raise ValueError(f"Invalid schedule period: {period}")

    if current is None:
        raise ValueError(f"Schedule record not available for day={day}, period={period}")

    speed_option = str(period_data.get("speed") or current.speed_option)
    end_value = period_data.get("end")
    end_time_value = current.end_time
    if end_value is not None:
        try:
            end_text = str(end_value)
            if (
                len(end_text) != 5
                or end_text[2] != ":"
                or not end_text[:2].isdigit()
                or not end_text[3:].isdigit()
            ):
                raise ValueError
            hour_str, minute_str = end_text.split(":", 1)
            end_time_value = time(int(hour_str), int(minute_str))
        except (TypeError, ValueError) as err:
            raise ValueError("Schedule end must be a valid HH:MM time") from err

    try:
        speed = SCHEDULE_OPTION_TO_SPEED[speed_option]
    except KeyError as err:
        raise ValueError(f"Invalid schedule speed: {speed_option}") from err

    record = WeeklyScheduleRecord(
        day=day,
        period=period,
        speed=speed,
        end_hour=end_time_value.hour,
        end_minute=end_time_value.minute,
        reserved=current.reserved,
    )
    validate_schedule_record(record)
    return record


def validate_schedule_record(record: WeeklyScheduleRecord) -> None:
    """Validate one schedule record without transport-specific end rules."""
    if record.day not in range(1, 8):
        raise ValueError(f"Invalid schedule day: {record.day}")
    if record.period not in range(1, 5):
        raise ValueError(f"Invalid schedule period: {record.period}")
    if record.speed not in SCHEDULE_SPEED_TO_OPTION:
        raise ValueError(f"Invalid schedule speed: {record.speed}")
    if not 0 <= record.reserved <= 0xFF:
        raise ValueError(f"Invalid schedule reserved byte: {record.reserved}")
    if not 0 <= record.end_hour <= 23 or not 0 <= record.end_minute <= 59:
        raise ValueError(
            "Invalid schedule end time: "
            f"{record.end_hour:02d}:{record.end_minute:02d}"
        )


def validate_schedule_day(records: list[WeeklyScheduleRecord]) -> None:
    """Validate that one day remains chronological across all transports."""
    expected_periods = [1, 2, 3, 4]
    periods = [record.period for record in records]
    if periods != expected_periods:
        raise ValueError("Schedule payload must include periods 1 through 4 in order")

    previous_end = 0
    for record in records:
        validate_schedule_record(record)
        current_end = record.end_hour * 60 + record.end_minute
        if record.period < 4 and current_end <= previous_end:
            raise ValueError("Schedule period end times must stay in chronological order")
        previous_end = current_end


def validate_bgcp_schedule_record(record: WeeklyScheduleRecord) -> None:
    """Validate one 0x0077/BGCP record, including its terminal-period rule."""
    validate_schedule_record(record)
    if record.speed not in SCHEDULE_SPEED_TO_VALUE:
        raise ValueError(f"Invalid BGCP schedule speed: {record.speed}")
    if record.period == 4 and (record.end_hour, record.end_minute) not in BGCP_FINAL_PERIOD_ENDS:
        raise ValueError("BGCP schedule period 4 must end at 00:00 or 23:59")


def validate_bgcp_schedule_day(records: list[WeeklyScheduleRecord]) -> None:
    """Validate a complete BGCP day without changing A21 schedule semantics."""
    validate_schedule_day(records)
    for record in records:
        validate_bgcp_schedule_record(record)


def changed_schedule_records(
    day: int,
    current_records: dict[int, WeeklyScheduleRecord],
    period_payloads: list[dict[str, object]],
) -> list[WeeklyScheduleRecord]:
    """Return only device records that differ after applying a partial day payload."""
    updated_records = [current_records.get(period) for period in range(1, 5)]
    if any(record is None for record in updated_records):
        day_label = SCHEDULE_DAY_LABELS.get(day, f"Day {day}")
        raise ValueError(f"Schedule records not available for {day_label}")

    for period_data in period_payloads:
        period = int(period_data["period"])
        updated_records[period - 1] = build_schedule_record(
            day,
            period_data,
            current_records.get(period),
        )

    validate_schedule_day(updated_records)
    return [
        record
        for record in updated_records
        if record != current_records.get(record.period)
    ]

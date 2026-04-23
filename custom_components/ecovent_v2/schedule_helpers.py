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
SCHEDULE_SPEED_TO_VALUE = {
    "standby": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "speed_4": 4,
    "speed_5": 5,
}


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
        }
        if self.period < 4:
            data["end"] = f"{self.end_hour:02d}:{self.end_minute:02d}"
        return data

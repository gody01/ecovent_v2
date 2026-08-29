"""EcoVent Fan mixin extracted from the vendored protocol client."""

from datetime import date

try:
    from .schedule_helpers import WeeklyScheduleRecord
except ImportError:
    from schedule_helpers import WeeklyScheduleRecord


class FanSpeedPropertiesMixin:
    def _preset_speed_percent(self, input):
        val = int(input, 16)
        if self.device_profile.speed_percent_scale == "percent":
            return val
        if val >= 0 and val <= 255:
            return int(val / 255 * 100)
        return None

    @property
    def supply_speed_low(self):
        return self._supply_speed_low

    @supply_speed_low.setter
    def supply_speed_low(self, input):
        self._supply_speed_low = self._preset_speed_percent(input)

    @property
    def exhaust_speed_low(self):
        return self._exhaust_speed_low

    @exhaust_speed_low.setter
    def exhaust_speed_low(self, input):
        self._exhaust_speed_low = self._preset_speed_percent(input)

    @property
    def supply_speed_medium(self):
        return self._supply_speed_medium

    @supply_speed_medium.setter
    def supply_speed_medium(self, input):
        self._supply_speed_medium = self._preset_speed_percent(input)

    @property
    def exhaust_speed_medium(self):
        return self._exhaust_speed_medium

    @exhaust_speed_medium.setter
    def exhaust_speed_medium(self, input):
        self._exhaust_speed_medium = self._preset_speed_percent(input)

    @property
    def supply_speed_high(self):
        return self._supply_speed_high

    @supply_speed_high.setter
    def supply_speed_high(self, input):
        self._supply_speed_high = self._preset_speed_percent(input)

    @property
    def exhaust_speed_high(self):
        return self._exhaust_speed_high

    @exhaust_speed_high.setter
    def exhaust_speed_high(self, input):
        self._exhaust_speed_high = self._preset_speed_percent(input)

    @property
    def supply_speed_4(self):
        return self._supply_speed_4

    @supply_speed_4.setter
    def supply_speed_4(self, input):
        self._supply_speed_4 = self._preset_speed_percent(input)

    @property
    def exhaust_speed_4(self):
        return self._exhaust_speed_4

    @exhaust_speed_4.setter
    def exhaust_speed_4(self, input):
        self._exhaust_speed_4 = self._preset_speed_percent(input)

    @property
    def supply_speed_5(self):
        return self._supply_speed_5

    @supply_speed_5.setter
    def supply_speed_5(self, input):
        self._supply_speed_5 = self._preset_speed_percent(input)

    @property
    def exhaust_speed_5(self):
        return self._exhaust_speed_5

    @exhaust_speed_5.setter
    def exhaust_speed_5(self, input):
        self._exhaust_speed_5 = self._preset_speed_percent(input)

    def preset_speed_percent(self, preset, *, fallback_to_manual=True):
        if self.uses_operating_mode_presets:
            return self.max_speed_setpoint
        if preset == "manual":
            return self.man_speed if fallback_to_manual else None

        preset_speeds = {
            "speed_1": (self.supply_speed_low, self.exhaust_speed_low),
            "speed_2": (self.supply_speed_medium, self.exhaust_speed_medium),
            "speed_3": (self.supply_speed_high, self.exhaust_speed_high),
            "low": (self.supply_speed_low, self.exhaust_speed_low),
            "medium": (self.supply_speed_medium, self.exhaust_speed_medium),
            "high": (self.supply_speed_high, self.exhaust_speed_high),
            "speed_4": (self.supply_speed_4, self.exhaust_speed_4),
            "speed_5": (self.supply_speed_5, self.exhaust_speed_5),
        }
        preset_speed = preset_speeds.get(preset)
        if preset_speed is None:
            return None

        supply_speed, exhaust_speed = preset_speed
        airflow = self.airflow
        if (
            self.supports_parameter("airflow")
            and airflow not in ("air_supply", "ventilation", "heat_recovery", "extract")
        ):
            return None
        if airflow == "air_supply" and supply_speed is not None:
            return supply_speed
        if airflow == "extract" and exhaust_speed is not None:
            return exhaust_speed

        # Home Assistant exposes one percentage, while balanced Freshpoint/Breezy
        # modes can have separate supply and extract setpoints. Average them as
        # a UI compromise until the integration has a richer two-fan surface.
        available_speeds = [
            speed for speed in (supply_speed, exhaust_speed) if speed is not None
        ]
        if available_speeds:
            return int(sum(available_speeds) / len(available_speeds))
        return None

    @property
    def man_speed(self):
        return self._man_speed

    @man_speed.setter
    def man_speed(self, input):
        val = int(input, 16)
        if self.device_profile.speed_percent_scale == "percent":
            self._man_speed = val
            return
        if val >= 0 and val <= 255:
            self._man_speed = int(val / 255 * 100)

    @property
    def max_speed_setpoint(self):
        return self._max_speed_setpoint

    @max_speed_setpoint.setter
    def max_speed_setpoint(self, input):
        val = int(input, 16)
        self._max_speed_setpoint = val

    @property
    def silent_speed_setpoint(self):
        return self._silent_speed_setpoint

    @silent_speed_setpoint.setter
    def silent_speed_setpoint(self, input):
        val = int(input, 16)
        self._silent_speed_setpoint = val

    @property
    def interval_ventilation_speed_setpoint(self):
        return self._interval_ventilation_speed_setpoint

    @interval_ventilation_speed_setpoint.setter
    def interval_ventilation_speed_setpoint(self, input):
        val = int(input, 16)
        self._interval_ventilation_speed_setpoint = val

    @property
    def fan1_speed(self):
        return self._fan1_speed

    @fan1_speed.setter
    def fan1_speed(self, input):
        val = int.from_bytes(
            self._decode_exact_bytes(input, 2, "fan1_speed"),
            byteorder="little",
            signed=False,
        )
        self._fan1_speed = str(val)

    @property
    def fan2_speed(self):
        return self._fan2_speed

    @fan2_speed.setter
    def fan2_speed(self, input):
        val = int.from_bytes(
            self._decode_exact_bytes(input, 2, "fan2_speed"),
            byteorder="little",
            signed=False,
        )
        self._fan2_speed = str(val)

    @property
    def filter_timer_setpoint(self):
        return self._filter_timer_setpoint

    @filter_timer_setpoint.setter
    def filter_timer_setpoint(self, input):
        val = int.from_bytes(
            self._decode_exact_bytes(input, 2, "filter_timer_setpoint"),
            byteorder="little",
            signed=False,
        )
        self._filter_timer_setpoint = str(val) + " d"

    @property
    def filter_timer_countdown(self):
        return self._filter_timer_countdown

    @filter_timer_countdown.setter
    def filter_timer_countdown(self, input):
        raw = bytes.fromhex(input)
        if len(raw) == 5 and raw[0] == 0:
            raw = raw[1:]
        if len(raw) == 4:
            val = raw
            days = val[-1] * 256 + val[-2]
            self._filter_timer_countdown = (
                str(days) + "d " + str(val[-3]) + "h " + str(val[-4]) + "m "
            )
            return
        if not 1 <= len(raw) <= 3:
            raise ValueError(
                "filter_timer_countdown must contain 1-4 bytes or one "
                "leading zero pad plus 4 bytes"
            )
        val = raw.rjust(3, b"\x00")
        self._filter_timer_countdown = (
            str(val[2]) + "d " + str(val[1]) + "h " + str(val[0]) + "m "
        )

    @property
    def boost_time(self):
        return self._boost_time

    @boost_time.setter
    def boost_time(self, input):
        val = int(input, 16)
        self._boost_time = str(val) + " m"

    @property
    def turn_on_delay_timer(self):
        return self._turn_on_delay_timer

    @turn_on_delay_timer.setter
    def turn_on_delay_timer(self, input):
        val = int(input, 16)
        self._turn_on_delay_timer = str(val)

    @property
    def rtc_time(self):
        return self._rtc_time

    @rtc_time.setter
    def rtc_time(self, input):
        if self.profile_key == "extract_fan":
            total_seconds = int.from_bytes(
                self._decode_exact_bytes(input, 3, "rtc_time"),
                byteorder="little",
                signed=False,
            )
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self._rtc_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return

        val = self._decode_exact_bytes(input, 3, "rtc_time")
        if val[0] > 59 or val[1] > 59 or val[2] > 23:
            raise ValueError(
                f"Invalid RTC time: {val[2]:02d}:{val[1]:02d}:{val[0]:02d}"
            )
        self._rtc_time = f"{val[2]:02d}:{val[1]:02d}:{val[0]:02d}"

    @property
    def silent_mode_start_time(self):
        return self._silent_mode_start_time

    @silent_mode_start_time.setter
    def silent_mode_start_time(self, input):
        if self.profile_key == "extract_fan":
            hours, minutes, seconds = self._decode_duration_seconds(
                input, "silent_mode_start_time"
            )
        else:
            seconds, minutes, hours = self._decode_exact_bytes(
                input, 3, "silent_mode_start_time"
            )
        self._silent_mode_start_time = f"{hours}h {minutes}m {seconds}s "

    @property
    def silent_mode_end_time(self):
        return self._silent_mode_end_time

    @silent_mode_end_time.setter
    def silent_mode_end_time(self, input):
        if self.profile_key == "extract_fan":
            hours, minutes, seconds = self._decode_duration_seconds(
                input, "silent_mode_end_time"
            )
        else:
            seconds, minutes, hours = self._decode_exact_bytes(
                input, 3, "silent_mode_end_time"
            )
        self._silent_mode_end_time = f"{hours}h {minutes}m {seconds}s "

    @property
    def rtc_date(self):
        return self._rtc_date

    @rtc_date.setter
    def rtc_date(self, input):
        val = self._decode_exact_bytes(input, 4, "rtc_date")
        if val[1] not in range(1, 8):
            raise ValueError(f"Invalid RTC weekday: {val[1]}")
        try:
            calendar_date = date(2000 + val[3], val[2], val[0])
        except ValueError as err:
            raise ValueError(
                f"Invalid RTC date: 20{val[3]:02d}-{val[2]:02d}-{val[0]:02d}"
            ) from err
        self._rtc_weekday = val[1]
        self._rtc_date = calendar_date.isoformat()

    @property
    def weekly_schedule_state(self):
        return self._weekly_schedule_state

    @weekly_schedule_state.setter
    def weekly_schedule_state(self, val):
        value = int(val, 16) if isinstance(val, str) else int(val)
        self._weekly_schedule_state = self._map_value(
            self.states, value, "weekly_schedule_state"
        )

    @property
    def weekly_schedule_setup(self):
        return self._weekly_schedule_setup

    @weekly_schedule_setup.setter
    def weekly_schedule_setup(self, input):
        val = self._decode_exact_bytes(input, 6, "weekly_schedule_setup")
        if val[0] not in range(1, 8):
            raise ValueError(f"Invalid schedule response day: {val[0]}")
        if val[1] not in range(1, 5):
            raise ValueError(f"Invalid schedule response period: {val[1]}")
        if val[4] > 59 or val[5] > 23:
            raise ValueError(
                "Invalid schedule response end time: "
                f"{val[5]:02d}:{val[4]:02d}"
            )
        speed = self._map_value(self.speeds, val[2], "weekly_schedule_speed")
        record = WeeklyScheduleRecord(
            day=val[0],
            period=val[1],
            speed=speed,
            end_hour=val[5],
            end_minute=val[4],
            reserved=val[3],
        )
        self._weekly_schedule_setup_record = record
        self._weekly_schedule_setup = (
            f"{record.day_label}/{record.period}: "
            f"to {record.end_hour:02d}:{record.end_minute:02d} {record.speed_option}"
        )

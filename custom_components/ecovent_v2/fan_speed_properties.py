"""EcoVent Fan mixin extracted from the vendored protocol client."""

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

    def preset_speed_percent(self, preset):
        if self.uses_operating_mode_presets:
            return self.max_speed_setpoint

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
            return self.man_speed

        supply_speed, exhaust_speed = preset_speed
        if self.airflow == "air_supply" and supply_speed is not None:
            return supply_speed
        if self.airflow == "ventilation" and exhaust_speed is not None:
            return exhaust_speed

        available_speeds = [
            speed for speed in (supply_speed, exhaust_speed) if speed is not None
        ]
        if available_speeds:
            return int(sum(available_speeds) / len(available_speeds))
        return self.man_speed

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
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._fan1_speed = str(val)

    @property
    def fan2_speed(self):
        return self._fan2_speed

    @fan2_speed.setter
    def fan2_speed(self, input):
        val = int.from_bytes(
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._fan2_speed = str(val)

    @property
    def filter_timer_setpoint(self):
        return self._filter_timer_setpoint

    @filter_timer_setpoint.setter
    def filter_timer_setpoint(self, input):
        val = int.from_bytes(bytes.fromhex(input), byteorder="little", signed=False)
        self._filter_timer_setpoint = str(val) + " d"

    @property
    def filter_timer_countdown(self):
        return self._filter_timer_countdown

    @filter_timer_countdown.setter
    def filter_timer_countdown(self, input):
        if len(input) >= 8:
            val = int(input, 16).to_bytes(max((len(input) + 1) // 2, 4), "big")
            days = val[-1] * 256 + val[-2]
            self._filter_timer_countdown = (
                str(days) + "d " + str(val[-3]) + "h " + str(val[-4]) + "m "
            )
            return
        # print ( "EcoventV2: " + input , file = sys.stderr )
        val = int(input, 16).to_bytes(3, "big")
        self._filter_timer_countdown = (
            str(val[2]) + "d " + str(val[1]) + "h " + str(val[0]) + "m "
        )
        # self._filter_timer_countdown = str(int(input[4:6],16)) + "d " + str(int(input[2:4],16)) + "h " +str(int(input[0:2],16)) + "m "

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
        raw = bytes.fromhex(input)
        if self.profile_key == "extract_fan":
            total_seconds = int.from_bytes(raw, byteorder="little", signed=False)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self._rtc_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return

        val = int(input, 16).to_bytes(3, "big")
        self._rtc_time = f"{val[2]:02d}:{val[1]:02d}:{val[0]:02d}"

    @property
    def silent_mode_start_time(self):
        return self._silent_mode_start_time

    @silent_mode_start_time.setter
    def silent_mode_start_time(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._silent_mode_start_time = (
            str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "
        )

    @property
    def silent_mode_end_time(self):
        return self._silent_mode_end_time

    @silent_mode_end_time.setter
    def silent_mode_end_time(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._silent_mode_end_time = (
            str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "
        )

    @property
    def rtc_date(self):
        return self._rtc_date

    @rtc_date.setter
    def rtc_date(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._rtc_weekday = val[1]
        self._rtc_date = f"20{val[3]:02d}-{val[2]:02d}-{val[0]:02d}"

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
        val = int(input, 16).to_bytes(6, "big")
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

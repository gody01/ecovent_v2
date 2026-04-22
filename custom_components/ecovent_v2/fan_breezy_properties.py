"""EcoVent Fan mixin extracted from the vendored protocol client."""

class FanBreezyPropertiesMixin:
    @property
    def co2_sensor_state(self):
        return self._co2_sensor_state

    @co2_sensor_state.setter
    def co2_sensor_state(self, input):
        val = int(input, 16)
        self._co2_sensor_state = self._map_value(self.states, val, "co2_sensor_state")

    @property
    def co2_treshold(self):
        return self._co2_treshold

    @co2_treshold.setter
    def co2_treshold(self, input):
        self._co2_treshold = self._decode_uint(input)

    @property
    def co2(self):
        return self._co2

    @co2.setter
    def co2(self, input):
        self._co2 = self._decode_uint(input)

    @property
    def outdoor_temperature(self):
        return self._outdoor_temperature

    @outdoor_temperature.setter
    def outdoor_temperature(self, input):
        self._outdoor_temperature = self._decode_signed_temperature(input)

    @property
    def supply_temperature(self):
        return self._supply_temperature

    @supply_temperature.setter
    def supply_temperature(self, input):
        self._supply_temperature = self._decode_signed_temperature(input)

    @property
    def exhaust_in_temperature(self):
        return self._exhaust_in_temperature

    @exhaust_in_temperature.setter
    def exhaust_in_temperature(self, input):
        self._exhaust_in_temperature = self._decode_signed_temperature(input)

    @property
    def exhaust_out_temperature(self):
        return self._exhaust_out_temperature

    @exhaust_out_temperature.setter
    def exhaust_out_temperature(self, input):
        self._exhaust_out_temperature = self._decode_signed_temperature(input)

    @property
    def heater_state(self):
        return self._heater_state

    @heater_state.setter
    def heater_state(self, input):
        val = int(input, 16)
        self._heater_state = self._map_value(self.states, val, "heater_state")

    @property
    def alarm_list(self):
        return self._alarm_list

    @alarm_list.setter
    def alarm_list(self, input):
        data = bytes.fromhex(input)
        alarms = []
        for index in range(0, len(data) - 1, 2):
            alarm_type = self._map_value(self.alarms, data[index + 1], "alarm_type")
            alarms.append(f"{data[index]}:{alarm_type}")
        self._alarm_list = ", ".join(alarms) if alarms else "none"

    @property
    def air_quality_status(self):
        return self._air_quality_status

    @air_quality_status.setter
    def air_quality_status(self, input):
        data = bytes.fromhex(input)
        if len(data) == 1:
            self._air_quality_status = self._map_value(
                self.statuses, data[0], "air_quality_status"
            )
            return

        parts = []
        labels = ("humidity", "co2", "reserved_1", "reserved_2", "voc")
        for label, value in zip(labels, data):
            parts.append(
                f"{label}:{self._map_value(self.air_quality_statuses, value, label)}"
            )
        self._air_quality_status = ", ".join(parts)

    @property
    def recovery_efficiency(self):
        return self._recovery_efficiency

    @recovery_efficiency.setter
    def recovery_efficiency(self, input):
        self._recovery_efficiency = int(input, 16)

    @property
    def schedule_speed(self):
        return self._schedule_speed

    @schedule_speed.setter
    def schedule_speed(self, input):
        val = int(input, 16)
        self._schedule_speed = self._map_value(self.speeds, val, "schedule_speed")

    @property
    def frost_protection_status(self):
        return self._frost_protection_status

    @frost_protection_status.setter
    def frost_protection_status(self, input):
        val = int(input, 16)
        self._frost_protection_status = self._map_value(
            self.frost_protection_statuses, val, "frost_protection_status"
        )

    @property
    def voc_sensor_state(self):
        return self._voc_sensor_state

    @voc_sensor_state.setter
    def voc_sensor_state(self, input):
        val = int(input, 16)
        self._voc_sensor_state = self._map_value(self.states, val, "voc_sensor_state")

    @property
    def voc_treshold(self):
        return self._voc_treshold

    @voc_treshold.setter
    def voc_treshold(self, input):
        self._voc_treshold = self._decode_uint(input)

    @property
    def voc(self):
        return self._voc

    @voc.setter
    def voc(self, input):
        self._voc = self._decode_uint(input)

    @property
    def screen_brightness(self):
        return self._screen_brightness

    @screen_brightness.setter
    def screen_brightness(self, input):
        self._screen_brightness = int(input, 16)

    @property
    def screen_backlight_mode(self):
        return self._screen_backlight_mode

    @screen_backlight_mode.setter
    def screen_backlight_mode(self, input):
        val = int(input, 16)
        self._screen_backlight_mode = self._map_value(
            self.screen_backlight_modes, val, "screen_backlight_mode"
        )

    @property
    def screen_temperature_source(self):
        return self._screen_temperature_source

    @screen_temperature_source.setter
    def screen_temperature_source(self, input):
        val = int(input, 16)
        self._screen_temperature_source = self._map_value(
            self.screen_temperature_sources, val, "screen_temperature_source"
        )

    @property
    def screen_air_quality_source(self):
        return self._screen_air_quality_source

    @screen_air_quality_source.setter
    def screen_air_quality_source(self, input):
        val = int(input, 16)
        self._screen_air_quality_source = self._map_value(
            self.screen_air_quality_sources, val, "screen_air_quality_source"
        )

    @property
    def screen_display_mode(self):
        return self._screen_display_mode

    @screen_display_mode.setter
    def screen_display_mode(self, input):
        val = int(input, 16)
        self._screen_display_mode = self._map_value(
            self.screen_display_modes, val, "screen_display_mode"
        )

    @property
    def screen_standby_time_state(self):
        return self._screen_standby_time_state

    @screen_standby_time_state.setter
    def screen_standby_time_state(self, input):
        val = int(input, 16)
        self._screen_standby_time_state = self._map_value(
            self.screen_standby_time_states, val, "screen_standby_time_state"
        )

    @property
    def screen_display_state(self):
        return self._screen_display_state

    @screen_display_state.setter
    def screen_display_state(self, input):
        val = int(input, 16)
        self._screen_display_state = self._map_value(
            self.screen_display_states, val, "screen_display_state"
        )

    @property
    def screen_off_start_time(self):
        return self._screen_off_start_time

    @screen_off_start_time.setter
    def screen_off_start_time(self, input):
        self._screen_off_start_time = self._decode_time_minutes_hours(input)

    @property
    def screen_off_end_time(self):
        return self._screen_off_end_time

    @screen_off_end_time.setter
    def screen_off_end_time(self, input):
        self._screen_off_end_time = self._decode_time_minutes_hours(input)

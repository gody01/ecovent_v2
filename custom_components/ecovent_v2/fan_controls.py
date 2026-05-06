"""EcoVent Fan mixin extracted from the vendored protocol client."""

import math


class FanControlsMixin:
    def set_state_on(self):
        request = "0001"
        value = "01"
        if self.state == "off":
            self.send_command(self.func["write_return"], request, value)

    def set_state_off(self):
        request = "0001"
        value = "00"
        if self.state == "on":
            self.send_command(self.func["write_return"], request, value)

    def set_speed(self, speed):
        if speed >= 1 and speed <= 5:
            request = "0002"
            value = hex(speed).replace("0x", "").zfill(2)
            self.send_command(self.func["write_return"], request, value)

    def set_man_speed_percent(self, speed):
        if speed >= 2 and speed <= 100:
            request = "0044"
            if self.device_profile.speed_percent_scale == "percent":
                value = speed
            else:
                value = math.ceil(255 / 100 * speed)
            value = hex(value).replace("0x", "").zfill(2)
            self.send_command(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.send_command(self.func["write_return"], request, value)

    def set_man_speed(self, speed):
        if speed >= 14 and speed <= 255:
            request = "0044"
            value = speed
            value = hex(value).replace("0x", "").zfill(2)
            self.send_command(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.send_command(self.func["write_return"], request, value)

    def set_airflow(self, val):
        if val >= 0 and val <= 2:
            request = "00b7"
            value = hex(val).replace("0x", "").zfill(2)
            self.send_command(self.func["write_return"], request, value)

    @property
    def operating_mode_preset(self):
        if self.all_day_mode == "on":
            return "all_day"
        if self.humidity_sensor_state == "automatic":
            return "humidity_trigger"
        if self.humidity_sensor_state == "manual":
            return "humidity_manual"
        if self.temperature_sensor_state == "on":
            return "temperature_trigger"
        if self.motion_sensor_state == "on":
            return "motion_trigger"
        if self.relay_sensor_state == "on":
            return "external_switch_trigger"
        if self.interval_ventilation_state == "on":
            return "interval_ventilation"
        if self.silent_mode_state == "on":
            return "silent"
        if self.boost_status == "on":
            return "boost"
        return None

    def set_speed_setpoint_percent(self, percentage):
        """Set speed setpoints used by autonomous operating modes."""
        target = max(30, min(100, int(percentage)))
        value = hex(target).replace("0x", "").zfill(2)
        self.set_param("max_speed_setpoint", value)
        self.set_param("interval_ventilation_speed_setpoint", value)
        self.set_param("all_day_mode", "on")
        self.set_param("silent_mode_state", "off")

    def set_operating_mode_preset(self, preset_mode):
        """Activate one autonomous operating mode and disable the others."""
        reset = {
            "all_day_mode": "off",
            "humidity_sensor_state": "off",
            "temperature_sensor_state": "off",
            "motion_sensor_state": "off",
            "relay_sensor_state": "off",
            "interval_ventilation_state": "off",
            "silent_mode_state": "off",
            "boost_status": "off",
        }
        targets = {
            "all_day": {"all_day_mode": "on"},
            "humidity_trigger": {"humidity_sensor_state": "automatic"},
            "humidity_manual": {"humidity_sensor_state": "manual"},
            "temperature_trigger": {"temperature_sensor_state": "on"},
            "motion_trigger": {"motion_sensor_state": "on"},
            "external_switch_trigger": {"relay_sensor_state": "on"},
            "interval_ventilation": {"interval_ventilation_state": "on"},
            "silent": {"silent_mode_state": "on"},
            "boost": {"boost_status": "on"},
        }
        target = targets.get(preset_mode)
        if target is None:
            raise ValueError(f"Invalid operating-mode preset: {preset_mode}")

        reset.update(target)
        self.set_parameters(reset)

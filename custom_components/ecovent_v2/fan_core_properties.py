"""EcoVent Fan mixin extracted from the vendored protocol client."""

import socket
import sys

class FanCorePropertiesMixin:
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, ip):
        try:
            socket.inet_aton(ip)
            self._host = ip
        except socket.error:
            sys.exit()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, pwd):
        self._password = pwd

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        value = int(val, 16) if isinstance(val, str) else int(val)
        self._state = self._map_value(self.states, value, "state")

    @property
    def speed(self):
        if self.uses_operating_mode_presets:
            return self.operating_mode_preset
        return self._speed

    @speed.setter
    def speed(self, input):
        val = int(input, 16)
        self._speed = self._map_value(self.speeds, val, "speed")

    @property
    def boost_status(self):
        return self._boost_status

    @boost_status.setter
    def boost_status(self, input):
        val = int(input, 16)
        self._boost_status = self._map_value(
            self._profile_enum(self.device_profile.boost_statuses_name),
            val,
            "boost_status",
        )

    @property
    def heater_status(self):
        return self._heater_status

    @heater_status.setter
    def heater_status(self, input):
        val = int(input, 16)
        self._heater_status = self._map_value(self.statuses, val, "heater_status")

    @property
    def timer_mode(self):
        return self._timer_mode

    @timer_mode.setter
    def timer_mode(self, input):
        val = int(input, 16)
        self._timer_mode = self._map_value(self.timer_modes, val, "timer_mode")

    @property
    def timer_counter(self):
        return self._timer_counter

    @timer_counter.setter
    def timer_counter(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._timer_counter = (
            str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "
        )

    @property
    def battery_status(self):
        return self._battery_status

    @battery_status.setter
    def battery_status(self, input):
        val = int(input, 16)
        self._battery_status = self._map_value(
            self.battery_statuses, val, "battery_status"
        )

    @property
    def low_battery_status(self):
        return self._low_battery_status

    @low_battery_status.setter
    def low_battery_status(self, input):
        val = int(input, 16)
        self._low_battery_status = self._map_value(
            self.statuses, val, "low_battery_status"
        )

    @property
    def all_day_mode(self):
        return self._all_day_mode

    @all_day_mode.setter
    def all_day_mode(self, input):
        val = int(input, 16)
        self._all_day_mode = self._map_value(self.states, val, "all_day_mode")

    @property
    def boost_timer_countdown(self):
        return self._boost_timer_countdown

    @boost_timer_countdown.setter
    def boost_timer_countdown(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._boost_timer_countdown = (
            str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "
        )

    @property
    def timer_status(self):
        return self._timer_status

    @timer_status.setter
    def timer_status(self, input):
        val = int(input, 16)
        self._timer_status = self._map_value(self.statuses, val, "timer_status")

    @property
    def humidity_sensor_state(self):
        return self._humidity_sensor_state

    @humidity_sensor_state.setter
    def humidity_sensor_state(self, input):
        val = int(input, 16)
        self._humidity_sensor_state = self._map_value(
            self._profile_enum(self.device_profile.humidity_sensor_states_name),
            val,
            "humidity_sensor_state",
        )

    @property
    def relay_sensor_state(self):
        return self._relay_sensor_state

    @relay_sensor_state.setter
    def relay_sensor_state(self, input):
        val = int(input, 16)
        self._relay_sensor_state = self._map_value(
            self.states, val, "relay_sensor_state"
        )

    @property
    def analogV_sensor_state(self):
        return self._analogV_sensor_state

    @analogV_sensor_state.setter
    def analogV_sensor_state(self, input):
        val = int(input, 16)
        self._analogV_sensor_state = self._map_value(
            self.states, val, "analogV_sensor_state"
        )

    @property
    def temperature_sensor_state(self):
        return self._temperature_sensor_state

    @temperature_sensor_state.setter
    def temperature_sensor_state(self, input):
        val = int(input, 16)
        self._temperature_sensor_state = self._map_value(
            self.states, val, "temperature_sensor_state"
        )

    @property
    def motion_sensor_state(self):
        return self._motion_sensor_state

    @motion_sensor_state.setter
    def motion_sensor_state(self, input):
        val = int(input, 16)
        self._motion_sensor_state = self._map_value(
            self.states, val, "motion_sensor_state"
        )

    @property
    def light_sensor_state(self):
        return self._light_sensor_state

    @light_sensor_state.setter
    def light_sensor_state(self, input):
        val = int(input, 16)
        self._light_sensor_state = self._map_value(
            self.states, val, "light_sensor_state"
        )

    @property
    def air_quality_sensor_state(self):
        return self._air_quality_sensor_state

    @air_quality_sensor_state.setter
    def air_quality_sensor_state(self, input):
        val = int(input, 16)
        self._air_quality_sensor_state = self._map_value(
            self.humidity_permission_modes, val, "air_quality_sensor_state"
        )

    @property
    def humidity_airflow(self):
        return self._humidity_airflow

    @humidity_airflow.setter
    def humidity_airflow(self, input):
        val = int(input, 16)
        self._humidity_airflow = self._map_value(
            self.arc_airflows_high, val, "humidity_airflow"
        )

    @property
    def motion_light_airflow(self):
        return self._motion_light_airflow

    @motion_light_airflow.setter
    def motion_light_airflow(self, input):
        val = int(input, 16)
        self._motion_light_airflow = self._map_value(
            self.arc_airflows_medium, val, "motion_light_airflow"
        )

    @property
    def air_quality_airflow(self):
        return self._air_quality_airflow

    @air_quality_airflow.setter
    def air_quality_airflow(self, input):
        val = int(input, 16)
        self._air_quality_airflow = self._map_value(
            self.arc_airflows_high, val, "air_quality_airflow"
        )

    @property
    def interval_ventilation_airflow(self):
        return self._interval_ventilation_airflow

    @interval_ventilation_airflow.setter
    def interval_ventilation_airflow(self, input):
        val = int(input, 16)
        self._interval_ventilation_airflow = self._map_value(
            self.arc_airflows_low, val, "interval_ventilation_airflow"
        )

    @property
    def all_day_airflow(self):
        return self._all_day_airflow

    @all_day_airflow.setter
    def all_day_airflow(self, input):
        val = int(input, 16)
        self._all_day_airflow = self._map_value(
            self.arc_airflows_low, val, "all_day_airflow"
        )

    @property
    def temperature_airflow(self):
        return self._temperature_airflow

    @temperature_airflow.setter
    def temperature_airflow(self, input):
        val = int(input, 16)
        self._temperature_airflow = self._map_value(
            self.arc_airflows_high, val, "temperature_airflow"
        )

    @property
    def humidity_treshold(self):
        return self._humidity_treshold

    @humidity_treshold.setter
    def humidity_treshold(self, input):
        val = int(input, 16)
        self._humidity_treshold = str(val)

    @property
    def temperature_treshold(self):
        return self._temperature_treshold

    @temperature_treshold.setter
    def temperature_treshold(self, input):
        val = int(input, 16)
        self._temperature_treshold = str(val)

    @property
    def battery_voltage(self):
        return self._battery_voltage

    @battery_voltage.setter
    def battery_voltage(self, input):
        val = int.from_bytes(
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._battery_voltage = str(val) + " mV"

    @property
    def humidity(self):
        return self._humidity

    @humidity.setter
    def humidity(self, input):
        val = int(input, 16)
        self._humidity = str(val)

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, input):
        val = int(input, 16)
        self._temperature = str(val)

    @property
    def room_temperature(self):
        return self._room_temperature

    @room_temperature.setter
    def room_temperature(self, input):
        self._room_temperature = self._decode_signed_temperature(input)

    @property
    def air_quality(self):
        return self._air_quality

    @air_quality.setter
    def air_quality(self, input):
        self._air_quality = self._decode_uint(input)

    @property
    def air_quality_treshold(self):
        return self._air_quality_treshold

    @air_quality_treshold.setter
    def air_quality_treshold(self, input):
        self._air_quality_treshold = self._decode_uint(input)

    @property
    def analogV(self):
        return self._analogV

    @analogV.setter
    def analogV(self, input):
        val = int(input, 16)
        self._analogV = str(val)

    @property
    def relay_status(self):
        return self._relay_status

    @relay_status.setter
    def relay_status(self, input):
        val = int(input, 16)
        self._relay_status = self._map_value(self.statuses, val, "relay_status")

    @property
    def boost_switch_status(self):
        return self._boost_switch_status

    @boost_switch_status.setter
    def boost_switch_status(self, input):
        val = int(input, 16)
        self._boost_switch_status = self._map_value(
            self.statuses, val, "boost_switch_status"
        )

    @property
    def fire_alarm_status(self):
        return self._fire_alarm_status

    @fire_alarm_status.setter
    def fire_alarm_status(self, input):
        val = int(input, 16)
        self._fire_alarm_status = self._map_value(
            self.statuses, val, "fire_alarm_status"
        )

    @property
    def temperature_status(self):
        return self._temperature_status

    @temperature_status.setter
    def temperature_status(self, input):
        val = int(input, 16)
        self._temperature_status = self._map_value(
            self.statuses, val, "temperature_status"
        )

    @property
    def motion_status(self):
        return self._motion_status

    @motion_status.setter
    def motion_status(self, input):
        val = int(input, 16)
        self._motion_status = self._map_value(self.statuses, val, "motion_status")

    @property
    def light_status(self):
        return self._light_status

    @light_status.setter
    def light_status(self, input):
        val = int(input, 16)
        self._light_status = self._map_value(self.statuses, val, "light_status")

    @property
    def interval_ventilation_status(self):
        return self._interval_ventilation_status

    @interval_ventilation_status.setter
    def interval_ventilation_status(self, input):
        val = int(input, 16)
        self._interval_ventilation_status = self._map_value(
            self.statuses, val, "interval_ventilation_status"
        )

    @property
    def silent_mode_status(self):
        return self._silent_mode_status

    @silent_mode_status.setter
    def silent_mode_status(self, input):
        val = int(input, 16)
        self._silent_mode_status = self._map_value(
            self.statuses, val, "silent_mode_status"
        )

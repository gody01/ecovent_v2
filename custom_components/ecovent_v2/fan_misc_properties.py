"""EcoVent Fan mixin extracted from the vendored protocol client."""

class FanMiscPropertiesMixin:
    @property
    def airflow(self):
        return self._airflow

    @airflow.setter
    def airflow(self, input):
        val = int(input, 16)
        self._airflow = self._map_value(self.airflows, val, "airflow")

    @property
    def analogV_treshold(self):
        return self._analogV_treshold

    @analogV_treshold.setter
    def analogV_treshold(self, input):
        val = int(input, 16)
        self._analogV_treshold = str(val)

    @property
    def unit_type(self):
        return self._unit_type

    @unit_type.setter
    def unit_type(self, input):
        val = int(input, 16)
        self._unit_type_id = val
        self._unit_type = self._map_value(self.unit_types, val, "model")
        self._apply_device_profile()

    @property
    def interval_ventilation_state(self):
        return self._interval_ventilation_state

    @interval_ventilation_state.setter
    def interval_ventilation_state(self, input):
        val = int(input, 16)
        self._interval_ventilation_state = self._map_value(
            self.states, val, "interval_ventilation_state"
        )

    @property
    def silent_mode_state(self):
        return self._silent_mode_state

    @silent_mode_state.setter
    def silent_mode_state(self, input):
        val = int(input, 16)
        self._silent_mode_state = self._map_value(
            self.states, val, "silent_mode_state"
        )

    @property
    def night_mode_timer(self):
        return self._night_mode_timer

    @night_mode_timer.setter
    def night_mode_timer(self, input):
        val = int(input, 16).to_bytes(2, "big")
        self._night_mode_timer = (
            str(val[1]).zfill(2) + "h " + str(val[0]).zfill(2) + "m"
        )

    @property
    def party_mode_timer(self):
        return self._party_mode_timer

    @party_mode_timer.setter
    def party_mode_timer(self, input):
        val = int(input, 16).to_bytes(2, "big")
        self._party_mode_timer = (
            str(val[1]).zfill(2) + "h " + str(val[0]).zfill(2) + "m"
        )

    @property
    def humidity_status(self):
        return self._humidity_status

    @humidity_status.setter
    def humidity_status(self, input):
        val = int(input, 16)
        self._humidity_status = self._map_value(self.statuses, val, "humidity_status")

    @property
    def analogV_status(self):
        return self._analogV_status

    @analogV_status.setter
    def analogV_status(self, input):
        val = int(input, 16)
        self._analogV_status = self._map_value(self.statuses, val, "analogV_status")

    @property
    def beeper(self):
        return self._beeper

    @beeper.setter
    def beeper(self, input):
        val = int(input, 16)
        index = self.get_params_index("beeper")
        param = self.params.get(index) if index is not None else None
        mapping = param[1] if param and param[1] is not None else self.bstatuses
        self._beeper = self._map_value(mapping, val, "beeper")

    @property
    def unknown_params(self):
        return self._unknown_params

    def reset_filter_timer(self):
        self.set_param("filter_timer_reset", "")

    def reset_alarms(self):
        self.set_param("reset_alarms", "")

"""EcoVent Fan mixin extracted from the vendored protocol client."""

class FanDevicePropertiesMixin:
    @property
    def device_search(self):
        return self._device_search

    @device_search.setter
    def device_search(self, val):
        self._device_search = self.hex2str(val)

    @property
    def device_password(self):
        return self._device_password

    @device_password.setter
    def device_password(self, val):
        self._device_password = self.hex2str(val)

    @property
    def machine_hours(self):
        return self._machine_hours

    @machine_hours.setter
    def machine_hours(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._machine_hours = (
            str(int.from_bytes(val[2:3], "big"))
            + "d "
            + str(val[1])
            + "h "
            + str(val[0])
            + "m "
        )

    @property
    def alarm_status(self):
        return self._alarm_status

    @alarm_status.setter
    def alarm_status(self, input):
        val = int(input, 16)
        self._alarm_status = self._map_value(self.alarms, val, "alarm_status")

    @property
    def cloud_server_state(self):
        return self._cloud_server_state

    @cloud_server_state.setter
    def cloud_server_state(self, input):
        val = int(input, 16)
        self._cloud_server_state = self._map_value(
            self.states, val, "cloud_server_state"
        )

    @property
    def wifi_module_status(self):
        return self._wifi_module_status

    @wifi_module_status.setter
    def wifi_module_status(self, input):
        val = int(input, 16)
        self._wifi_module_status = self._map_value(
            self.statuses, val, "wifi_module_status"
        )

    @property
    def wifi_connection_status(self):
        return self._wifi_connection_status

    @wifi_connection_status.setter
    def wifi_connection_status(self, input):
        val = int(input, 16)
        self._wifi_connection_status = self._map_value(
            self.statuses, val, "wifi_connection_status"
        )

    @property
    def firmware(self):
        return self._firmware

    @firmware.setter
    def firmware(self, input):
        val = int(input, 16).to_bytes(6, "big")
        self._firmware = (
            str(val[0])
            + "."
            + str(val[1])
            + " "
            + str(int.from_bytes(val[4:6], byteorder="little", signed=False))
            + "-"
            + str(val[3]).zfill(2)
            + "-"
            + str(val[2]).zfill(2)
        )

    @property
    def filter_replacement_status(self):
        return self._filter_replacement_status

    @filter_replacement_status.setter
    def filter_replacement_status(self, input):
        val = int(input, 16)
        self._filter_replacement_status = self._map_value(
            self.statuses, val, "filter_replacement_status"
        )

    @property
    def heater_blowing_status(self):
        return self._heater_blowing_status

    @heater_blowing_status.setter
    def heater_blowing_status(self, input):
        val = int(input, 16)
        self._heater_blowing_status = self._map_value(
            self.statuses, val, "heater_blowing_status"
        )

    @property
    def wifi_operation_mode(self):
        return self._wifi_operation_mode

    @wifi_operation_mode.setter
    def wifi_operation_mode(self, input):
        val = int(input, 16)
        self._wifi_operation_mode = self._map_value(
            self.wifi_operation_modes, val, "wifi_operation_mode"
        )

    @property
    def wifi_name(self):
        return self._wifi_name

    @wifi_name.setter
    def wifi_name(self, input):
        self._wifi_name = self.hex2str(input)

    @property
    def wifi_pasword(self):
        return self._wifi_pasword

    @wifi_pasword.setter
    def wifi_pasword(self, input):
        self._wifi_pasword = self.hex2str(input)

    @property
    def wifi_enc_type(self):
        return self._wifi_enc_type

    @wifi_enc_type.setter
    def wifi_enc_type(self, input):
        val = int(input, 16)
        self._wifi_enc_type = self._map_value(self.wifi_enc_types, val, "wifi_enc_type")

    @property
    def wifi_freq_channel(self):
        return self._wifi_freq_channel

    @wifi_freq_channel.setter
    def wifi_freq_channel(self, input):
        val = int(input, 16)
        self._wifi_freq_channel = str(val)

    @property
    def wifi_dhcp(self):
        return self._wifi_dhcp

    @wifi_dhcp.setter
    def wifi_dhcp(self, input):
        val = int(input, 16)
        self._wifi_dhcp = self._map_value(self.wifi_dhcps, val, "wifi_dhcp")

    @property
    def wifi_assigned_ip(self):
        return self._wifi_assigned_ip

    @wifi_assigned_ip.setter
    def wifi_assigned_ip(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_assigned_ip = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def wifi_assigned_netmask(self):
        return self._wifi_assigned_netmask

    @wifi_assigned_netmask.setter
    def wifi_assigned_netmask(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_assigned_netmask = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def wifi_main_gateway(self):
        return self._wifi_main_gateway

    @wifi_main_gateway.setter
    def wifi_main_gateway(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_main_gateway = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def current_wifi_ip(self):
        return self._current_wifi_ip

    @current_wifi_ip.setter
    def current_wifi_ip(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._current_wifi_ip = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

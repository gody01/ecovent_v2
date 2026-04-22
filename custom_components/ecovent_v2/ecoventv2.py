"""Library to handle communication with Wifi ecofan from TwinFresh / Blauberg."""

import logging
import math
import socket
import sys
import time

__version__ = "loc_0.9.29"

_LOGGER = logging.getLogger(__name__)

try:
    from .protocol_profiles import DEVICE_MODELS, DEVICE_PROFILES, UNIT_TYPE_NAMES
except ImportError:
    from protocol_profiles import DEVICE_MODELS, DEVICE_PROFILES, UNIT_TYPE_NAMES

""""
# currently having entities in HA:
==================================
F       0x0001: ["state", states],
F       0x0002: ["speed", speeds],
B       0x0006: ["boost_status", statuses],
B       0x0007: ["timer_mode", timer_modes],
S       0x000B: ["timer_counter", None],
Sw      0x000F: ["humidity_sensor_state", states],
Sw      0x0014: ["relay_sensor_state", states],
Sw      0x0016: ["analogV_sensor_state", states],
F N     0x0019: ["humidity_treshold", None],
S       0x0024: ["battery_voltage", None],
S       0x0025: ["humidity", None],
S       0x002D: ["analogV", None],
B       0x0032: ["relay_status", statuses],
F       0x0044: ["man_speed", None],
S       0x004A: ["fan1_speed", None],
S       0x004B: ["fan2_speed", None],
S       0x0064: ["filter_timer_countdown", None],
F N     0x0066: ["boost_time", None],
        0x006F: ["rtc_time", None],
        0x0070: ["rtc_date", None],
I       0x007C: ["device_search", None],   # this is actually the fan serial number
        0x007D: ["device_password", None],
S       0x007E: ["machine_hours", None],
        0x0081: ["heater_status", statuses],
B       0x0083: ["alarm_status", alarms],
B       0x0085: ["cloud_server_state", states],
I       0x0086: ["firmware", None],
B       0x0088: ["filter_replacement_status", statuses],
I S     0x00A3: ["current_wifi_ip", None],
F S     0x00B7: ["airflow", airflows],
F N     0x00B8: ["analogV_treshold", None],
I       0x00B9: ["unit_type", unit_types],
        # Write only parameters
FC      0x0065: ["filter_timer_reset", None],  # WRITE ONLY
Sw      0x0072: ["weekly_schedule_state", states],
        0x0077: ["weekly_schedule_setup", None],
FC      0x0080: ["reset_alarms", None],  # WRITE ONLY
        0x0094: ["wifi_operation_mode", wifi_operation_modes],
        # 0x0095: ["wifi_name", None],  # propose not to transfer this data over network
        # 0x0096: ["wifi_pasword", None], # propose not to transfer this data over network
        # 0x0099: ["wifi_enc_type", wifi_enc_types], # propose not to transfer this data over network
        0x009A: ["wifi_freq_channel", None],
        0x009B: ["wifi_dhcp", wifi_dhcps],
I       0x009C: ["wifi_assigned_ip", None],
        0x009D: ["wifi_assigned_netmask", None],
        0x009E: ["wifi_main_gateway", None],
        0x0302: ["night_mode_timer", None],
        0x0303: ["party_mode_timer", None],
B       0x0304: ["humidity_status", statuses],
B       0x0305: ["analogV_status", statuses],
        0x0306: ["beeper", bstatuses]        # beeper seems not to work on V2 eco vents, needs firmware 1.xxx or higher

B used as binary sensor
I used for initialization and discovery
F used for fan properties
FC used for fan commands
N used for number
S used for sensor
Sw used for switch

"""


class Fan(object):
    """Class to communicate with the ecofan"""

    HEADER = "FDFD"
    HEADER_BYTES = bytes.fromhex(HEADER)
    beeper_probe_read_count = 3
    beeper_probe_settle_seconds = 1

    func = {
        "read": "01",
        "write": "02",
        "write_return": "03",
        "inc": "04",
        "dec": "05",
        "resp": "06",
    }

    states = {0: "off", 1: "on", 2: "toggle"}

    speeds = {
        0: "standby",
        1: "low",
        2: "medium",
        3: "high",
        4: "speed_4",
        5: "speed_5",
        0xFF: "manual",
    }

    freshbox_speeds = {
        1: "speed_1",
        2: "speed_2",
        3: "speed_3",
        4: "speed_4",
        5: "speed_5",
    }

    battery_statuses = {0: "discharged", 1: "normal"}

    humidity_permission_modes = {
        0: "off",
        1: "automatic",
        2: "manual",
    }

    timer_modes = {0: "off", 1: "night", 2: "party"}

    statuses = {0: "off", 1: "on"}
    air_quality_statuses = {0: "normal", 1: "over_setpoint"}
    frost_protection_statuses = {0: "inactive", 1: "active"}
    screen_backlight_modes = {0: "auto", 1: "manual", 2: "toggle"}
    screen_temperature_sources = {
        0: "alternating",
        1: "supply_air",
        2: "extract_air",
    }
    screen_air_quality_sources = {0: "alternating", 1: "co2", 2: "voc"}
    screen_display_modes = {
        0: "alternating",
        1: "time",
        2: "temperature_humidity",
    }
    screen_standby_time_states = {0: "off", 1: "on"}
    screen_display_states = {0: "off", 1: "on", 2: "off_interval"}

    # Observed on a TwinFresh V.2 as a volatile command/status flag, not a stable
    # beeper preference. Writing 0 or 2 did not disable command beeps reliably.
    bstatuses = {0: "off", 1: "on", 2: "silent"}
    sound_emitter_states = {0: "off", 1: "on", 2: "toggle"}

    boost_statuses = {0: "off", 1: "on", 2: "delay"}

    airflows = {0: "ventilation", 1: "heat_recovery", 2: "air_supply", 3: "something"}

    alarms = {0: "no", 1: "alarm", 2: "warning"}

    days_of_week = {
        0: "all days",
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
        8: "Mon-Fri",
        9: "Sat-Sun",
    }

    filters = {0: "filter replacement not required", 1: "replace filter"}

    unit_types = UNIT_TYPE_NAMES

    wifi_operation_modes = {1: "client", 2: "ap"}

    wifi_enc_types = {48: "Open", 50: "wpa-psk", 51: "wpa2_psk", 52: "wpa_wpa2_psk"}

    wifi_dhcps = {0: "STATIC", 1: "DHCP", 2: "Invert"}

    params = {
        0x0001: ["state", states],
        0x0002: ["speed", speeds],
        0x0006: ["boost_status", boost_statuses],
        0x0007: ["timer_mode", timer_modes],
        0x000B: ["timer_counter", None],
        0x000F: ["humidity_sensor_state", states],
        0x0014: ["relay_sensor_state", states],
        0x0016: ["analogV_sensor_state", states],
        0x0019: ["humidity_treshold", None],
        0x0024: ["battery_voltage", None],
        0x0025: ["humidity", None],
        0x002D: ["analogV", None],
        0x0032: ["relay_status", statuses],
        0x003A: ["supply_speed_low", None],
        0x003B: ["exhaust_speed_low", None],
        0x003C: ["supply_speed_medium", None],
        0x003D: ["exhaust_speed_medium", None],
        0x003E: ["supply_speed_high", None],
        0x003F: ["exhaust_speed_high", None],
        0x0044: ["man_speed", None],
        0x004A: ["fan1_speed", None],
        0x004B: ["fan2_speed", None],
        0x0063: ["filter_timer_setpoint", None],
        0x0064: ["filter_timer_countdown", None],
        0x0066: ["boost_time", None],
        #   0x006F: ["rtc_time", None],  according stats not used in integration
        #   0x0070: ["rtc_date", None],  according stats not used in integration
        0x007C: ["device_search", None],  # this is the fan serial number
        #   0x007D: ["device_password", None],  according stats not used in integration
        0x007E: ["machine_hours", None],
        #   0x0081: ["heater_status", statuses], according stats not used in integration
        0x0083: ["alarm_status", alarms],
        0x0085: ["cloud_server_state", states],
        0x0086: ["firmware", None],
        0x0088: ["filter_replacement_status", statuses],
        0x00A3: ["current_wifi_ip", None],
        0x00B7: ["airflow", airflows],
        0x00B8: ["analogV_treshold", None],
        0x00B9: ["unit_type", unit_types],
        0x0072: ["weekly_schedule_state", states],
        #   0x0077: ["weekly_schedule_setup", None], according stats not used in integration
        #        0x0087: [ 'factory_reset', None ],
        #        0x00a0: [ 'wifi_apply_and_quit', None ],
        #        0x00a2: [ 'wifi_discard_and_quit', None ],
        #  0x0094: ["wifi_operation_mode", wifi_operation_modes],  according stats not used in integration
        #  # 0x0095: ["wifi_name", None],  # propose not to transfer this data over network   according stats not used in integration
        #  # 0x0096: ["wifi_pasword", None], # propose not to transfer this data over network  according stats not used in integration
        #  # 0x0099: ["wifi_enc_type", wifi_enc_types], # propose not to transfer this data over network  according stats not used in integration
        #  0x009A: ["wifi_freq_channel", None],  according stats not used in integration
        #  0x009B: ["wifi_dhcp", wifi_dhcps],  according stats not used in integration
        0x009C: ["wifi_assigned_ip", None],
        #  0x009D: ["wifi_assigned_netmask", None],  according stats not used in integration
        #  0x009E: ["wifi_main_gateway", None],  according stats not used in integration
        0x0302: ["night_mode_timer", None],
        0x0303: ["party_mode_timer", None],
        0x0304: ["humidity_status", statuses],
        0x0305: ["analogV_status", statuses],
        0x0306: ["beeper", bstatuses],
    }

    # Extract-fan profile. Keep this ordered by parameter number so
    # it can be compared against the implementation reference in protocol.md and
    # the PDF parameter table. Parameters 0x0014, 0x0016, 0x002E, and
    # 0x0031 are not visible in the PDF table; they come from the
    # ynsgnr/blauberg-assistant implementation linked from issue #11.
    extract_fan_params = {
        0x0001: ["state", states],
        0x0002: ["battery_status", battery_statuses],
        0x0003: ["all_day_mode", states],
        0x0004: ["fan1_speed", None],
        0x0005: ["boost_status", statuses],
        0x0006: ["boost_timer_countdown", None],
        0x0007: ["timer_status", statuses],
        0x0008: ["humidity_status", statuses],
        0x000A: ["temperature_status", statuses],
        0x000B: ["motion_status", statuses],
        0x000C: ["relay_status", statuses],
        0x000D: ["interval_ventilation_status", statuses],
        0x000E: ["silent_mode_status", statuses],
        0x000F: ["humidity_sensor_state", humidity_permission_modes],
        0x0011: ["temperature_sensor_state", states],
        0x0012: ["motion_sensor_state", states],
        0x0013: ["relay_sensor_state", states],
        0x0014: ["humidity_treshold", None],
        0x0016: ["temperature_treshold", None],
        0x0018: ["max_speed_setpoint", None],
        0x001A: ["silent_speed_setpoint", None],
        0x001B: ["interval_ventilation_speed_setpoint", None],
        0x001D: ["interval_ventilation_state", states],
        0x001E: ["silent_mode_state", states],
        0x001F: ["silent_mode_start_time", None],
        0x0020: ["silent_mode_end_time", None],
        0x0021: ["rtc_time", None],
        0x0023: ["boost_time", None],
        0x0024: ["turn_on_delay_timer", None],
        0x002E: ["humidity", None],
        0x0031: ["temperature", None],
        0x007C: ["device_search", None],
        0x0086: ["firmware", None],
        0x009C: ["wifi_assigned_ip", None],
        0x00A3: ["current_wifi_ip", None],
        0x00B9: ["unit_type", unit_types],
    }

    # Breezy/Freshpoint profile from the 2025 Breezy Eco and Freshpoint manuals.
    # It shares the UDP framing and several Vento rows, but it is not a pure
    # superset: some same-number rows are device-family specific and Vento has
    # parameters these manuals do not document.
    breezy_params = {
        0x0001: ["state", states],
        0x0002: ["speed", speeds],
        0x0007: ["timer_mode", timer_modes],
        0x000B: ["timer_counter", None],
        0x000F: ["humidity_sensor_state", states],
        0x0011: ["co2_sensor_state", states],
        0x0019: ["humidity_treshold", None],
        0x001A: ["co2_treshold", None],
        0x001F: ["outdoor_temperature", None],
        0x0020: ["supply_temperature", None],
        0x0021: ["exhaust_in_temperature", None],
        0x0022: ["exhaust_out_temperature", None],
        0x0024: ["battery_voltage", None],
        0x0025: ["humidity", None],
        0x0027: ["co2", None],
        0x003A: ["supply_speed_low", None],
        0x003B: ["exhaust_speed_low", None],
        0x003C: ["supply_speed_medium", None],
        0x003D: ["exhaust_speed_medium", None],
        0x003E: ["supply_speed_high", None],
        0x003F: ["exhaust_speed_high", None],
        0x0044: ["man_speed", None],
        0x004A: ["fan1_speed", None],
        0x004B: ["fan2_speed", None],
        0x0063: ["filter_timer_setpoint", None],
        0x0064: ["filter_timer_countdown", None],
        0x0068: ["heater_state", states],
        0x007C: ["device_search", None],
        0x007E: ["machine_hours", None],
        0x007F: ["alarm_list", None],
        0x0081: ["heater_status", statuses],
        0x0083: ["alarm_status", alarms],
        0x0084: ["air_quality_status", None],
        0x0085: ["cloud_server_state", states],
        0x0086: ["firmware", None],
        0x0088: ["filter_replacement_status", statuses],
        0x009C: ["wifi_assigned_ip", None],
        0x00A3: ["current_wifi_ip", None],
        0x00B7: ["airflow", airflows],
        0x00B9: ["unit_type", unit_types],
        0x0129: ["recovery_efficiency", None],
        0x0302: ["night_mode_timer", None],
        0x0303: ["party_mode_timer", None],
        0x0306: ["schedule_speed", speeds],
        0x030B: ["frost_protection_status", frost_protection_statuses],
        0x0315: ["voc_sensor_state", states],
        0x031F: ["voc_treshold", None],
        0x0320: ["voc", None],
        0x0400: ["screen_brightness", None],
        0x0401: ["beeper", sound_emitter_states],
        0x0402: ["screen_backlight_mode", screen_backlight_modes],
        0x0403: ["screen_temperature_source", screen_temperature_sources],
        0x0404: ["screen_air_quality_source", screen_air_quality_sources],
        0x0405: ["screen_display_mode", screen_display_modes],
        0x0406: ["screen_standby_time_state", screen_standby_time_states],
        0x0407: ["screen_display_state", screen_display_states],
        0x0408: ["screen_off_start_time", None],
        0x0409: ["screen_off_end_time", None],
    }

    # Freshbox 100 WiFi profile. Keep this conservative until a live device or
    # issue trace confirms which AHU-specific controls should become HA entities.
    freshbox_params = {
        0x0001: ["state", states],
        0x0002: ["speed", freshbox_speeds],
        0x0006: ["boost_status", statuses],
        0x0007: ["timer_status", states],
        0x000B: ["timer_counter", None],
        0x001F: ["outdoor_temperature", None],
        0x0020: ["supply_temperature", None],
        0x0021: ["exhaust_in_temperature", None],
        0x0022: ["exhaust_out_temperature", None],
        0x0032: ["boost_switch_status", statuses],
        0x0033: ["fire_alarm_status", statuses],
        0x003A: ["supply_speed_low", None],
        0x003B: ["exhaust_speed_low", None],
        0x003C: ["supply_speed_medium", None],
        0x003D: ["exhaust_speed_medium", None],
        0x003E: ["supply_speed_high", None],
        0x003F: ["exhaust_speed_high", None],
        0x0040: ["supply_speed_4", None],
        0x0041: ["exhaust_speed_4", None],
        0x0042: ["supply_speed_5", None],
        0x0043: ["exhaust_speed_5", None],
        0x0063: ["filter_timer_setpoint", None],
        0x0064: ["filter_timer_countdown", None],
        0x0066: ["boost_time", None],
        0x007C: ["device_search", None],
        0x007E: ["machine_hours", None],
        0x007F: ["alarm_list", None],
        0x0081: ["heater_status", statuses],
        0x0083: ["alarm_status", alarms],
        0x0085: ["cloud_server_state", states],
        0x0086: ["firmware", None],
        0x0088: ["filter_replacement_status", statuses],
        0x0093: ["wifi_module_status", statuses],
        0x00A1: ["wifi_connection_status", statuses],
        0x00A3: ["current_wifi_ip", None],
        0x00B6: ["heater_blowing_status", statuses],
        0x00B9: ["unit_type", unit_types],
    }

    write_params = {
        0x0065: ["filter_timer_reset", None],
        0x0080: ["reset_alarms", None],
    }

    extract_fan_write_params = {
        0x0025: ["factory_reset", None],
        0x00A0: ["wifi_apply_and_quit", None],
    }

    breezy_write_params = {
        0x0065: ["filter_timer_reset", None],
        0x0080: ["reset_alarms", None],
    }

    freshbox_write_params = {
        0x0065: ["filter_timer_reset", None],
        0x0080: ["reset_alarms", None],
    }

    device_profiles = DEVICE_PROFILES
    device_models = DEVICE_MODELS

    _name = None
    _host = None
    _port = None
    _id = None
    _password = None
    _state = None
    _speed = None
    _boost_status = None
    _heater_status = None
    _timer_mode = None
    _timer_counter = None
    _humidity_sensor_state = None
    _relay_sensor_state = None
    _analogV_sensor_state = None
    _humidity_treshold = None
    _battery_voltage = None
    _humidity = None
    _analogV = None
    _relay_status = None
    _supply_speed_low = None
    _exhaust_speed_low = None
    _supply_speed_medium = None
    _exhaust_speed_medium = None
    _supply_speed_high = None
    _exhaust_speed_high = None
    _man_speed = None
    _fan1_speed = None
    _fan2_speed = None
    _filter_timer_setpoint = None
    _filter_timer_countdown = None
    _boost_time = None
    _rtc_time = None
    _rtc_date = None
    _weekly_schedule_state = None
    _weekly_schedule_setup = None
    _device_search = None
    _device_password = None
    _machine_hours = None
    _alarm_status = None
    _cloud_server_state = None
    _firmware = None
    _filter_replacement_status = None
    _wifi_operation_mode = None
    _wifi_name = None
    _wifi_pasword = None
    _wifi_enc_type = None
    _wifi_freq_channel = None
    _wifi_dhcp = None
    _wifi_assigned_ip = None
    _wifi_assigned_netmask = None
    _wifi_main_gateway = None
    _current_wifi_ip = None
    _airflow = None
    _analogV_treshold = None
    _unit_type = None
    _unit_type_id = None
    _night_mode_timer = None
    _party_mode_timer = None
    _humidity_status = None
    _analogV_status = None
    _beeper = None
    _unknown_params = None
    _profile_key = "vento"
    _battery_status = None
    _all_day_mode = None
    _boost_timer_countdown = None
    _timer_status = None
    _temperature_status = None
    _motion_status = None
    _interval_ventilation_status = None
    _silent_mode_status = None
    _temperature_sensor_state = None
    _motion_sensor_state = None
    _temperature_treshold = None
    _max_speed_setpoint = None
    _silent_speed_setpoint = None
    _interval_ventilation_speed_setpoint = None
    _interval_ventilation_state = None
    _silent_mode_state = None
    _silent_mode_start_time = None
    _silent_mode_end_time = None
    _turn_on_delay_timer = None
    _temperature = None
    _co2_sensor_state = None
    _co2_treshold = None
    _co2 = None
    _outdoor_temperature = None
    _supply_temperature = None
    _exhaust_in_temperature = None
    _exhaust_out_temperature = None
    _heater_state = None
    _alarm_list = None
    _air_quality_status = None
    _recovery_efficiency = None
    _schedule_speed = None
    _frost_protection_status = None
    _voc_sensor_state = None
    _voc_treshold = None
    _voc = None
    _screen_brightness = None
    _screen_backlight_mode = None
    _screen_temperature_source = None
    _screen_air_quality_source = None
    _screen_display_mode = None
    _screen_standby_time_state = None
    _screen_display_state = None
    _screen_off_start_time = None
    _screen_off_end_time = None
    _boost_switch_status = None
    _fire_alarm_status = None
    _supply_speed_4 = None
    _exhaust_speed_4 = None
    _supply_speed_5 = None
    _exhaust_speed_5 = None
    _wifi_module_status = None
    _wifi_connection_status = None
    _heater_blowing_status = None

    def __init__(
        self,
        host,
        password="1111",
        fan_id="DEFAULT_DEVICEID",
        name="ecofanv2",
        port=4000,
    ):
        self._name = name
        self._host = host
        self._port = port
        self._type = "02"
        self._id = fan_id
        self._pwd_size = 0
        self._password = password
        self._unknown_params = {}
        self.socket = None
        self._bulk_read_supported = None
        self._profile_key = "vento"
        self._runtime_capabilities = set()
        self._set_device_profile("vento")

    def init_device(self):
        if self._id == "DEFAULT_DEVICEID":
            self.get_param("device_search")
            self._id = self.device_search
        _LOGGER.debug("EcoventV2: Initialized fan with ID: %s", self._id)
        if not self._id:
            return False
        self.get_param("unit_type")
        self._apply_device_profile()
        success = self.update()
        if success:
            self.detect_runtime_capabilities()
        return success

    @property
    def device_profile(self):
        """Return the active device profile."""
        return self.device_profiles[self._profile_key]

    @property
    def profile_key(self):
        """Return the active device profile key."""
        return self.device_profile.key

    @property
    def fan_preset_modes(self):
        """Return the Home Assistant preset modes supported by this profile."""
        return list(self.device_profile.preset_modes)

    @property
    def supports_direction(self):
        """Return whether the profile exposes airflow direction control."""
        return self.device_profile.supports_direction

    @property
    def supports_oscillation(self):
        """Return whether the profile exposes heat-recovery oscillation control."""
        return self.device_profile.supports_oscillation

    @property
    def supports_preset_speed_settings(self):
        """Return whether the profile has separate preset speed settings."""
        return self.device_profile.supports_preset_speed_settings

    @property
    def supports_percentage_control(self):
        """Return whether HA may write arbitrary percentage speed commands."""
        return self.device_profile.supports_percentage_control

    @property
    def uses_operating_mode_presets(self):
        """Return whether speed maps to autonomous operating modes."""
        return self.device_profile.uses_operating_mode_presets

    def supports_capability(self, capability):
        """Return whether the active profile declares a named capability."""
        return (
            capability in self.device_profile.capabilities
            or capability in self._runtime_capabilities
        )

    def supports_parameter(self, parameter):
        """Return whether the active protocol profile knows a parameter."""
        return self.get_params_index(parameter) is not None

    def supports_entity(
        self,
        *,
        required_params=(),
        required_capabilities=(),
        excluded_params=(),
        excluded_capabilities=(),
    ):
        """Return whether an entity description applies to this profile."""
        return (
            all(self.supports_parameter(param) for param in required_params)
            and all(
                self.supports_capability(capability)
                for capability in required_capabilities
            )
            and not any(self.supports_parameter(param) for param in excluded_params)
            and not any(
                self.supports_capability(capability)
                for capability in excluded_capabilities
            )
        )

    def parameter_options(self, parameter):
        """Return enum options for a supported parameter, if it has any."""
        index = self.get_params_index(parameter)
        if index is None:
            return None

        param = self.params.get(index) or self.write_params.get(index)
        if param[1] is None:
            return None
        return list(param[1].values())

    def detect_runtime_capabilities(self):
        """Probe optional writable capabilities that cannot be trusted by model id."""
        self._runtime_capabilities.clear()
        if self._detect_beeper_control():
            self._runtime_capabilities.add("beeper_control")

    def _detect_beeper_control(self):
        """Return whether beeper can stay off after a command that may beep."""
        original = self.beeper
        options = self.parameter_options("beeper")
        if original is None or not options or "off" not in options:
            return False

        restored = original == "off"
        try:
            if not self.set_param("beeper", "off"):
                return False
            if not self._trigger_beeper_probe_command():
                return False
            if not self._beeper_stays_off_after_probe():
                return False

            if original != "off":
                if not self.set_param("beeper", original):
                    return False
                if not self.get_param("beeper"):
                    return False
                restored = self.beeper == original
            return restored
        finally:
            if not restored and self.beeper != original:
                self.set_param("beeper", original)
                self.get_param("beeper")

    def _beeper_stays_off_after_probe(self):
        """Return whether repeated reads show the command did not re-enable beep."""
        for attempt in range(self.beeper_probe_read_count):
            if attempt:
                time.sleep(self.beeper_probe_settle_seconds)
            if not self.get_param("beeper"):
                return False
            if self.beeper != "off":
                return False
        return True

    def _trigger_beeper_probe_command(self):
        """Send a no-op command that exercises the device command beeper path."""
        if self.supports_parameter("state") and self.state is not None:
            return self.set_param("state", self.state)
        if self.supports_parameter("speed") and self.speed is not None:
            return self.set_param("speed", self.speed)
        return False

    def _profile_enum(self, enum_name):
        """Return a profile-specific enum map by class attribute name."""
        return getattr(type(self), enum_name)

    def _decode_uint(self, input, byteorder="little"):
        """Decode unsigned protocol integers from hex payload bytes."""
        return int.from_bytes(bytes.fromhex(input), byteorder=byteorder, signed=False)

    def _decode_signed_temperature(self, input):
        """Decode Breezy/Freshpoint signed tenths-of-degree temperature values."""
        value = int.from_bytes(bytes.fromhex(input), byteorder="little", signed=True)
        if value in (-32768, 32767):
            return None
        return round(value / 10, 1)

    def _decode_time_minutes_hours(self, input):
        """Decode two-byte minute/hour protocol time into HH:MM text."""
        value = bytes.fromhex(input)
        if len(value) < 2:
            return None
        return f"{value[1]:02d}:{value[0]:02d}"

    def _set_device_profile(self, profile_key):
        """Apply protocol maps for the selected device family."""
        profile = self.device_profiles[profile_key]
        previous_profile = getattr(self, "_profile_key", None)
        if previous_profile != profile_key:
            _LOGGER.info("EcoVentV2: using %s parameter profile", profile_key)

        self._profile_key = profile_key
        self.params = getattr(type(self), profile.params_name).copy()
        self.write_params = getattr(type(self), profile.write_params_name).copy()
        self._write_only_params = set(self.write_params)
        if previous_profile != profile_key:
            self._bulk_read_supported = None

    def _apply_device_profile(self):
        """Select parameter meanings after reading the model id."""
        model = self.device_models.get(self._unit_type_id)
        profile_key = model.profile_key if model is not None else "vento"
        self._set_device_profile(profile_key)

    def search_devices(self, addr="0.0.0.0", port=4000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((addr, port))
            sock.settimeout(0.5)
            ips = []
            target_host = self._host or "<broadcast>"
            target_port = self._port or port
            payload = bytes.fromhex(
                self.build_packet(
                    self.func["read"] + self.encode_params("007c"),
                    fan_id="DEFAULT_DEVICEID",
                )
            )
            i = 10
            while i > 1:
                i = i - 1
                self._device_search = self._id
                try:
                    sock.sendto(payload, (target_host, target_port))
                    data, addr = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                if (
                    self.parse_response(data)
                    and self._device_search != "DEFAULT_DEVICEID"
                ):
                    ips.append(addr[0])
                    ips = list(set(ips))
            return ips
        finally:
            sock.close()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.settimeout(0.4)
        self._socket_connected = False
        while not self._socket_connected:
            try:
                self.socket.connect((self._host, self._port))
                return self.socket
            except OSError:
                self.socket.close()
                return None

    def str2hex(self, str_msg):
        return "".join("{:02x}".format(ord(c)) for c in str_msg)

    def hex2str(self, hex_msg):
        return "".join(
            chr(int("0x" + hex_msg[i : (i + 2)], 16)) for i in range(0, len(hex_msg), 2)
        )

    def hexstr2tuple(self, hex_msg):
        return [int(hex_msg[i : (i + 2)], 16) for i in range(0, len(hex_msg), 2)]

    def chksum(self, hex_msg):
        checksum = sum(self.hexstr2tuple(hex_msg)) & 0xFFFF
        return f"{checksum & 0xFF:02x}{checksum >> 8:02x}"

    def get_size(self, str):
        return hex(len(str)).replace("0x", "").zfill(2)

    def get_header(self, fan_id=None, password=None, packet_type=None):
        fan_id = self._id if fan_id is None else fan_id
        password = self._password if password is None else password
        packet_type = self._type if packet_type is None else packet_type
        id_size = self.get_size(fan_id)
        pwd_size = self.get_size(password)
        id = self.str2hex(fan_id)
        password = self.str2hex(password)
        str = f"{packet_type}{id_size}{id}{pwd_size}{password}"
        return str

    def build_packet(self, data, fan_id=None, password=None, packet_type=None):
        payload = (
            self.get_header(fan_id=fan_id, password=password, packet_type=packet_type)
            + data
        )
        return self.HEADER + payload + self.chksum(payload)

    def validate_packet(self, data):
        if not isinstance(data, (bytes, bytearray)):
            return False
        if len(data) < 24:
            return False
        if bytes(data[:2]) != self.HEADER_BYTES:
            return False
        checksum = int.from_bytes(data[-2:], byteorder="little", signed=False)
        payload_sum = sum(data[2:-2]) & 0xFFFF
        return checksum == payload_sum

    def get_params_index(self, value):
        for params in (self.params, self.write_params):
            for i in params:
                if params[i][0] == value:
                    return i

    def get_params_values(self, idx, value):
        # print ( "EcoventV2: " + idx,  file = sys.stderr )
        index = self.get_params_index(idx)
        if index is not None:
            param = self.params.get(index) or self.write_params.get(index)
            if param[1] is not None:
                for i in param[1]:
                    if param[1][i] == value:
                        return [index, i]
            return [index, None]
        else:
            return [None, None]

    def encode_params(self, param, value=""):
        parameter = ""
        for i in range(0, len(param), 4):
            n_out = ""
            out = param[i : (i + 4)]
            if out == "0077" and value == "":
                value = "0101"
            if value != "":
                val_bytes = int(len(value) / 2)
            else:
                val_bytes = 0
            if out[:2] != "00":
                n_out = "ff" + out[:2]
            if val_bytes > 1:
                n_out += "fe" + hex(val_bytes).replace("0x", "").zfill(2) + out[2:4]
            else:
                n_out += out[2:4]
            parameter += n_out + value
            if out == "0077":
                value = ""
        return parameter

    def send(self, data):
        # print ( "EcoventV2: " + data , file = sys.stderr )
        try:
            self.socket = self.connect()
            if self.socket is None:
                return None
            payload = self.build_packet(data)
            response = self.socket.sendall(bytes.fromhex(payload))
        except socket.timeout:
            # print ( "EcoventV2: Connection timeout send to device: " + self._host , file = sys.stderr )
            return None
        except (
            OSError
        ):  # this shall include all connection errors like Aborted, Refused and Reset
            return None
        except TypeError:
            return (
                None  # this can happen if the socket connection fails and returns None
            )
        else:
            return response

    def receive(self):
        try:
            if self.socket is None:
                return False
            response = self.socket.recv(1024)
        except socket.timeout:
            # print ( "EcoventV2: Connection timeout receive from device: " + self._host , file = sys.stderr )
            return False
        except OSError:
            return False
        else:
            return response
        finally:
            if self.socket is not None:
                self.socket.close()

    def do_func(self, func, param, value="", retries=10):
        _LOGGER.debug(f"Executing function {func} with param {param} and value {value}")
        data = func + self.encode_params(param, value)
        response = False
        i = 0
        while not response:
            i = i + 1
            self.send(data)
            response = self.receive()
            if response:
                if self.parse_response(response):
                    return True
                response = False
            if i >= retries:
                # print ("EcoventV2: Timeout device: " + self._host + " bail out after " + str(i) + " retries" , file = sys.stderr )
                return False

    def update(self):
        request = ""
        for param in self.params:
            if param in self._write_only_params:
                continue
            request += hex(param).replace("0x", "").zfill(4)
        success = self._read_params(request)
        return success

    def quick_update(self):
        # just update following states ...
        # 0x0006: ["boost_status", statuses],
        # 0x000B: ["timer_counter", None],
        # 0x002D: ["analogV", None],
        # 0x0032: ["relay_status", statuses],
        # 0x0044: ["man_speed", None],
        # 0x004A: ["fan1_speed", None],
        # 0x004B: ["fan2_speed", None],
        # 0x0304: ["humidity_status", statuses],
        # 0x0305: ["analogV_status", statuses],
        return self._read_params(self.device_profile.quick_update_request)

    def update_preset_speed_settings(self):
        if not self.supports_preset_speed_settings:
            return True

        request = "003A003B003C003D003E003F"
        return self._read_params(request)

    def _read_params(self, request):
        if self._bulk_read_supported is not False and self.do_func(
            self.func["read"], request, retries=3
        ):
            self._bulk_read_supported = True
            return True

        self._bulk_read_supported = False
        success = False
        for i in range(0, len(request), 4):
            success = (
                self.do_func(self.func["read"], request[i : i + 4], retries=1)
                or success
            )
        return success

    def set_param(self, param, value):
        valpar = self.get_params_values(param, value)
        # print ( "EcoventV2: " + " " + param + "/" + value , file = sys.stderr )
        if valpar[0] is not None:
            if valpar[1] is not None:
                return self.do_func(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    hex(valpar[1]).replace("0x", "").zfill(2),
                )
            else:
                return self.do_func(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    value,
                )
        return False

    def set_params(self, values):
        """Write several profile-mapped parameters in one command."""
        request = ""
        for param, value in values.items():
            valpar = self.get_params_values(param, value)
            if valpar[0] is None:
                continue

            request += hex(valpar[0]).replace("0x", "").zfill(4)
            if valpar[1] is not None:
                request += hex(valpar[1]).replace("0x", "").zfill(2)
            else:
                request += value

        if request:
            self.do_func(self.func["write_return"], request)

    def get_param(self, param):
        idx = self.get_params_index(param)
        if idx is not None:
            #  _LOGGER.debug(f"Getting parameter {param} with index {idx}")
            return self.do_func(self.func["read"], hex(idx).replace("0x", "").zfill(4))
        return False

    def set_state_on(self):
        request = "0001"
        value = "01"
        if self.state == "off":
            self.do_func(self.func["write_return"], request, value)

    def set_state_off(self):
        request = "0001"
        value = "00"
        if self.state == "on":
            self.do_func(self.func["write_return"], request, value)

    def set_speed(self, speed):
        if speed >= 1 and speed <= 5:
            request = "0002"
            value = hex(speed).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    def set_man_speed_percent(self, speed):
        if speed >= 2 and speed <= 100:
            request = "0044"
            if self.device_profile.speed_percent_scale == "percent":
                value = speed
            else:
                value = math.ceil(255 / 100 * speed)
            value = hex(value).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.do_func ( self.func['write_return'], request, value )

    def set_man_speed(self, speed):
        if speed >= 14 and speed <= 255:
            request = "0044"
            value = speed
            value = hex(value).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.do_func ( self.func['write_return'], request, value )

    def set_airflow(self, val):
        if val >= 0 and val <= 2:
            request = "00b7"
            value = hex(val).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

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
        self.set_params(reset)

    def parse_response(self, data):
        if not self.validate_packet(data):
            return False
        pointer = 2  # discard frame marker
        length = len(data) - 2
        if len(data) < pointer + 2:
            return False
        pointer += 1  # packet type
        id_size = data[pointer]
        pointer += 1
        if len(data) < pointer + id_size + 3:
            return False
        pointer += id_size
        pwd_size = data[pointer]
        pointer += 1
        if len(data) < pointer + pwd_size + 3:
            return False
        pointer += pwd_size
        # function = data[pointer]  not used
        pointer += 1
        # from here parsing of parameters begin
        payload = data[pointer:length]
        response = bytearray()
        ext_function = 0
        value_counter = 1
        high_byte_value = 0
        parameter = 1
        for p in payload:
            if parameter and p == 0xFF:
                ext_function = 0xFF
                # print ( "def ext:" + hex(0xff) )
            elif parameter and p == 0xFE:
                ext_function = 0xFE
                # print ( "def ext:" + hex(0xfe) )
            elif parameter and p == 0xFD:
                ext_function = 0xFD
                # print ( "dev ext:" + hex(0xfd) )
            else:
                if ext_function == 0xFF:
                    high_byte_value = p
                    ext_function = 1
                elif ext_function == 0xFE:
                    value_counter = p
                    ext_function = 2
                elif ext_function == 0xFD:
                    ext_function = 0
                    response = bytearray()
                else:
                    if parameter == 1:
                        # print ("appending: " + hex(high_byte_value))
                        response.append(high_byte_value)
                        parameter = 0
                        ext_function = 0
                    else:
                        value_counter -= 1
                    response.append(p)

            if value_counter <= 0:
                parameter = 1
                value_counter = 1
                high_byte_value = 0
                ext_function = 0
                if len(response) < 2:
                    return False
                self._store_param(response)
                response = bytearray()
        return (
            ext_function == 0 and parameter == 1 and value_counter == 1 and not response
        )

    def _store_param(self, response):
        param_id = int(response[:2].hex(), 16)
        value = response[2:].hex()
        if param_id not in self.params:
            self._unknown_params[param_id] = value
            return
        try:
            setattr(self, self.params[param_id][0], value)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            self._unknown_params[param_id] = value

    def _map_value(self, mapping, value, label):
        mapped_value = mapping.get(value)
        if mapped_value is None:
            return f"Unknown {label} {value}"
        return mapped_value

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
        val = int(input, 16).to_bytes(3, "big")
        self._rtc_time = str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "

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
        self._rtc_date = (
            str(val[1])
            + " 20"
            + str(val[3])
            + "-"
            + str(val[2]).zfill(2)
            + "-"
            + str(val[0]).zfill(2)
        )

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
        self._weekly_schedule_setup = (
            self.days_of_week[val[0]]
            + "/"
            + str(val[1])
            + ": to "
            + str(val[5])
            + "h "
            + str(val[4])
            + "m "
            + self.speeds[val[2]]
        )

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

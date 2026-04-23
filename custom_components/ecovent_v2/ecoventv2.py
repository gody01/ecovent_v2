"""Library to handle communication with Wifi ecofan from TwinFresh / Blauberg."""

import logging

__version__ = "loc_0.9.29"

_LOGGER = logging.getLogger(__name__)

try:
    from . import protocol_maps
    from .fan_breezy_properties import FanBreezyPropertiesMixin
    from .fan_capabilities import FanCapabilitiesMixin
    from .fan_controls import FanControlsMixin
    from .fan_core_properties import FanCorePropertiesMixin
    from .fan_device_properties import FanDevicePropertiesMixin
    from .fan_misc_properties import FanMiscPropertiesMixin
    from .fan_protocol import FanProtocolMixin
    from .fan_protocol_parse import FanProtocolParseMixin
    from .fan_speed_properties import FanSpeedPropertiesMixin
    from .protocol_profiles import DEVICE_MODELS, DEVICE_PROFILES, UNIT_TYPE_NAMES
except ImportError:
    import protocol_maps
    from fan_breezy_properties import FanBreezyPropertiesMixin
    from fan_capabilities import FanCapabilitiesMixin
    from fan_controls import FanControlsMixin
    from fan_core_properties import FanCorePropertiesMixin
    from fan_device_properties import FanDevicePropertiesMixin
    from fan_misc_properties import FanMiscPropertiesMixin
    from fan_protocol import FanProtocolMixin
    from fan_protocol_parse import FanProtocolParseMixin
    from fan_speed_properties import FanSpeedPropertiesMixin
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


class Fan(
    FanCapabilitiesMixin,
    FanControlsMixin,
    FanCorePropertiesMixin,
    FanDevicePropertiesMixin,
    FanBreezyPropertiesMixin,
    FanMiscPropertiesMixin,
    FanProtocolMixin,
    FanProtocolParseMixin,
    FanSpeedPropertiesMixin,
):
    """Class to communicate with the ecofan"""

    HEADER = "FDFD"
    HEADER_BYTES = bytes.fromhex(HEADER)
    beeper_probe_read_count = 3
    beeper_probe_settle_seconds = 1

    # Protocol enum maps and parameter tables live in protocol_maps.py.
    func = protocol_maps.func
    states = protocol_maps.states
    speeds = protocol_maps.speeds
    freshbox_speeds = protocol_maps.freshbox_speeds
    battery_statuses = protocol_maps.battery_statuses
    humidity_permission_modes = protocol_maps.humidity_permission_modes
    timer_modes = protocol_maps.timer_modes
    statuses = protocol_maps.statuses
    air_quality_statuses = protocol_maps.air_quality_statuses
    frost_protection_statuses = protocol_maps.frost_protection_statuses
    screen_backlight_modes = protocol_maps.screen_backlight_modes
    screen_temperature_sources = protocol_maps.screen_temperature_sources
    screen_air_quality_sources = protocol_maps.screen_air_quality_sources
    screen_display_modes = protocol_maps.screen_display_modes
    screen_standby_time_states = protocol_maps.screen_standby_time_states
    screen_display_states = protocol_maps.screen_display_states
    arc_airflows_low = protocol_maps.arc_airflows_low
    arc_airflows_medium = protocol_maps.arc_airflows_medium
    arc_airflows_high = protocol_maps.arc_airflows_high
    bstatuses = protocol_maps.bstatuses
    sound_emitter_states = protocol_maps.sound_emitter_states
    boost_statuses = protocol_maps.boost_statuses
    airflows = protocol_maps.airflows
    alarms = protocol_maps.alarms
    days_of_week = protocol_maps.days_of_week
    filters = protocol_maps.filters
    unit_types = protocol_maps.unit_types
    wifi_operation_modes = protocol_maps.wifi_operation_modes
    wifi_enc_types = protocol_maps.wifi_enc_types
    wifi_dhcps = protocol_maps.wifi_dhcps
    params = protocol_maps.params
    extract_fan_params = protocol_maps.extract_fan_params
    breezy_params = protocol_maps.breezy_params
    freshbox_params = protocol_maps.freshbox_params
    arc_params = protocol_maps.arc_params
    write_params = protocol_maps.write_params
    extract_fan_write_params = protocol_maps.extract_fan_write_params
    breezy_write_params = protocol_maps.breezy_write_params
    freshbox_write_params = protocol_maps.freshbox_write_params
    arc_write_params = protocol_maps.arc_write_params

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
    _rtc_weekday = None
    _weekly_schedule_state = None
    _weekly_schedule_setup = None
    _weekly_schedule_setup_record = None
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
    _low_battery_status = None
    _all_day_mode = None
    _boost_timer_countdown = None
    _timer_status = None
    _temperature_status = None
    _motion_status = None
    _light_status = None
    _interval_ventilation_status = None
    _silent_mode_status = None
    _temperature_sensor_state = None
    _motion_sensor_state = None
    _light_sensor_state = None
    _air_quality_sensor_state = None
    _humidity_airflow = None
    _motion_light_airflow = None
    _air_quality_airflow = None
    _interval_ventilation_airflow = None
    _all_day_airflow = None
    _temperature_airflow = None
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
    _room_temperature = None
    _air_quality = None
    _air_quality_treshold = None
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

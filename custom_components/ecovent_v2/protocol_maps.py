"""EcoVent protocol enum and parameter maps."""

try:
    from .protocol_profiles import UNIT_TYPE_NAMES
except ImportError:
    from protocol_profiles import UNIT_TYPE_NAMES

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
arc_airflows_low = {1: "20_m3h", 2: "40_m3h", 3: "60_m3h"}
arc_airflows_medium = {
    2: "40_m3h",
    3: "60_m3h",
    4: "90_m3h",
    5: "115_m3h",
}
arc_airflows_high = {3: "60_m3h", 4: "90_m3h", 5: "115_m3h"}

bstatuses = {0: "off", 1: "on", 2: "silent"}
sound_emitter_states = {0: "off", 1: "on", 2: "toggle"}

boost_statuses = {0: "off", 1: "on", 2: "delay"}

airflows = {0: "ventilation", 1: "heat_recovery", 2: "air_supply"}

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
    0x006F: ["rtc_time", None],
    0x0070: ["rtc_date", None],
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
    0x0077: ["weekly_schedule_setup", None],
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
    0x0306: ["schedule_speed", speeds],
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
    0x0072: ["weekly_schedule_state", states],
    0x0077: ["weekly_schedule_setup", None],
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

# Arc Smart profile from the 2025 Smart House guide. This device does not
# document normal unit on/off or speed-mode rows, so expose it conservatively
# as a read-focused environmental fan profile.
arc_params = {
    0x0006: ["boost_status", states],
    0x0007: ["timer_status", statuses],
    0x000B: ["timer_counter", None],
    0x000F: ["humidity_sensor_state", humidity_permission_modes],
    0x0019: ["humidity_treshold", None],
    0x0021: ["room_temperature", None],
    0x0024: ["battery_voltage", None],
    0x0025: ["humidity", None],
    0x004B: ["fan1_speed", None],
    0x0066: ["boost_time", None],
    0x007C: ["device_search", None],
    0x0083: ["low_battery_status", statuses],
    0x0085: ["cloud_server_state", states],
    0x0086: ["firmware", None],
    0x00A3: ["current_wifi_ip", None],
    0x00B9: ["unit_type", unit_types],
    0x0304: ["humidity_status", statuses],
    0x030D: ["all_day_mode", states],
    0x030E: ["light_status", statuses],
    0x030F: ["motion_status", statuses],
    0x0310: ["interval_ventilation_status", statuses],
    0x0311: ["silent_mode_status", statuses],
    0x0312: ["air_quality_status", statuses],
    0x0313: ["light_sensor_state", states],
    0x0314: ["motion_sensor_state", states],
    0x0315: ["air_quality_sensor_state", humidity_permission_modes],
    0x0316: ["interval_ventilation_state", states],
    0x0317: ["silent_mode_state", states],
    0x0318: ["silent_mode_start_time", None],
    0x0319: ["silent_mode_end_time", None],
    0x031A: ["humidity_airflow", arc_airflows_high],
    0x031B: ["motion_light_airflow", arc_airflows_medium],
    0x031C: ["air_quality_airflow", arc_airflows_high],
    0x031D: ["interval_ventilation_airflow", arc_airflows_low],
    0x031E: ["all_day_airflow", arc_airflows_low],
    0x031F: ["air_quality_treshold", None],
    0x0320: ["air_quality", None],
    0x0323: ["temperature_status", statuses],
    0x0324: ["temperature_sensor_state", states],
    0x0325: ["temperature_treshold", None],
    0x032F: ["temperature_airflow", arc_airflows_high],
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

arc_write_params = {}

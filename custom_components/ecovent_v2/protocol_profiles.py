"""EcoVent protocol profile definitions."""

try:
    from .protocol_metadata import DeviceProfile, OPERATING_MODE_PRESETS
except ImportError:
    from protocol_metadata import DeviceProfile, OPERATING_MODE_PRESETS


DEVICE_PROFILES = {
    "vento": DeviceProfile(
        key="vento",
        params_name="params",
        write_params_name="write_params",
        quick_update_request="0006000B002D003200440016004A004B03040305",
        preset_modes=("off", "low", "medium", "high", "manual"),
        boost_statuses_name="boost_statuses",
        humidity_sensor_states_name="states",
        schedule_speed_modes=("low", "medium", "high"),
        capabilities=frozenset(
            {
                "analog_voltage",
                "airflow",
                "battery_voltage",
                "beeper_status",
                "binary_diagnostics",
                "boost_delay_status",
                "filter_maintenance",
                "night_party_timers",
                "sensor_switches",
                "timer_mode",
            }
        ),
        supports_direction=True,
        supports_oscillation=True,
        supports_preset_speed_settings=True,
    ),
    "extract_fan": DeviceProfile(
        key="extract_fan",
        params_name="extract_fan_params",
        write_params_name="extract_fan_write_params",
        quick_update_request="0001000400050008000A000B000C000D000E002E0031",
        preset_modes=("off", *OPERATING_MODE_PRESETS),
        boost_statuses_name="states",
        humidity_sensor_states_name="humidity_permission_modes",
        schedule_speed_modes=(),
        capabilities=frozenset(
            {
                "battery_status",
                "toggle_boost_status",
                "speed_setpoints",
                "temperature",
            }
        ),
        uses_operating_mode_presets=True,
    ),
    "breezy": DeviceProfile(
        key="breezy",
        params_name="breezy_params",
        write_params_name="breezy_write_params",
        quick_update_request="0007000B00250027004A004B0081008300840129030B0320",
        preset_modes=("off", "low", "medium", "high", "speed_4", "speed_5", "manual"),
        boost_statuses_name="statuses",
        humidity_sensor_states_name="states",
        schedule_speed_modes=("low", "medium", "high", "speed_4", "speed_5"),
        capabilities=frozenset(
            {
                "airflow",
                "air_quality",
                "battery_voltage",
                "breezy_screen",
                "co2",
                "filter_maintenance",
                "heater",
                "night_party_timers",
                "sensor_switches",
                "temperature_probes",
                "timer_mode",
                "voc",
            }
        ),
        supports_direction=True,
        supports_oscillation=True,
        supports_preset_speed_settings=True,
        speed_percent_scale="percent",
    ),
    "freshbox": DeviceProfile(
        key="freshbox",
        params_name="freshbox_params",
        write_params_name="freshbox_write_params",
        quick_update_request="0006000B003200330081008300A100B6",
        preset_modes=("off", "speed_1", "speed_2", "speed_3", "speed_4", "speed_5"),
        boost_statuses_name="statuses",
        humidity_sensor_states_name="states",
        schedule_speed_modes=("speed_1", "speed_2", "speed_3", "speed_4", "speed_5"),
        capabilities=frozenset(
            {
                "filter_maintenance",
                "timer_mode",
            }
        ),
        speed_percent_scale="percent",
        supports_percentage_control=False,
    ),
    "arc": DeviceProfile(
        key="arc",
        params_name="arc_params",
        write_params_name="arc_write_params",
        quick_update_request="0007000B00210025004B0304030E030F0310031103120320",
        preset_modes=(),
        boost_statuses_name="states",
        humidity_sensor_states_name="humidity_permission_modes",
        schedule_speed_modes=(),
        capabilities=frozenset(
            {
                "arc_environment",
                "battery_voltage",
                "binary_diagnostics",
                "timer_mode",
            }
        ),
        supports_percentage_control=False,
    ),
}


try:
    from .protocol_model_catalog import DEVICE_MODELS
except ImportError:
    from protocol_model_catalog import DEVICE_MODELS


UNIT_TYPE_NAMES = {
    unit_type: model.display_name for unit_type, model in DEVICE_MODELS.items()
}

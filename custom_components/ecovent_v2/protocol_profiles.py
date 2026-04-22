"""EcoVent protocol model and profile metadata."""

from dataclasses import dataclass


OPERATING_MODE_PRESETS = (
    "all_day",
    "humidity_trigger",
    "humidity_manual",
    "temperature_trigger",
    "motion_trigger",
    "external_switch_trigger",
    "interval_ventilation",
    "silent",
    "boost",
)


VENTO_SMART_HOME_MANUAL_URL = (
    "https://blaubergventilatoren.net/download/vento-inhome-manual-14758.pdf"
)
SMART_WIFI_MANUAL_URL = (
    "https://blaubergventilatoren.net/download/smart-wi-fi-manual-8533.pdf"
)
TWINFRESH_STYLE_MANUAL_URL = (
    "https://ventilation-system.com/download/twinfresh-style-wi-fi-manual-19765.pdf"
)
TWINFRESH_STYLE_MINI_MANUAL_URL = (
    "https://ventilation-system.com/download/twinfresh-style-wi-fi-mini-manual-19765.pdf"
)
BREEZY_ECO_MANUAL_URL = (
    "https://ventilation-system.com/download/breezy-eco-manual-21433.pdf"
)
FRESHPOINT_MANUAL_URL = (
    "https://blaubergventilatoren.net/download/freshpoint-manual-16999.pdf"
)
FRESHBOX_100_WIFI_MANUAL_URL = (
    "https://blaubergventilatoren.net/download/freshbox-100-wifi-datasheet-7508.pdf"
)


@dataclass(frozen=True)
class DeviceProfile:
    """Protocol capabilities and parameter maps for a device family."""

    key: str
    params_name: str
    write_params_name: str
    quick_update_request: str
    preset_modes: tuple[str, ...]
    boost_statuses_name: str
    humidity_sensor_states_name: str
    capabilities: frozenset[str] = frozenset()
    supports_direction: bool = False
    supports_oscillation: bool = False
    supports_preset_speed_settings: bool = False
    uses_operating_mode_presets: bool = False
    speed_percent_scale: str = "byte"
    supports_percentage_control: bool = True


@dataclass(frozen=True)
class DeviceModel:
    """Known unit type and the protocol profile it uses."""

    name: str
    profile_key: str = "vento"
    aliases: tuple[str, ...] = ()
    source_documents: tuple[str, ...] = ()

    @property
    def display_name(self):
        """Return a stable model name including known relabels."""
        if not self.aliases:
            return self.name
        return " / ".join((self.name, *self.aliases))


DEVICE_PROFILES = {
    "vento": DeviceProfile(
        key="vento",
        params_name="params",
        write_params_name="write_params",
        quick_update_request="0006000B002D003200440016004A004B03040305",
        preset_modes=("off", "low", "medium", "high", "manual"),
        boost_statuses_name="boost_statuses",
        humidity_sensor_states_name="states",
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
        preset_modes=("speed_1", "speed_2", "speed_3", "speed_4", "speed_5"),
        boost_statuses_name="statuses",
        humidity_sensor_states_name="states",
        capabilities=frozenset(
            {
                "filter_maintenance",
                "timer_mode",
            }
        ),
        speed_percent_scale="percent",
        supports_percentage_control=False,
    ),
}


DEVICE_MODELS = {
    0x0300: DeviceModel(
        "Vento Expert A50-1/A85-1/A100-1 W V.2",
        aliases=("TwinFresh Expert RW1-50/85/100 V.2",),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0400: DeviceModel(
        "Vento Expert Duo A30-1 W V.2",
        aliases=("TwinFresh Expert Duo RW1-30 V.2",),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0500: DeviceModel(
        "Vento Expert A30 W V.2",
        aliases=("TwinFresh Expert RW-30 V.2",),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0E00: DeviceModel(
        "TwinFresh Style Wifi V.2",
        aliases=("Oxxify smart 50",),
        source_documents=(
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x1100: DeviceModel(
        "Breezy 160",
        profile_key="breezy",
        aliases=("Freshpoint 160", "Vents Breezy 160-E"),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1400: DeviceModel(
        "Breezy Eco 160",
        profile_key="breezy",
        aliases=("Freshpoint Eco 160",),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1600: DeviceModel(
        "Breezy 200",
        profile_key="breezy",
        aliases=("Freshpoint 200",),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1800: DeviceModel(
        "Breezy Eco 200",
        profile_key="breezy",
        aliases=("Freshpoint Eco 200",),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1A00: DeviceModel(
        "TwinFresh Atmo / newer Blauberg Vento",
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x1B00: DeviceModel(
        "Vento inHome S11 W",
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x1C00: DeviceModel(
        "TwinFresh Atmo 160",
        source_documents=(
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0600: DeviceModel(
        "Blauberg Smart Wi-Fi extract fan",
        "extract_fan",
        source_documents=(SMART_WIFI_MANUAL_URL,),
    ),
    # Freshbox uses the same BGCP/UDP framing but a different AHU parameter map.
    # Its unit type is documented as 0x0002; this parser stores the two response
    # bytes as a hex integer, so the little-endian value appears as 0x0200.
    0x0200: DeviceModel(
        "Freshbox 100 WiFi",
        "freshbox",
        source_documents=(FRESHBOX_100_WIFI_MANUAL_URL,),
    ),
}


UNIT_TYPE_NAMES = {
    unit_type: model.display_name for unit_type, model in DEVICE_MODELS.items()
}

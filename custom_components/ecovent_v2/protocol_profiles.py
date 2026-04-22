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
MICRA_100_WIFI_MANUAL_URL = (
    "https://ventilation-system.com/download/micra-100-wifi-manual-19886.pdf"
)
ARC_SMART_MANUAL_URL = (
    "https://ventilation-system.com/download/arc-smart-manual-21863.pdf"
)
O2_SUPREME_MANUAL_URL = (
    "https://blaubergventilatoren.net/download/o2-supreme-manual-15274.pdf"
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
class MarketingName:
    """Marketing model name with its brand layer and evidence strength."""

    brand: str
    family: str
    model: str
    evidence: str
    source_documents: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceModel:
    """Known unit type and the protocol profile it uses."""

    name: str
    profile_key: str = "vento"
    aliases: tuple[str, ...] = ()
    source_documents: tuple[str, ...] = ()
    device_type: int | None = None
    parser_key: int | None = None
    manufacturer_group: str = "Blauberg Group / VENTS platform"
    official_names: tuple[MarketingName, ...] = ()
    relabels: tuple[MarketingName, ...] = ()
    candidates: tuple[MarketingName, ...] = ()

    @property
    def display_name(self):
        """Return the concise parser-facing model name."""
        names = [self.name, *self.aliases]
        return " / ".join(dict.fromkeys(names))


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
        preset_modes=("off", "speed_1", "speed_2", "speed_3", "speed_4", "speed_5"),
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
    "arc": DeviceProfile(
        key="arc",
        params_name="arc_params",
        write_params_name="arc_write_params",
        quick_update_request="0007000B00210025004B0304030E030F0310031103120320",
        preset_modes=(),
        boost_statuses_name="states",
        humidity_sensor_states_name="humidity_permission_modes",
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


DEVICE_MODELS = {
    0x0300: DeviceModel(
        "Blauberg VENTO Expert / VENTS TwinFresh Expert",
        device_type=3,
        parser_key=0x0300,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert",
                "VENTO Expert A50-1 S10 W V.2",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert",
                "VENTO Expert A85-1 S10 W V.2",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert",
                "VENTO Expert A100-1 S10 W V.2",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert",
                "VENTO Expert A50-1 W V.3",
                "official_listing",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert",
                "TwinFresh Expert RW1-50 V.2",
                "official_group",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert",
                "TwinFresh Expert RW1-85 V.2",
                "official_group",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert",
                "TwinFresh Expert RW1-100 V.2",
                "official_group",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert",
                "TwinFresh Expert RW1-50 V.3",
                "official_listing",
            ),
        ),
        relabels=(
            MarketingName(
                "SIKU",
                "SIKU RV",
                "SIKU RV 50 W Pro WiFi V2",
                "official_listing",
            ),
            MarketingName(
                "SIKU",
                "SIKU RV",
                "SIKU RV 50 W PRO WIFI V2",
                "official_listing",
            ),
            MarketingName("DUKA", "DUKA One", "DUKA One S6W", "community_tested"),
            MarketingName("RL Raumklima", "RL PRO-Serie", "RL 50RVW", "community_tested"),
            MarketingName(
                "Winzel",
                "Winzel Expert",
                "Winzel Expert WiFi RW1-50 P",
                "app_by_blauberg",
            ),
            MarketingName(
                "Winzel",
                "Winzel Expert",
                "Blauberg Winzel Expert WiFi RW1-50 P",
                "app_by_blauberg",
            ),
        ),
        candidates=(
            MarketingName(
                "Flexit", "Roomie One", "Flexit Roomie One WiFi V2", "candidate"
            ),
            MarketingName("DUKA", "DUKA One", "DUKA One Pro 50 S Wi-Fi", "candidate"),
            MarketingName("NIBE", "DVC 10", "NIBE DVC 10", "candidate"),
            MarketingName("NIBE", "DVC 10", "NIBE DVC 10-50W", "candidate"),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0400: DeviceModel(
        "Blauberg VENTO Expert Duo / VENTS TwinFresh Expert Duo",
        device_type=4,
        parser_key=0x0400,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert Duo",
                "VENTO Expert DUO A30-1 S10 W V.2",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert Duo",
                "VENTO Expert DUO A30-1 S10 W V.2 BLK",
                "official_listing",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert Duo",
                "TwinFresh Expert Duo RW1-30 V.2",
                "official_group",
            ),
        ),
        relabels=(
            MarketingName(
                "SIKU",
                "SIKU RV",
                "SIKU RV 30 DW Pro Duo WiFi V2",
                "official_listing",
            ),
            MarketingName(
                "SIKU",
                "SIKU RV",
                "SIKU RV 30 DW PRO DUO WIFI V2",
                "official_listing",
            ),
            MarketingName(
                "Flexit", "Roomie Dual", "Flexit Roomie Dual Wifi", "community_tested"
            ),
            MarketingName("Flexit", "Roomie Dual", "Roomie Dual WiFi V2", "candidate"),
            MarketingName("DUKA", "DUKA One", "DUKA One S6BW", "community_tested"),
            MarketingName("RL Raumklima", "RL PRO-Serie", "RL 30DVW", "community_tested"),
        ),
        candidates=(
            MarketingName("Flexit", "Aura", "Flexit Aura", "candidate"),
            MarketingName("Flexit", "Muto", "Flexit Muto", "candidate"),
            MarketingName("NIBE", "DVC 10", "NIBE DVC 10-D30W", "candidate"),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0500: DeviceModel(
        "Blauberg VENTO Expert A30 / VENTS TwinFresh Expert RW-30",
        device_type=5,
        parser_key=0x0500,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO Expert",
                "VENTO Expert A30 S10 W V.2",
                "official_group",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Expert",
                "TwinFresh Expert RW-30 V.2",
                "official_group",
            ),
        ),
        candidates=(
            MarketingName(
                "SIKU", "SIKU RV", "SIKU RV 25 W Pro WiFi V2", "candidate"
            ),
            MarketingName("RL Raumklima", "RL PRO-Serie", "RL 25RVW", "candidate"),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0E00: DeviceModel(
        "VENTS TwinFresh Style Wi-Fi",
        device_type=14,
        parser_key=0x0E00,
        official_names=(
            MarketingName(
                "VENTS", "TwinFresh Style", "Vents TwinFresh Style Wi-Fi", "official_group"
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Style",
                "TwinFresh Style Wi-Fi",
                "protocol_pdf",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Style",
                "Vents TwinFresh Style Frost Wi-Fi",
                "official_group",
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Style",
                "Vents TwinFresh Style Wi-Fi mini",
                "official_group",
            ),
        ),
        relabels=(
            MarketingName("OXXIFY", "OXXIFY.smart", "OXXIFY.smart 50", "observed"),
            MarketingName("Oxxify", "Oxxify.smart", "Oxxify.smart 50", "observed"),
            MarketingName("Oxxify", "Oxxify smart", "Oxxify smart 50", "observed"),
        ),
        candidates=(
            MarketingName("Oxxify", "Oxxify.smart", "Oxxify.smart 30", "candidate"),
            MarketingName("Oxxify", "Oxxify.smart", "oxxify.smart 50k", "candidate"),
            MarketingName("OXXIFY", "OXXIFY.pro", "OXXIFY.pro 50", "candidate"),
            MarketingName("OXXIFY", "OXXIFY.eco", "OXXIFY.eco 50", "candidate"),
        ),
        source_documents=(
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0D00: DeviceModel(
        "VENTS Arc Smart / Blauberg O2 Supreme",
        "arc",
        device_type=13,
        parser_key=0x0D00,
        official_names=(
            MarketingName("VENTS", "Arc Smart", "Vents Arc Smart", "official_group"),
            MarketingName("VENTS", "Arc Smart", "Vents Arc Smart white", "official_group"),
            MarketingName("VENTS", "Arc Smart", "Vents Arc Smart black", "official_group"),
            MarketingName(
                "Blauberg Ventilatoren",
                "O2 Supreme",
                "Blauberg O2 Supreme",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "O2 Supreme",
                "O2 Supreme white",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "O2 Supreme",
                "O2 Supreme black",
                "official_group",
            ),
        ),
        source_documents=(ARC_SMART_MANUAL_URL, O2_SUPREME_MANUAL_URL),
    ),
    0x1100: DeviceModel(
        "VENTS Breezy 160 / Blauberg Freshpoint 160",
        profile_key="breezy",
        device_type=17,
        parser_key=0x1100,
        official_names=(
            MarketingName("VENTS", "Breezy", "Vents Breezy 160", "official_group"),
            MarketingName("VENTS", "Breezy", "Vents Breezy 160-E", "official_group"),
            MarketingName(
                "VENTS", "Breezy", "Vents Breezy 160-E Smart", "official_group"
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 160",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 160-E Pro L055",
                "official_listing",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 160-E Pro L07",
                "official_listing",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 160-E Pro L1",
                "official_listing",
            ),
        ),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1400: DeviceModel(
        "VENTS Breezy Eco 160 / Blauberg Freshpoint Eco 160",
        profile_key="breezy",
        device_type=20,
        parser_key=0x1400,
        official_names=(
            MarketingName("VENTS", "Breezy Eco", "Vents Breezy Eco 160", "official_group"),
            MarketingName(
                "VENTS", "Breezy Eco", "Vents Breezy Eco 160-E", "official_group"
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint Eco",
                "Freshpoint Eco 160",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint Eco",
                "Freshpoint Eco 160-E L07",
                "official_listing",
            ),
        ),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1600: DeviceModel(
        "VENTS Breezy 200 / Blauberg Freshpoint 200",
        profile_key="breezy",
        device_type=22,
        parser_key=0x1600,
        official_names=(
            MarketingName("VENTS", "Breezy", "Vents Breezy 200-E", "official_group"),
            MarketingName(
                "VENTS", "Breezy", "Vents Breezy 200-E Smart", "official_group"
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 200",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 200-E Pro L055",
                "official_listing",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 200-E Pro L07",
                "official_listing",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint",
                "Freshpoint 200-E Pro L1",
                "official_listing",
            ),
        ),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1800: DeviceModel(
        "VENTS Breezy Eco 200 / Blauberg Freshpoint Eco 200",
        profile_key="breezy",
        device_type=24,
        parser_key=0x1800,
        official_names=(
            MarketingName(
                "VENTS", "Breezy Eco", "Vents Breezy Eco 200", "protocol_pdf"
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshpoint Eco",
                "Freshpoint Eco 200",
                "protocol_pdf",
            ),
        ),
        source_documents=(
            BREEZY_ECO_MANUAL_URL,
            FRESHPOINT_MANUAL_URL,
        ),
    ),
    0x1A00: DeviceModel(
        "VENTO inHome old / TwinFresh Atmo old",
        device_type=26,
        parser_key=0x1A00,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome",
                "protocol_pdf",
            ),
            MarketingName("VENTS", "TwinFresh Atmo", "TwinFresh Atmo", "protocol_pdf"),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x1B00: DeviceModel(
        "VENTO inHome 100 / TwinFresh Atmo 100",
        device_type=27,
        parser_key=0x1B00,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome 100",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome mini",
                "official_listing",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome mini W",
                "official_listing",
            ),
            MarketingName("VENTS", "TwinFresh Atmo", "TwinFresh Atmo 100", "protocol_pdf"),
            MarketingName(
                "VENTS", "TwinFresh Atmo", "Vents TwinFresh Atmo mini", "official_listing"
            ),
            MarketingName(
                "VENTS",
                "TwinFresh Atmo",
                "Vents TwinFresh Atmo mini Wi-Fi",
                "official_listing",
            ),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x1C00: DeviceModel(
        "VENTO inHome 160 / TwinFresh Atmo 160",
        device_type=28,
        parser_key=0x1C00,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome 160",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "VENTO inHome",
                "VENTO inHome W",
                "official_listing",
            ),
            MarketingName("VENTS", "TwinFresh Atmo", "TwinFresh Atmo 160", "protocol_pdf"),
            MarketingName(
                "VENTS", "TwinFresh Atmo", "Vents TwinFresh Atmo Wi-Fi", "official_listing"
            ),
        ),
        source_documents=(
            VENTO_SMART_HOME_MANUAL_URL,
            TWINFRESH_STYLE_MANUAL_URL,
            TWINFRESH_STYLE_MINI_MANUAL_URL,
        ),
    ),
    0x0600: DeviceModel(
        "Blauberg Smart Wi-Fi / VENTS iFan Wi-Fi",
        "extract_fan",
        parser_key=0x0600,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "Smart",
                "Blauberg Smart Wi-Fi",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Smart",
                "Smart IR Wi-Fi",
                "official_group",
            ),
            MarketingName("VENTS", "iFan", "Vents iFan Wi-Fi", "official_group"),
            MarketingName("VENTS", "iFan", "Vents iFan Move Wi-Fi", "official_group"),
        ),
        source_documents=(SMART_WIFI_MANUAL_URL,),
    ),
    # Freshbox uses the same BGCP/UDP framing but a different AHU parameter map.
    # Its unit type is documented as 0x0002; this parser stores the two response
    # bytes as a hex integer, so the little-endian value appears as 0x0200.
    0x0200: DeviceModel(
        "Blauberg Freshbox 100 WiFi / VENTS Micra 100 WiFi",
        "freshbox",
        device_type=2,
        parser_key=0x0200,
        official_names=(
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshbox",
                "Freshbox 100 WiFi",
                "protocol_pdf",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshbox",
                "Freshbox 100 ERV WiFi",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshbox",
                "Freshbox E-100 WiFi",
                "official_group",
            ),
            MarketingName(
                "Blauberg Ventilatoren",
                "Freshbox",
                "Freshbox E2-100 ERV WiFi",
                "official_group",
            ),
            MarketingName("VENTS", "Micra", "Vents Micra 100 WiFi", "protocol_pdf"),
            MarketingName("VENTS", "Micra", "Vents Micra 100 ERV WiFi", "official_group"),
            MarketingName("VENTS", "Micra", "Vents Micra 100 E WiFi", "official_group"),
            MarketingName(
                "VENTS", "Micra", "Vents Micra 100 E2 ERV WiFi", "official_group"
            ),
        ),
        source_documents=(FRESHBOX_100_WIFI_MANUAL_URL, MICRA_100_WIFI_MANUAL_URL),
    ),
}


UNIT_TYPE_NAMES = {
    unit_type: model.display_name for unit_type, model in DEVICE_MODELS.items()
}

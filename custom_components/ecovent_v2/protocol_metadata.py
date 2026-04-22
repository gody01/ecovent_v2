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

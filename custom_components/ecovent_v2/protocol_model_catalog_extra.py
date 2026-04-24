"""EcoVent protocol model-name catalogue extension."""

try:
    from .protocol_metadata import (
        BREEZY_ECO_MANUAL_URL,
        FRESHBOX_100_WIFI_MANUAL_URL,
        FRESHPOINT_MANUAL_URL,
        MICRA_100_WIFI_MANUAL_URL,
        SMART_WIFI_MANUAL_URL,
        TWINFRESH_STYLE_MANUAL_URL,
        TWINFRESH_STYLE_MINI_MANUAL_URL,
        VENTO_SMART_HOME_MANUAL_URL,
        DeviceModel,
        MarketingName,
    )
except ImportError:
    from protocol_metadata import (
        BREEZY_ECO_MANUAL_URL,
        FRESHBOX_100_WIFI_MANUAL_URL,
        FRESHPOINT_MANUAL_URL,
        MICRA_100_WIFI_MANUAL_URL,
        SMART_WIFI_MANUAL_URL,
        TWINFRESH_STYLE_MANUAL_URL,
        TWINFRESH_STYLE_MINI_MANUAL_URL,
        VENTO_SMART_HOME_MANUAL_URL,
        DeviceModel,
        MarketingName,
    )

EXTRA_DEVICE_MODELS = {
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

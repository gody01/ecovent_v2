"""EcoVent protocol model-name catalogue."""

try:
    from .protocol_metadata import (
        ARC_SMART_MANUAL_URL,
        O2_SUPREME_MANUAL_URL,
        TWINFRESH_STYLE_MANUAL_URL,
        TWINFRESH_STYLE_MINI_MANUAL_URL,
        VENTO_SMART_HOME_MANUAL_URL,
        DeviceModel,
        MarketingName,
    )
except ImportError:
    from protocol_metadata import (
        ARC_SMART_MANUAL_URL,
        O2_SUPREME_MANUAL_URL,
        TWINFRESH_STYLE_MANUAL_URL,
        TWINFRESH_STYLE_MINI_MANUAL_URL,
        VENTO_SMART_HOME_MANUAL_URL,
        DeviceModel,
        MarketingName,
    )

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
}

try:
    from .protocol_model_catalog_extra import EXTRA_DEVICE_MODELS
except ImportError:
    from protocol_model_catalog_extra import EXTRA_DEVICE_MODELS

DEVICE_MODELS.update(EXTRA_DEVICE_MODELS)

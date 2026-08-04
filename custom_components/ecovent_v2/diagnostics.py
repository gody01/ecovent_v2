"""Diagnostics for EcoVent V2."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .protocol_diagnostics import (
    hardware_profile_mismatch_issue_url,
    unsupported_optional_poll_parameter_details,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for one EcoVent V2 config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    fan = coordinator._fan
    unsupported_optional = unsupported_optional_poll_parameter_details(fan)

    diagnostics: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
        },
        "device": {
            "name": fan.name,
            "profile": fan.profile_key,
            "unit_type": fan.unit_type,
            "unit_type_id": getattr(fan, "_unit_type_id", None),
            "firmware": fan.firmware,
            "device_id_known": bool(fan.id and fan.id != "DEFAULT_DEVICEID"),
            "transport": getattr(fan, "transport", "bgcp_udp"),
        },
        "protocol": {
            "bulk_read_supported": getattr(fan, "_bulk_read_supported", None),
            "missing_required_params": sorted(fan.last_missing_required_params),
            "missing_optional_params": sorted(fan.last_missing_optional_params),
            "unsupported_params": sorted(fan.last_unsupported_params),
            "unsupported_optional_poll_params": list(unsupported_optional),
        },
    }
    if unsupported_optional:
        diagnostics["hardware_profile_mismatch_issue_url"] = (
            hardware_profile_mismatch_issue_url(fan)
        )
    return diagnostics

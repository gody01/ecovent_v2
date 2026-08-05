"""Protocol diagnostics surfaced through Home Assistant repairs."""

from __future__ import annotations

from urllib.parse import urlencode

GITHUB_NEW_ISSUE_URL = "https://github.com/gody01/ecovent_v2/issues/new"


def _format_param_id(param_id: int) -> str:
    return f"0x{param_id:04X}"


def unsupported_optional_poll_parameter_details(fan) -> tuple[dict[str, str], ...]:
    """Return public-safe details about hardware-rejected optional poll rows."""
    details = []
    for param_id in sorted(fan.unsupported_optional_poll_parameter_ids()):
        definition = fan.params.get(param_id)
        name = definition[0] if definition is not None else "unknown"
        details.append({"id": _format_param_id(param_id), "name": name})
    return tuple(details)


def unsupported_optional_poll_parameter_summary(fan) -> str:
    """Return a compact human-readable unsupported row summary."""
    return ", ".join(
        f"{detail['id']} ({detail['name']})"
        for detail in unsupported_optional_poll_parameter_details(fan)
    )


def hardware_profile_mismatch_issue_body(fan) -> str:
    """Build a prefilled GitHub issue body for live hardware/profile mismatches."""
    unsupported = unsupported_optional_poll_parameter_details(fan)
    unsupported_rows = "\n".join(
        f"- `{detail['id']}` `{detail['name']}`" for detail in unsupported
    )
    if not unsupported_rows:
        unsupported_rows = "- none detected"

    unit_type_id = getattr(fan, "_unit_type_id", None)
    unit_type_text = f"0x{unit_type_id:04X}" if unit_type_id is not None else "unknown"

    return "\n".join(
        (
            "### Detected hardware/profile mismatch",
            "",
            "EcoVent V2 detected that this device explicitly rejects optional "
            "registers that the current profile expects.",
            "",
            "Please add the exact marketing model, photos of the label, firmware "
            "version, and any extra hardware options installed.",
            "",
            "### Detected device context",
            "",
            f"- Integration profile: `{fan.profile_key}`",
            f"- Reported unit type: `{fan.unit_type}`",
            f"- Unit type id: `{unit_type_text}`",
            f"- Firmware: `{fan.firmware}`",
            f"- Device id: `{'known' if fan.id and fan.id != 'DEFAULT_DEVICEID' else 'default/unknown'}`",
            "",
            "### Unsupported optional registers",
            "",
            unsupported_rows,
            "",
            "### User notes",
            "",
            "- Marketing name / seller link:",
            "- Photos or manual link:",
            "- Installed sensor modules/options:",
        )
    )


def hardware_profile_mismatch_issue_url(fan) -> str:
    """Return a GitHub new-issue URL with detected mismatch details filled in."""
    title = f"Hardware profile mismatch for {fan.unit_type or fan.profile_key}"
    return (
        f"{GITHUB_NEW_ISSUE_URL}?"
        + urlencode({"title": title, "body": hardware_profile_mismatch_issue_body(fan)})
    )

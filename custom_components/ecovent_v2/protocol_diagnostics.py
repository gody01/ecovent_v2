"""Protocol diagnostics surfaced through Home Assistant repairs."""

from __future__ import annotations

from urllib.parse import urlencode

GITHUB_NEW_ISSUE_URL = "https://github.com/gody01/ecovent_v2/issues/new"

_VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS = frozenset(
    {0x003A, 0x003B, 0x003C, 0x003D, 0x003E, 0x003F, 0x0063}
)

_KNOWN_VARIANT_UNSUPPORTED_OPTIONAL_PARAMS = {
    # Blauberg VENTO Expert A50-1 W V.2 firmware 0.4 and VENTO Expert DUO
    # A30-1 S10 W V.2 firmware 0.7 devices explicitly reject these optional
    # preset-speed/filter-timer rows. Keep hiding the generated entities, but do
    # not ask users to file another mismatch report when these are the only
    # unsupported optional rows for the exact unit-type family.
    ("vento", 0x0300): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
    ("vento", 0x0400): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
}


def _format_param_id(param_id: int) -> str:
    return f"0x{param_id:04X}"


def reportable_hardware_profile_mismatch_param_ids(fan) -> frozenset[int]:
    """Return unsupported optional rows that still need a hardware report."""
    unsupported = fan.unsupported_optional_poll_parameter_ids()
    unit_type_id = getattr(fan, "_unit_type_id", None)
    known_variant = _KNOWN_VARIANT_UNSUPPORTED_OPTIONAL_PARAMS.get(
        (fan.profile_key, unit_type_id), frozenset()
    )
    return frozenset(unsupported - known_variant)


def unsupported_optional_poll_parameter_details(
    fan, param_ids: frozenset[int] | None = None
) -> tuple[dict[str, str], ...]:
    """Return public-safe details about hardware-rejected optional poll rows."""
    details = []
    if param_ids is None:
        param_ids = fan.unsupported_optional_poll_parameter_ids()
    for param_id in sorted(param_ids):
        definition = fan.params.get(param_id)
        name = definition[0] if definition is not None else "unknown"
        details.append({"id": _format_param_id(param_id), "name": name})
    return tuple(details)


def unsupported_optional_poll_parameter_summary(
    fan, param_ids: frozenset[int] | None = None
) -> str:
    """Return a compact human-readable unsupported row summary."""
    return ", ".join(
        f"{detail['id']} ({detail['name']})"
        for detail in unsupported_optional_poll_parameter_details(fan, param_ids)
    )


def hardware_profile_mismatch_issue_body(
    fan, param_ids: frozenset[int] | None = None
) -> str:
    """Build a prefilled GitHub issue body for live hardware/profile mismatches."""
    unsupported = unsupported_optional_poll_parameter_details(fan, param_ids)
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
            "This report is for this one EcoVent config entry. If several "
            "devices show the same Repair, please open one report for each "
            "distinct model, firmware, and unsupported-register set. Identical "
            "devices with identical firmware and rejected rows can share one "
            "report; note the device count below.",
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


def hardware_profile_mismatch_issue_url(
    fan, param_ids: frozenset[int] | None = None
) -> str:
    """Return a GitHub new-issue URL with detected mismatch details filled in."""
    unit_type_id = getattr(fan, "_unit_type_id", None)
    unit_type_text = f"0x{unit_type_id:04X}" if unit_type_id is not None else "unknown"
    firmware = fan.firmware or "unknown firmware"
    title = (
        f"Hardware profile mismatch for {fan.unit_type or fan.profile_key} "
        f"{unit_type_text} firmware {firmware}"
    )
    return (
        f"{GITHUB_NEW_ISSUE_URL}?"
        + urlencode(
            {"title": title, "body": hardware_profile_mismatch_issue_body(fan, param_ids)}
        )
    )

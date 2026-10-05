"""Protocol diagnostics surfaced through Home Assistant repairs."""

from __future__ import annotations

from urllib.parse import urlencode

try:
    from .ecoventv2 import __version__ as _ECOVENT_VERSION
except ImportError:
    from ecoventv2 import __version__ as _ECOVENT_VERSION

GITHUB_NEW_ISSUE_URL = "https://github.com/gody01/ecovent_v2/issues/new"


def _report_version() -> str:
    """Return the user-facing EcoVent version without the local-build marker."""
    return _ECOVENT_VERSION.removeprefix("loc_")

_VENTO_EXPERT_SPEED_OPTION_ROWS = frozenset(
    {0x003A, 0x003B, 0x003C, 0x003D, 0x003E, 0x003F}
)
_VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS = _VENTO_EXPERT_SPEED_OPTION_ROWS | {
    0x0063
}
_VENTO_EXPERT_A30_MINI_AIR_UNSUPPORTED_OPTIONAL_ROWS = frozenset(
    {
        0x0016,
        0x002D,
        0x003A,
        0x003B,
        0x003C,
        0x003D,
        0x003E,
        0x003F,
        0x004B,
        0x0063,
        0x00B8,
        0x0305,
    }
)
_FRESHPOINT_160E_STANDARD_UNSUPPORTED_OPTIONAL_ROWS = frozenset(
    {
        0x0011,
        0x001A,
        0x0025,
        0x0027,
        0x0129,
        0x0315,
        0x031F,
        0x0320,
        0x0403,
        0x0404,
        0x0405,
    }
)
_EXTRACT_FAN_SMART_WIFI_UNSUPPORTED_OPTIONAL_ROWS = frozenset({0x000B, 0x0012})

# Issue #109: keep RECOM 4 SR rejections quiet only after its four probes
# positively identify this 0x0100 variant; DF270-shaped devices remain reportable.
_RECOM_4_SR_UNSUPPORTED_OPTIONAL_ROWS = frozenset(
    {0x00B7, 0x00B8, 0x0302, 0x0303, 0x0304, 0x0305, 0x0306}
)
_KNOWN_VARIANT_UNSUPPORTED_OPTIONAL_PARAMS = {
    # Blauberg VENTO Expert A50-1 W V.2 firmware 0.4 and VENTO Expert DUO
    # A30-1 S10 W V.2 firmware 0.7 devices explicitly reject these optional
    # preset-speed/filter-timer rows. Keep hiding the generated entities, but do
    # not ask users to file another mismatch report when these are the only
    # unsupported optional rows for the exact unit-type family.
    # Newer 0x0300 firmware can support the filter timer while still omitting
    # the preset-speed rows; keep that row reportable unless the firmware is a
    # known old variant that rejects the complete set.
    ("vento", 0x0300): _VENTO_EXPERT_SPEED_OPTION_ROWS,
    ("vento", 0x0400): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
}

_KNOWN_VARIANT_FIRMWARE_UNSUPPORTED_OPTIONAL_PARAMS = {
    # TwinFresh Atmo old / VENTO inHome old explicitly reject the same optional
    # preset-speed and filter-timer rows on firmware 1.0 2023-12-03.
    ("vento", 0x1A00, "1.0 2023-12-03"): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
    ("vento", 0x0300, "0.4 2019-12-20"): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
    ("vento", 0x0300, "0.6 2021-05-17"): frozenset({0x0063}),
    ("vento", 0x0300, "0.7 2021-10-04"): _VENTO_EXPERT_SPEED_FILTER_OPTION_ROWS,
    (
        "vento",
        0x0500,
        "0.3 2020-08-26",
    ): _VENTO_EXPERT_A30_MINI_AIR_UNSUPPORTED_OPTIONAL_ROWS,
    (
        "vento",
        0x0500,
        "0.5 2021-10-04",
    ): _VENTO_EXPERT_A30_MINI_AIR_UNSUPPORTED_OPTIONAL_ROWS,
    (
        "breezy",
        0x1100,
        "0.8 2024-03-15",
    ): _FRESHPOINT_160E_STANDARD_UNSUPPORTED_OPTIONAL_ROWS,
    (
        "breezy",
        0x1100,
        "0.12 2025-09-01",
    ): _FRESHPOINT_160E_STANDARD_UNSUPPORTED_OPTIONAL_ROWS,
    (
        "extract_fan",
        0x0600,
        "2.2 2022-06-16",
    ): _EXTRACT_FAN_SMART_WIFI_UNSUPPORTED_OPTIONAL_ROWS,
}


def _format_param_id(param_id: int) -> str:
    return f"0x{param_id:04X}"


def reportable_hardware_profile_mismatch_param_ids(fan) -> frozenset[int]:
    """Return unsupported optional rows that still need a hardware report."""
    unsupported = fan.unsupported_optional_poll_parameter_ids()
    unit_type_id = getattr(fan, "_unit_type_id", None)
    known_variant = _KNOWN_VARIANT_UNSUPPORTED_OPTIONAL_PARAMS.get(
        (fan.profile_key, unit_type_id), frozenset()
    ) | _KNOWN_VARIANT_FIRMWARE_UNSUPPORTED_OPTIONAL_PARAMS.get(
        (fan.profile_key, unit_type_id, fan.firmware), frozenset()
    )
    if (
        fan.profile_key == "vento"
        and unit_type_id == 0x0100
        and fan.supports_capability("temperature_probes")
    ):
        known_variant |= _RECOM_4_SR_UNSUPPORTED_OPTIONAL_ROWS
    return frozenset(unsupported - known_variant)


def hardware_profile_mismatch_state(
    fan,
) -> tuple[str, int | None, str | None, frozenset[int]]:
    """Return the device identity and unsupported rows that define one Repair."""
    return (
        fan.profile_key,
        getattr(fan, "_unit_type_id", None),
        fan.firmware,
        reportable_hardware_profile_mismatch_param_ids(fan),
    )


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
            f"- EcoVent V2 integration version: `{_report_version()}`",
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


def rejected_device_value_details(fan) -> tuple[dict, ...]:
    """Return bounded aggregate rejection reports keyed by (param, reason class)."""
    reports = getattr(fan, "_rejected_value_reports", {}) or {}
    out = []
    for key in sorted(reports, key=lambda k: (k[0], k[1])):
        item = dict(reports[key])
        item["key"] = f"{item['id']}/{item['reason_class']}"
        out.append(item)
    return tuple(out)


def rejected_device_value_issue_body(fan, details=None) -> str:
    """Build a bounded, public-safe issue body for rejected device values."""
    if details is None:
        details = rejected_device_value_details(fan)
    details = tuple(details)
    shown = details[:8]
    rows = []
    for item in shown:
        episodes = []
        for episode in item.get("episodes", ())[:4]:
            prev = episode.get("prev_valid") or "unknown"
            bad = ",".join(episode.get("bad_samples", ())[:5]) or "unknown"
            next_valid = episode.get("next_valid") or "open"
            episodes.append(f"{prev} -> {bad} -> {next_valid}")
        episode_text = "; ".join(episodes) or "none closed"
        rows.append(
            f"- `{item['name']}` `{item['id']}` ({item['reason_class']}: "
            f"{item.get('reason', 'decoder rejected value')[:80]}; "
            f"count {item['count']}; {item['first_seen']}..{item['last_seen']}; "
            f"raw {item['min_raw_hex']}..{item['max_raw_hex']}; "
            f"episodes: {episode_text})"
        )
    omitted = len(details) - len(shown)
    if omitted:
        rows.append(f"- +{omitted} more rejected parameter(s) omitted")
    unit_type_id = getattr(fan, "_unit_type_id", None)
    return "\n".join(
        (
            "### Rejected device values",
            "",
            "EcoVent V2 received values for known parameters that its decoder "
            "rejected. Nothing is sent automatically; submitting this report "
            "requires your action.",
            "",
            f"- Integration profile: `{getattr(fan, 'profile_key', 'unknown')}`",
            f"- Unit type: `{getattr(fan, 'unit_type', None) or 'unknown'}`",
            f"- Unit type id: `{f'0x{unit_type_id:04X}' if unit_type_id is not None else 'unknown'}`",
            f"- Firmware: `{getattr(fan, 'firmware', None) or 'unknown'}`",
            f"- EcoVent V2 integration version: `{_report_version()}`",
            "",
            "### Rejected parameters (up to 8 shown)",
            "",
            *(rows or ["- none detected"]),
        )
    )


def rejected_device_value_issue_url(fan, details=None) -> str:
    """Return a bounded GitHub issue URL containing decoder rejection details."""
    unit_type = getattr(fan, "unit_type", None) or getattr(fan, "profile_key", "unknown")
    title = f"Rejected device values for {unit_type}"
    return f"{GITHUB_NEW_ISSUE_URL}?" + urlencode(
        {"title": title, "body": rejected_device_value_issue_body(fan, details)}
    )



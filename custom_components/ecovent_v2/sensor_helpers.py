"""Helpers for Home Assistant sensor entities."""

from __future__ import annotations

from collections.abc import Sequence


def enum_options_with_value(
    options: Sequence[str] | None,
    native_value: str | None,
) -> list[str] | None:
    """Return enum options that include the current device value.

    EcoVent devices occasionally report newer enum values before the integration knows
    their label. The parser exposes them as stable ``Unknown <name> <value>`` strings;
    HA enum sensors must include that string in ``options`` or entity state writes fail.
    """
    if options is None:
        return None

    result = list(options)
    if native_value is not None and native_value not in result:
        result.append(native_value)
    return result

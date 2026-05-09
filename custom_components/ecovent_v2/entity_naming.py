"""Entity naming helpers for stable EcoVent registry ids."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.util import slugify


_SUFFIX_REPLACEMENTS = (
    ("analogV", "analog_voltage"),
    ("analogv", "analog_voltage"),
    ("treshold", "threshold"),
    ("fan1", "fan_1"),
    ("fan2", "fan_2"),
    ("man_speed", "manual_speed"),
)


def clean_object_id_suffix(value: str) -> str:
    """Return a stable object-id suffix decoupled from UI label wording."""
    suffix = value.removeprefix("_")
    for old, new in _SUFFIX_REPLACEMENTS:
        suffix = suffix.replace(old, new)

    if suffix.endswith("_state"):
        suffix = suffix.removesuffix("_state")

    return slugify(suffix)


def stable_entity_id(platform: Platform, device_name: str, suffix: str) -> str:
    """Build the preferred entity id for one-shot legacy migrations."""
    return f"{platform}.{slugify(device_name)}_{clean_object_id_suffix(suffix)}"


class StableObjectIdMixin:
    """Provide a stable object id while keeping rich friendly names."""

    _ecovent_object_id_suffix: str | None = None

    @property
    def suggested_object_id(self) -> str | None:
        """Return the object id base Home Assistant should use for new entities."""
        if self._ecovent_object_id_suffix:
            fan = getattr(self, "_fan", None)
            device_name = getattr(fan, "name", None)
            if device_name:
                return f"{slugify(device_name)}_{self._ecovent_object_id_suffix}"
            return self._ecovent_object_id_suffix
        return super().suggested_object_id

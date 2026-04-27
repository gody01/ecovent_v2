"""Helpers for EcoVent number entities."""

from __future__ import annotations

import math


def encode_raw_number(value: float, value_bytes: int = 1) -> str:
    """Encode a plain numeric value for a protocol write."""
    intval = int(value)
    if value_bytes > 1:
        return intval.to_bytes(value_bytes, "little").hex()
    return hex(intval).replace("0x", "").zfill(2)


def encode_speed_percent(value: float, speed_percent_scale: str) -> str:
    """Encode a Home Assistant percent value for a speed setpoint row."""
    target = max(0, min(100, int(value)))
    if speed_percent_scale == "percent":
        encoded = target
    else:
        encoded = math.ceil(255 / 100 * target)
    return hex(encoded).replace("0x", "").zfill(2)

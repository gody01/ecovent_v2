"""Create a protocol-specific ventilation device from a config entry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_PASSWORD, CONF_PORT

from .const import (
    CONF_TRANSPORT,
    TRANSPORT_BGCP_UDP,
    TRANSPORT_MODBUS_RTU,
    TRANSPORT_MODBUS_TCP,
)
from .ecoventv2 import Fan


def create_device(data: Mapping[str, Any], *, unique_id: str | None = None):
    """Return the device implementation selected by the config entry."""
    transport = data.get(CONF_TRANSPORT, TRANSPORT_BGCP_UDP)
    if transport == TRANSPORT_BGCP_UDP:
        return Fan(
            data[CONF_IP_ADDRESS],
            data[CONF_PASSWORD],
            "DEFAULT_DEVICEID",
            data[CONF_NAME],
            data.get(CONF_PORT, 4000),
        )

    if transport in {TRANSPORT_MODBUS_TCP, TRANSPORT_MODBUS_RTU}:
        # Keep pymodbus out of the legacy BGCP import path. Home Assistant installs
        # manifest requirements before this factory is called.
        from .a21_modbus import A21ModbusDevice

        return A21ModbusDevice.from_config(data, device_id=unique_id)

    raise ValueError(f"Unsupported EcoVent transport: {transport}")

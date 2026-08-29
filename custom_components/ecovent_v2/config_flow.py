"""Config flow for EcoVent_v2 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    A21_DEVICE_MODELS,
    A21_BAUD_RATES,
    A21_STOP_BITS,
    CONF_AUTO_CLOCK_SYNC,
    CONF_BAUDRATE,
    CONF_DEVICE_MODEL,
    CONF_PARITY,
    CONF_SERIAL_PORT,
    CONF_SILENT_MODE,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    CONF_UNIT_ID,
    DOMAIN,
    SUPPORTED_TRANSPORTS,
    TRANSPORT_BGCP_UDP,
    TRANSPORT_MODBUS_RTU,
    TRANSPORT_MODBUS_TCP,
    UPDATE_INTERVAL,
)
from .device_factory import create_device

_LOGGER = logging.getLogger(__name__)


def _common_schema(defaults: dict[str, Any]) -> dict[Any, Any]:
    """Return fields shared by every transport."""
    return {
        vol.Optional(
            CONF_NAME, default=defaults.get(CONF_NAME, "Vento Expert Fan")
        ): str,
        vol.Optional(UPDATE_INTERVAL, default=defaults.get(UPDATE_INTERVAL, 30)): int,
        vol.Optional(
            # Legacy initial form default=True; reconfigure uses the saved value.
            CONF_AUTO_CLOCK_SYNC,
            default=defaults.get(CONF_AUTO_CLOCK_SYNC, True),
        ): bool,
    }


def _bgcp_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the legacy BGCP-over-UDP form schema."""
    defaults = defaults or {}
    schema = {
        vol.Required(CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, "")): str,
        vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, 4000)): int,
        vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "1111")): str,
        **_common_schema(defaults),
        # Legacy initial form default=False; reconfigure uses the saved value.
        vol.Optional(
            CONF_SILENT_MODE, default=defaults.get(CONF_SILENT_MODE, False)
        ): bool,
    }
    return vol.Schema(schema)


def _modbus_tcp_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the A21 Modbus TCP form schema."""
    defaults = defaults or {}
    schema = {
        vol.Required(CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, "")): str,
        vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, 502)): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, 1)): vol.All(
            int, vol.Range(min=1, max=16)
        ),
        vol.Optional(
            CONF_DEVICE_MODEL,
            default=defaults.get(CONF_DEVICE_MODEL, A21_DEVICE_MODELS[-1]),
        ): vol.In(A21_DEVICE_MODELS),
        **_common_schema(defaults),
    }
    return vol.Schema(schema)


def _modbus_rtu_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the A21 Modbus RTU form schema."""
    defaults = defaults or {}
    schema = {
        vol.Required(CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, "")): str,
        vol.Optional(
            CONF_BAUDRATE, default=defaults.get(CONF_BAUDRATE, 115200)
        ): vol.In(A21_BAUD_RATES),
        vol.Optional(CONF_PARITY, default=defaults.get(CONF_PARITY, "N")): vol.In(
            ("N", "E", "O")
        ),
        vol.Optional(CONF_STOPBITS, default=defaults.get(CONF_STOPBITS, 2)): vol.In(
            A21_STOP_BITS
        ),
        vol.Optional(CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, 1)): vol.All(
            int, vol.Range(min=1, max=16)
        ),
        vol.Optional(
            CONF_DEVICE_MODEL,
            default=defaults.get(CONF_DEVICE_MODEL, A21_DEVICE_MODELS[-1]),
        ): vol.In(A21_DEVICE_MODELS),
        **_common_schema(defaults),
    }
    return vol.Schema(schema)


# Kept for callers/tests that imported the old public schema name.
STEP_USER_DATA_SCHEMA = _bgcp_schema()


def _schema_for_transport(
    transport: str, defaults: dict[str, Any] | None = None
) -> vol.Schema:
    """Return the transport-specific connection schema."""
    if transport == TRANSPORT_BGCP_UDP:
        return _bgcp_schema(defaults)
    if transport == TRANSPORT_MODBUS_TCP:
        return _modbus_tcp_schema(defaults)
    if transport == TRANSPORT_MODBUS_RTU:
        return _modbus_rtu_schema(defaults)
    raise ValueError(f"Unsupported transport: {transport}")


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate a device connection and return its stable identity."""
    config = dict(data)
    config.setdefault(CONF_TRANSPORT, TRANSPORT_BGCP_UDP)
    device = create_device(config)

    try:
        initialized = await hass.async_add_executor_job(device.init_device)
        if not initialized:
            if getattr(device, "identity_probe_failed", False):
                raise UnsupportedDevice
            if config[CONF_TRANSPORT] == TRANSPORT_BGCP_UDP:
                raise InvalidAuth
            raise CannotConnect

        device_id = getattr(device, "id", None)
        if not device_id or device_id == "DEFAULT_DEVICEID":
            if getattr(device, "identity_probe_failed", False):
                raise UnsupportedDevice
            raise InvalidAuth

        if (
            config[CONF_TRANSPORT] == TRANSPORT_BGCP_UDP
            and getattr(device, "current_wifi_ip", None) is None
        ):
            raise InvalidAuth

        title = getattr(device, "name", None) or config[CONF_NAME]
        if config[CONF_TRANSPORT] == TRANSPORT_BGCP_UDP:
            title = f"{title} {device_id}"

        return {
            "title": title,
            "id": device_id,
        }
    except (CannotConnect, InvalidAuth, UnsupportedDevice):
        raise
    except (ConnectionError, OSError) as err:
        raise CannotConnect from err
    finally:
        close = getattr(device, "close", None)
        if close is not None:
            try:
                await hass.async_add_executor_job(close)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Unable to close EcoVent V2 transport after validation: %s",
                    err,
                    exc_info=True,
                )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoVent_v2."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose a transport before collecting its connection data."""
        # Existing automations submit the legacy BGCP fields directly to `user`.
        if user_input is not None and CONF_TRANSPORT not in user_input:
            return await self._async_create_transport_entry(
                TRANSPORT_BGCP_UDP, user_input, "user"
            )

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_TRANSPORT, default=TRANSPORT_BGCP_UDP
                        ): vol.In(SUPPORTED_TRANSPORTS)
                    }
                ),
            )

        transport = user_input[CONF_TRANSPORT]
        if transport == TRANSPORT_BGCP_UDP:
            return await self.async_step_bgcp()
        if transport == TRANSPORT_MODBUS_TCP:
            return await self.async_step_modbus_tcp()
        if transport == TRANSPORT_MODBUS_RTU:
            return await self.async_step_modbus_rtu()
        return self.async_abort(reason="unsupported_transport")

    async def async_step_bgcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a legacy BGCP-over-UDP device."""
        return await self._async_create_transport_entry(
            TRANSPORT_BGCP_UDP, user_input, "bgcp"
        )

    async def async_step_modbus_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a VENTS A21 controller via Modbus TCP."""
        return await self._async_create_transport_entry(
            TRANSPORT_MODBUS_TCP, user_input, "modbus_tcp"
        )

    async def async_step_modbus_rtu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a VENTS A21 controller via Modbus RTU."""
        return await self._async_create_transport_entry(
            TRANSPORT_MODBUS_RTU, user_input, "modbus_rtu"
        )

    async def _async_create_transport_entry(
        self,
        transport: str,
        user_input: dict[str, Any] | None,
        step_id: str,
    ) -> FlowResult:
        """Validate and create an entry for a selected transport."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _schema_for_transport(transport)(dict(user_input))
            data[CONF_TRANSPORT] = transport
            if data[UPDATE_INTERVAL] < 3:
                errors[UPDATE_INTERVAL] = "update_interval_too_low"
            else:
                try:
                    info = await validate_input(self.hass, data)
                    await self.async_set_unique_id(info["id"])
                    self._abort_if_unique_id_configured()
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except UnsupportedDevice:
                    errors["base"] = "unsupported_device"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception during device validation")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(title=info["title"], data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=_schema_for_transport(transport, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Reconfigure a device without changing its transport."""
        entry = self._get_reconfigure_entry()
        transport = entry.data.get(CONF_TRANSPORT, TRANSPORT_BGCP_UDP)
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _schema_for_transport(transport)(dict(user_input))
            data[CONF_TRANSPORT] = transport
            if data[UPDATE_INTERVAL] < 3:
                errors[UPDATE_INTERVAL] = "update_interval_too_low"
            else:
                try:
                    info = await validate_input(self.hass, data)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except UnsupportedDevice:
                    errors["base"] = "unsupported_device"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception during device validation")
                    errors["base"] = "unknown"
                else:
                    if (
                        transport == TRANSPORT_BGCP_UDP
                        and entry.unique_id is not None
                        and info["id"] != entry.unique_id
                    ):
                        return self.async_abort(reason="wrong_device")
                    return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema_for_transport(transport, dict(entry.data)),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate that a device cannot be reached."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate invalid BGCP authentication or identity."""


class UnsupportedDevice(exceptions.HomeAssistantError):
    """Error to indicate a non-A21 controller answered the identity probe."""

"""Config flow for EcoVent_v2 integration."""

from __future__ import annotations

import logging
from typing import Any

from .ecoventv2 import Fan
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

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # vol.Required(CONF_IP_ADDRESS, default="<broadcast>"): str,
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Optional(CONF_PORT, default=4000): int,
        # vol.Optional(CONF_DEVICE_ID, default="DEFAULT_DEVICEID"): str,   nothing useful to enter
        vol.Required(CONF_PASSWORD, default="1111"): str,
        vol.Optional(CONF_NAME, default="Vento Expert Fan"): str,
        vol.Optional(UPDATE_INTERVAL, default=30): int,
    }
)


class VentoHub:
    """Vento Hub Class."""

    def __init__(self, host: str, port: int, fan_id: str, name: str) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.fan_id = fan_id
        self.fan = None
        self.name = name

    async def authenticate(self, hass: HomeAssistant, password: str) -> bool:
        """Authenticate."""
        self.fan = Fan(self.host, password, self.fan_id, self.name, self.port)
        await hass.async_add_executor_job(self.fan.init_device)
        self.fan_id = self.fan.id
        _LOGGER.info(
            "Config Flow: Authenticated fan with name:%s ID: %s", self.name, self.fan_id
        )
        if self.fan_id is not None:
            self.name = self.name + " " + self.fan_id
        return (
            (self.fan.id != "DEFAULT_DEVICEID")
            and (self.fan_id is not None)
            and (self.fan.current_wifi_ip is not None)
        )
        # added check for current wifi IP to avoid unvalid fan id. There is no further check elsewhere to prevent progressing with wrong fan id.


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = VentoHub(
        # data[CONF_IP_ADDRESS], data[CONF_PORT], data[CONF_DEVICE_ID], data[CONF_NAME]
        data[CONF_IP_ADDRESS],
        data[CONF_PORT],
        "DEFAULT_DEVICEID",
        data[CONF_NAME],
    )

    if not await hub.authenticate(hass, data[CONF_PASSWORD]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": hub.name, "id": hub.fan_id}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoVent_v2."""

    VERSION = 1

    def __init__(self):
        """Initialite ConfigFlow."""
        self._fan = Fan(
            "<broadcast>", "1111", "DEFAULT_DEVICEID", "Vento Express", 4000
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            """
            if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                ip = None
                ips = await self.hass.async_add_executor_job(
                    self._fan.search_devices, "0.0.0.0"
                )
                # ips = ["10.94.0.105", "10.94.0.106", "10.94.0.107", "10.94.0.108"]
                unique_ids = []
                _LOGGER.debug("Config Flow: Found IPs: %s", ips)
                for entry in self._async_current_entries(include_ignore=True):
                    unique_ids.append(entry.unique_id)
                for ip in ips:
                    self._fan.host = ip
                    self._fan.id = user_input[CONF_DEVICE_ID]
                    self._fan.password = user_input[CONF_PASSWORD]
                    self._fan.name = user_input[CONF_NAME]
                    self._fan.port = user_input[CONF_PORT]
                    _LOGGER.debug("Config Flow: Initializing fan at IP: %s", ip)
                    await self.hass.async_add_executor_job(self._fan.init_device)
                    if self._fan.id not in unique_ids:
                        user_input[CONF_IP_ADDRESS] = ip
                        break
                if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                    raise CannotConnect
                    """
            if user_input[UPDATE_INTERVAL] < 3:
                errors[UPDATE_INTERVAL] = (
                    "update interval must be at least 3 seconds to prevent overloading the device with requests."
                )
                raise exceptions.HomeAssistantError("update interval too low")

            info = await validate_input(self.hass, user_input)
            await self.async_set_unique_id(info["id"])
            self._abort_if_unique_id_configured()
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfigure step."""
        errors: dict[str, str] = {}

        # _LOGGER.info("Reconfigure called with user input: %s", user_input)
        if user_input is not None:
            try:
                """
                if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                    ip = None
                    ips = await self.hass.async_add_executor_job(
                        self._fan.search_devices, "0.0.0.0"
                    )
                    # ips = ["10.94.0.105", "10.94.0.106", "10.94.0.107", "10.94.0.108"]
                    unique_ids = []
                    for entry in self._async_current_entries(include_ignore=True):
                        unique_ids.append(entry.unique_id)
                    for ip in ips:
                        self._fan.host = ip
                        self._fan.id = user_input[CONF_DEVICE_ID]
                        self._fan.password = user_input[CONF_PASSWORD]
                        self._fan.name = user_input[CONF_NAME]
                        self._fan.port = user_input[CONF_PORT]
                        await self.hass.async_add_executor_job(self._fan.init_device)
                        if self._fan.id not in unique_ids:
                            user_input[CONF_IP_ADDRESS] = ip
                            break
                    if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                        raise CannotConnect
                    """
                if user_input[UPDATE_INTERVAL] < 3:
                    errors[UPDATE_INTERVAL] = (
                        "update interval must be at least 3 seconds to prevent overloading the device with requests."
                    )
                    raise exceptions.HomeAssistantError("update interval too low")

                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data_updates=user_input
                )

        ip_configured = self._get_reconfigure_entry().data.get(
            CONF_IP_ADDRESS, "<broadcast>"
        )
        port_configured = self._get_reconfigure_entry().data.get(CONF_PORT, 4000)
        # devId_configured = self._get_reconfigure_entry().data.get(
        #    CONF_DEVICE_ID, "DEFAULT_DEVICEID"
        # )
        password_configured = self._get_reconfigure_entry().data.get(
            CONF_PASSWORD, "1111"
        )
        name_configured = self._get_reconfigure_entry().data.get(
            CONF_NAME, "Vento Expert Fan"
        )
        update_interval_configured = self._get_reconfigure_entry().data.get(
            UPDATE_INTERVAL, 30
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS, default=ip_configured): str,
                    vol.Optional(CONF_PORT, default=port_configured): int,
                    # vol.Optional(CONF_DEVICE_ID, default=devId_configured): str,
                    vol.Required(CONF_PASSWORD, default=password_configured): str,
                    vol.Optional(CONF_NAME, default=name_configured): str,
                    vol.Optional(
                        UPDATE_INTERVAL, default=update_interval_configured
                    ): int,
                }
            ),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""

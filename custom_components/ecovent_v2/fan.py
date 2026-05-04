"""Support for Blauberg Vento Expert Fans with api v.2."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import (
    DOMAIN,
    SERVICE_FILTER_TIMER_RESET,
    SERVICE_RESET_ALARMS,
    SERVICE_SYNC_DEVICE_CLOCK,
)
from .coordinator import EcoVentCoordinator
from .number_helpers import encode_speed_percent

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_ON_PERCENTAGE = 5
SPEED_RANGE = (1, 3)  # off is not included

DIRECTIONS = ["forward", "reverse"]


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Fan config entry."""
    async_add_entities([VentoExpertFan(hass, config)])

    platform = entity_platform.async_get_current_platform()

    # This will call VentoExpertFan.async_reset_filter_timer()
    platform.async_register_entity_service(
        SERVICE_FILTER_TIMER_RESET, {}, VentoExpertFan.async_reset_filter_timer
    )
    # This will call VentoExpertFana.sync_reset_alarms()
    platform.async_register_entity_service(
        SERVICE_RESET_ALARMS, {}, VentoExpertFan.async_reset_alarms
    )
    platform.async_register_entity_service(
        SERVICE_SYNC_DEVICE_CLOCK, {}, VentoExpertFan.async_sync_device_clock
    )


class VentoExpertFan(CoordinatorEntity, FanEntity):
    """Cento Expert Coordinator Class."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize fan."""

        coordinator: EcoVentCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)

        self._fan = coordinator._fan
        # self._percentage = self._fan.man_speed we use fan object directly otherwise we would miss changes from fan changes via remote or direct control
        self._attr_unique_id = self._fan.id
        self._attr_name = self._fan.name
        self._attr_icon = "mdi:fan"
        self._attr_translation_key = "vent"
        self._attr_extra_state_attributes = {"ipv4_address": self._fan.current_wifi_ip}
        self._attr_supported_features = FanEntityFeature(0)
        if self._fan.fan_preset_modes:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE
        if self._fan.supports_parameter("state"):
            self._attr_supported_features |= (
                FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON
            )
        if self._fan.supports_percentage_control:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        if self._fan.supports_oscillation:
            self._attr_supported_features |= FanEntityFeature.OSCILLATE
        if self._fan.supports_direction:
            self._attr_supported_features |= FanEntityFeature.DIRECTION
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
            model=self._fan.unit_type,
            model_id=f"WIFI IP: {self._fan.current_wifi_ip}, {self._fan.wifi_assigned_ip}",
            sw_version=self._fan.firmware,
            manufacturer="Blauberg",
            configuration_url=f"http://{self._fan.current_wifi_ip}",
        )

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attr_extra_state_attributes

    @property
    def name(self) -> str:
        """Get entity name."""
        return self._fan.name

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._fan.id

    @property
    def is_on(self) -> bool:
        """Return state."""
        return self._fan.state == "on"

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        if self._fan.state == "off":
            return 0
        return self._fan.preset_speed_percent(self._fan.speed)

    @property
    def preset_modes(self) -> list[str]:
        """Return a list of available preset modes."""
        return self._fan.fan_preset_modes

    @property
    def directions(self) -> list[str]:
        """Return a list of available preset modes."""
        if not self._fan.supports_direction:
            return []
        return DIRECTIONS

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        if self._fan.state == "off":
            return "off"
        if (
            self._silent_mode_controls_manual_speed
            and self._fan.speed == "manual"
            and self.coordinator.silent_preset_mode in self.preset_modes
        ):
            return self.coordinator.silent_preset_mode
        return self._fan.speed

    @property
    def _silent_mode_controls_manual_speed(self) -> bool:
        """Return whether silent mode can use this fan's manual speed row."""
        return (
            self.coordinator.silent_mode_enabled
            and self._fan.supports_parameter("speed")
            and self._fan.supports_parameter("man_speed")
        )

    def _set_param_if_changed(self, name: str, target: Any) -> bool:
        """Write a device parameter only when it actually changes."""
        current = getattr(self._fan, name)
        if current == target:
            _LOGGER.debug(
                "Skipping unchanged %s command for %s: %s",
                name,
                self._fan.name,
                target,
            )
            return False

        self._fan.set_param(name, target)
        return True

    def _set_parameters_if_changed(self, targets: dict[str, Any]) -> bool:
        """Write changed device parameters in one packet."""
        changed = {}
        for name, target in targets.items():
            current = getattr(self._fan, name)
            if current == target:
                _LOGGER.debug(
                    "Skipping unchanged %s command for %s: %s",
                    name,
                    self._fan.name,
                    target,
                )
                continue
            changed[name] = target

        if not changed:
            return False

        self._fan.set_parameters(changed)
        return True

    def _set_manual_percentage_if_changed(self, percentage: int) -> bool:
        """Write manual speed percentage only when it actually changes."""
        target_percentage = max(2, percentage)
        if self._fan.man_speed == target_percentage:
            _LOGGER.debug(
                "Skipping unchanged manual speed command for %s: %s%%",
                self._fan.name,
                target_percentage,
            )
            return False

        self._fan.set_man_speed_percent(target_percentage)
        return True

    def _manual_speed_value(self, percentage: int) -> str:
        """Encode a manual speed percentage for a raw protocol batch write."""
        return encode_speed_percent(
            max(2, percentage),
            self._fan.device_profile.speed_percent_scale,
        )

    def _silent_manual_targets(
        self,
        percentage: int | None = None,
        *,
        turn_on: bool = True,
    ) -> dict[str, Any]:
        """Build a manual-mode batch that keeps silent mode changes together."""
        targets = {}
        if turn_on and self._fan.state != "on":
            targets["state"] = "on"
        if self._fan.speed != "manual":
            targets["speed"] = "manual"
        if percentage is not None and self._fan.man_speed != max(2, percentage):
            targets["man_speed"] = self._manual_speed_value(percentage)
        return targets

    def _silent_preset_percentage(self, preset_mode: str) -> int:
        """Map an HA-facing preset to the manual percentage sent to the fan."""
        if preset_mode == "manual":
            return self._fan.man_speed or DEFAULT_ON_PERCENTAGE

        preset_percentage = self._fan.preset_speed_percent(preset_mode)
        if preset_percentage is None:
            return self._fan.man_speed or DEFAULT_ON_PERCENTAGE
        return preset_percentage

    def _set_silent_manual_percentage(
        self,
        percentage: int,
        *,
        turn_on: bool = True,
        preset_mode: str = "manual",
        extra_targets: dict[str, Any] | None = None,
    ) -> bool:
        """Apply one silent-mode control burst while keeping HA preset facade."""
        changed = False
        if turn_on and self._fan.state != "on":
            # This protocol ignores an off -> on transition when it is batched
            # with manual speed writes, so power on first and keep the follow-up
            # batch for speed changes.
            changed = self._set_param_if_changed("state", "on")
            turn_on = False

        targets = self._silent_manual_targets(percentage, turn_on=turn_on)
        if extra_targets:
            targets.update(extra_targets)

        changed = self._set_parameters_if_changed(targets) or changed
        self.coordinator.set_silent_preset_mode(preset_mode)
        return changed

    def set_airflow_mode(self, airflow: str, turn_on: bool = True) -> None:
        """Set airflow mode, optionally turning the fan on first."""
        if self._silent_mode_controls_manual_speed:
            percentage = self._fan.man_speed or DEFAULT_ON_PERCENTAGE
            preset_mode = self.coordinator.silent_preset_mode or "manual"
            self._set_silent_manual_percentage(
                percentage,
                turn_on=turn_on,
                preset_mode=preset_mode,
                extra_targets={"airflow": airflow},
            )
            return

        if turn_on:
            self._set_param_if_changed("state", "on")
        self._set_param_if_changed("airflow", airflow)

    @property
    def current_direction(self) -> str | None:
        """Fan direction."""
        if not self._fan.supports_direction:
            return None
        if self._fan.airflow == "air_supply":
            return "reverse"
        return "forward"

    @property
    def oscillating(self) -> bool:
        """Oscillating."""
        if not self._fan.supports_oscillation:
            return False
        return self._fan.airflow == "heat_recovery"

    @property
    def boost_time(self) -> int:
        """Boost time."""
        return self._fan.boost_time

    @property
    def humidity_treshold(self) -> int:
        """Boost time."""
        return self._fan.humidity_treshold

    @property
    def analogV_treshold(self) -> int:
        """Boost time."""
        return self._fan.analogV_treshold

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the entity."""
        speed = kwargs.get("speed")
        if (
            preset_mode is None
            and isinstance(speed, str)
            and speed in self._fan.fan_preset_modes
        ):
            preset_mode = speed

        if preset_mode is not None:
            await self.hass.async_add_executor_job(
                self.set_preset_mode,
                preset_mode,
                True,
            )
        if percentage is not None:
            await self.hass.async_add_executor_job(
                self.set_percentage,
                percentage,
                True,
            )

        if preset_mode is None and percentage is None:
            if self._silent_mode_controls_manual_speed:
                await self.hass.async_add_executor_job(
                    self._set_silent_manual_percentage,
                    self._silent_preset_percentage(
                        self.coordinator.silent_preset_mode or "manual"
                    ),
                    preset_mode=self.coordinator.silent_preset_mode or "manual",
                )
                await self.coordinator.async_refresh()
                return
            await self.hass.async_add_executor_job(
                self._set_param_if_changed, "state", "on"
            )
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the entity."""
        await self.hass.async_add_executor_job(
            self._set_param_if_changed, "state", "off"
        )
        await self.coordinator.async_refresh()

    def set_preset_mode(self, preset_mode: str, turn_on: bool = True) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == "off":
            self._set_param_if_changed("state", "off")
            self.coordinator.set_silent_preset_mode(None)
            return

        if self._silent_mode_controls_manual_speed:
            if preset_mode not in self.preset_modes:
                raise ValueError(f"Invalid preset mode: {preset_mode}")
            self._set_silent_manual_percentage(
                self._silent_preset_percentage(preset_mode),
                turn_on=turn_on,
                preset_mode=preset_mode,
            )
            return

        if self._fan.uses_operating_mode_presets:
            if turn_on:
                self._set_param_if_changed("state", "on")
            self._fan.set_operating_mode_preset(preset_mode)
            return

        if preset_mode in self.preset_modes:
            state_changed = False
            if turn_on:
                state_changed = self._set_param_if_changed("state", "on")
            speed_changed = self._set_param_if_changed("speed", preset_mode)
            if preset_mode != "manual" and (state_changed or speed_changed):
                self._fan.update_preset_speed_settings()
        else:
            raise ValueError(f"Invalid preset mode: {preset_mode}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self.hass.async_add_executor_job(self.set_preset_mode, preset_mode, True)
        await self.coordinator.async_refresh()

    def set_percentage(self, percentage: int, turn_on: bool = True) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage <= 0:
            self._set_param_if_changed("state", "off")
            return

        if self._fan.uses_operating_mode_presets:
            if turn_on:
                self._set_param_if_changed("state", "on")
            self._fan.set_speed_setpoint_percent(percentage)
            return

        if self._silent_mode_controls_manual_speed:
            self._set_silent_manual_percentage(
                percentage,
                turn_on=turn_on,
                preset_mode="manual",
            )
            return

        if turn_on:
            self._set_param_if_changed("state", "on")

        self._set_param_if_changed("speed", "manual")
        self._set_manual_percentage_if_changed(percentage)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        await self.hass.async_add_executor_job(self.set_percentage, percentage, True)
        await self.coordinator.async_refresh()

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        await self.hass.async_add_executor_job(self.set_direction, direction)
        await self.coordinator.async_refresh()

    def set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if direction == "forward":
            target_airflow = "ventilation"
        elif direction == "reverse":
            target_airflow = "air_supply"
        else:
            raise ValueError(f"Invalid direction: {direction}")

        self.set_airflow_mode(target_airflow, True)

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        await self.hass.async_add_executor_job(self.set_oscillating, oscillating)
        await self.coordinator.async_refresh()
        # self.schedule_update_ha_state()

    def set_oscillating(self, oscillating: bool) -> None:
        """Set oscillation."""
        target_airflow = "heat_recovery" if oscillating else "ventilation"
        self.set_airflow_mode(target_airflow, True)

    ###### Custom services

    # Reset filter timer
    async def async_reset_filter_timer(self, fan_target) -> None:
        """Reset Fan's filter timer."""
        await self.hass.async_add_executor_job(
            self._fan.set_param, "filter_timer_reset", ""
        )
        await self.coordinator.async_refresh()

    # Reset alarms
    async def async_reset_alarms(self, fan_target) -> None:
        """Reset Fan's Alarms."""
        await self.hass.async_add_executor_job(self._fan.set_param, "reset_alarms", "")
        await self.coordinator.async_refresh()

    async def async_sync_device_clock(self, fan_target) -> None:
        """Synchronize the device clock with Home Assistant local time."""
        await self.coordinator.async_sync_device_clock()

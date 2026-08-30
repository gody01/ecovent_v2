"""Support for Blauberg Vento Expert Fans with api v.2."""

from __future__ import annotations

from functools import partial
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
DEFAULT_PRESET_PERCENTAGES = {
    "low": 33,
    "medium": 66,
    "high": 100,
    "speed_1": 20,
    "speed_2": 40,
    "speed_3": 60,
    "speed_4": 80,
    "speed_5": 100,
}
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
        transport = getattr(self._fan, "transport", "bgcp_udp")
        self._attr_extra_state_attributes = {"transport": transport}
        if self._fan.current_wifi_ip is not None:
            self._attr_extra_state_attributes["ipv4_address"] = (
                self._fan.current_wifi_ip
            )
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
            model_id=getattr(
                self._fan,
                "connection_description",
                f"WIFI IP: {self._fan.current_wifi_ip}, {self._fan.wifi_assigned_ip}",
            ),
            sw_version=self._fan.firmware,
            manufacturer=getattr(self._fan, "manufacturer", "Blauberg"),
            configuration_url=getattr(
                self._fan,
                "configuration_url",
                f"http://{self._fan.current_wifi_ip}",
            ),
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
    def is_on(self) -> bool | None:
        """Return state."""
        state = self._fan.state
        return None if state is None else state == "on"

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        state = self._fan.state
        if state is None:
            return None
        if state == "off":
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

        self._set_param(name, target)
        return True

    def _set_param(self, name: str, target: Any) -> None:
        """Write a device parameter and fail the HA command on transport failure."""
        if not self._fan.set_param(name, target):
            raise RuntimeError(
                f"Failed to write {name}={target!r} for {self._fan.name}"
            )

    def _set_parameters_if_changed(
        self,
        targets: dict[str, Any],
        *,
        include_extra_write_parameters: bool = True,
    ) -> bool:
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

        if not self._fan.set_parameters(
            changed,
            include_extra_write_parameters=include_extra_write_parameters,
        ):
            raise RuntimeError(
                f"Failed to write {sorted(changed)} for {self._fan.name}"
            )
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

        if not self._fan.set_man_speed_percent(target_percentage):
            raise RuntimeError(
                "Failed to write manual speed "
                f"{target_percentage}% for {self._fan.name}"
            )
        return True

    def _confirmed_percentage_target(self, percentage: int) -> int:
        """Return the percentage the selected device path can represent."""
        target = int(percentage)
        if target <= 0:
            return 0
        if self._fan.uses_operating_mode_presets:
            return max(30, min(100, target))
        if (
            0 < target < 2
            and not self._silent_mode_controls_manual_speed
            and not self._fan.uses_operating_mode_presets
        ):
            return 2
        return target

    def _manual_speed_value(self, percentage: int) -> str:
        """Encode a manual speed percentage for a raw protocol batch write."""
        return encode_speed_percent(
            percentage,
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
        if percentage is not None:
            target_percentage = max(0, min(100, percentage))
            if self._fan.man_speed != target_percentage:
                targets["man_speed"] = self._manual_speed_value(target_percentage)
        return targets

    def _silent_preset_percentage(self, preset_mode: str) -> int:
        """Map an HA-facing preset to the manual percentage sent to the fan."""
        if preset_mode == "manual":
            if self._fan.man_speed is not None:
                return self._fan.man_speed
            return DEFAULT_ON_PERCENTAGE

        preset_percentage = self._fan.preset_speed_percent(
            preset_mode,
            fallback_to_manual=False,
        )
        if preset_percentage is None:
            fallback_percentage = DEFAULT_PRESET_PERCENTAGES.get(preset_mode)
            if fallback_percentage is not None:
                return fallback_percentage
            if self._fan.man_speed is not None:
                return self._fan.man_speed
            return DEFAULT_ON_PERCENTAGE
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

        entering_manual_mode = self._fan.speed != "manual"
        if targets and not entering_manual_mode and not extra_targets:
            audible_targets = set(targets) - {"man_speed"}
            assert not audible_targets, (
                "steady-state silent manual speed update would emit audible "
                f"writes: {sorted(audible_targets)}"
            )

        audible_writes_before = self._fan.audible_write_command_count
        changed = (
            self._set_parameters_if_changed(
                targets,
                include_extra_write_parameters=entering_manual_mode,
            )
            or changed
        )
        if targets and not entering_manual_mode and not extra_targets:
            assert self._fan.audible_write_command_count == audible_writes_before, (
                "steady-state silent manual speed update emitted an audible write"
            )
        self.coordinator.set_silent_preset_mode(preset_mode)
        return changed

    def _is_preset_mode_unchanged(self, preset_mode: str) -> bool:
        """Return whether a preset service call is a true local no-op."""
        if preset_mode == "off":
            return self._fan.state == "off"

        if self._silent_mode_controls_manual_speed:
            if preset_mode not in self.preset_modes:
                return False

            target_percentage = self._silent_preset_percentage(preset_mode)
            return (
                self._fan.state == "on"
                and self._fan.speed == "manual"
                and self._fan.man_speed == max(0, min(100, target_percentage))
            )

        return preset_mode == self.preset_mode

    def set_airflow_mode(self, airflow: str, turn_on: bool = True) -> None:
        """Set airflow mode, optionally turning the fan on first."""
        if self._silent_mode_controls_manual_speed:
            percentage = (
                self._fan.man_speed
                if self._fan.man_speed is not None
                else DEFAULT_ON_PERCENTAGE
            )
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
        airflow = self._fan.airflow
        if airflow is None:
            return None
        if airflow == "air_supply":
            return "reverse"
        if airflow in ("ventilation", "heat_recovery"):
            return "forward"
        return None

    @property
    def oscillating(self) -> bool | None:
        """Oscillating."""
        if not self._fan.supports_oscillation:
            return False
        airflow = self._fan.airflow
        if airflow not in ("ventilation", "heat_recovery", "air_supply", "extract"):
            return None
        return airflow == "heat_recovery"

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

        if preset_mode is None and percentage is None:
            if self._silent_mode_controls_manual_speed:
                silent_preset = self.coordinator.silent_preset_mode or "manual"
                if self._is_preset_mode_unchanged(silent_preset):
                    self.coordinator.set_silent_preset_mode(silent_preset)
                    self.async_write_ha_state()
                    _LOGGER.debug(
                        "Skipping unchanged turn_on command for %s",
                        self._fan.name,
                    )
                    return
            elif self._fan.state == "on":
                _LOGGER.debug(
                    "Skipping unchanged turn_on command for %s",
                    self._fan.name,
                )
                return

        if preset_mode is not None and percentage is not None:
            raise ValueError("preset_mode and percentage cannot be set together")

        try:
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
                    silent_preset = self.coordinator.silent_preset_mode or "manual"
                    await self.hass.async_add_executor_job(
                        partial(
                            self._set_silent_manual_percentage,
                            self._silent_preset_percentage(silent_preset),
                            preset_mode=silent_preset,
                        ),
                    )
                else:
                    await self.hass.async_add_executor_job(
                        self._set_param_if_changed, "state", "on"
                    )
        finally:
            await self.coordinator.async_refresh_confirmed()

        if preset_mode is not None and self.preset_mode != preset_mode:
            raise RuntimeError(
                f"Device did not confirm preset {preset_mode!r} for {self._fan.name}"
            )
        if (
            percentage is not None
            and self.percentage != self._confirmed_percentage_target(percentage)
        ):
            raise RuntimeError(
                f"Device did not confirm speed {percentage}% for {self._fan.name}"
            )
        if preset_mode is None and percentage is None:
            if self.is_on is not True:
                raise RuntimeError(
                    f"Device did not confirm power on for {self._fan.name}"
                )
            if (
                self._silent_mode_controls_manual_speed
                and self.preset_mode != silent_preset
            ):
                raise RuntimeError(
                    f"Device did not confirm preset {silent_preset!r} "
                    f"for {self._fan.name}"
                )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the entity."""
        if self._fan.state == "off":
            _LOGGER.debug("Skipping unchanged turn_off command for %s", self._fan.name)
            return

        try:
            await self.hass.async_add_executor_job(
                self._set_param_if_changed, "state", "off"
            )
        finally:
            await self.coordinator.async_refresh_confirmed()
        if self.is_on is not False:
            raise RuntimeError(f"Device did not confirm power off for {self._fan.name}")

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
            if not self._fan.set_operating_mode_preset(preset_mode):
                raise RuntimeError(
                    f"Failed to set preset {preset_mode!r} for {self._fan.name}"
                )
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
        if self._is_preset_mode_unchanged(preset_mode):
            if preset_mode == "off":
                self.coordinator.set_silent_preset_mode(None)
            elif self._silent_mode_controls_manual_speed:
                self.coordinator.set_silent_preset_mode(preset_mode)
                self.async_write_ha_state()
            _LOGGER.debug(
                "Skipping unchanged preset command for %s: %s",
                self._fan.name,
                preset_mode,
            )
            return

        try:
            await self.hass.async_add_executor_job(
                self.set_preset_mode, preset_mode, True
            )
        finally:
            await self.coordinator.async_refresh_confirmed()
        if self.preset_mode != preset_mode:
            raise RuntimeError(
                f"Device did not confirm preset {preset_mode!r} for {self._fan.name}"
            )

    def set_percentage(self, percentage: int, turn_on: bool = True) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage <= 0:
            if self._silent_mode_controls_manual_speed:
                self._set_silent_manual_percentage(
                    0,
                    turn_on=turn_on,
                    preset_mode="manual",
                )
                return
            self._set_param_if_changed("state", "off")
            return

        if self._fan.uses_operating_mode_presets:
            if turn_on:
                self._set_param_if_changed("state", "on")
            if not self._fan.set_speed_setpoint_percent(percentage):
                raise RuntimeError(
                    f"Failed to set speed {percentage}% for {self._fan.name}"
                )
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
        if (
            percentage <= 0
            and self._fan.state == "off"
            and not self._silent_mode_controls_manual_speed
        ):
            _LOGGER.debug(
                "Skipping unchanged percentage command for %s: %s%%",
                self._fan.name,
                percentage,
            )
            return

        if (
            not self._fan.uses_operating_mode_presets
            and self._fan.speed == "manual"
            and percentage == self.percentage
            and (percentage > 0 or self._silent_mode_controls_manual_speed)
        ):
            if self._silent_mode_controls_manual_speed:
                self.coordinator.set_silent_preset_mode("manual")
                self.async_write_ha_state()
            _LOGGER.debug(
                "Skipping unchanged percentage command for %s: %s%%",
                self._fan.name,
                percentage,
            )
            return

        try:
            await self.hass.async_add_executor_job(
                self.set_percentage, percentage, True
            )
        finally:
            await self.coordinator.async_refresh_confirmed()
        if self.percentage != self._confirmed_percentage_target(percentage):
            raise RuntimeError(
                f"Device did not confirm speed {percentage}% for {self._fan.name}"
            )

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        try:
            await self.hass.async_add_executor_job(self.set_direction, direction)
        finally:
            await self.coordinator.async_refresh_confirmed()
        if self.current_direction != direction:
            raise RuntimeError(
                f"Device did not confirm direction {direction!r} for {self._fan.name}"
            )

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
        try:
            await self.hass.async_add_executor_job(self.set_oscillating, oscillating)
        finally:
            await self.coordinator.async_refresh_confirmed()
        if self.oscillating is not oscillating:
            raise RuntimeError(
                f"Device did not confirm oscillation={oscillating!r} "
                f"for {self._fan.name}"
            )
        # self.schedule_update_ha_state()

    def set_oscillating(self, oscillating: bool) -> None:
        """Set oscillation."""
        target_airflow = "heat_recovery" if oscillating else "ventilation"
        self.set_airflow_mode(target_airflow, True)

    ###### Custom services

    # Reset filter timer
    async def async_reset_filter_timer(self, _service_call) -> None:
        """Reset Fan's filter timer."""
        try:
            await self.hass.async_add_executor_job(
                self._set_param, "filter_timer_reset", "01"
            )
        finally:
            await self.coordinator.async_refresh_confirmed()

    # Reset alarms
    async def async_reset_alarms(self, _service_call) -> None:
        """Reset Fan's Alarms."""
        try:
            await self.hass.async_add_executor_job(
                self._set_param, "reset_alarms", "01"
            )
        finally:
            await self.coordinator.async_refresh_confirmed()

    async def async_sync_device_clock(self, _service_call) -> None:
        """Synchronize the device clock with Home Assistant local time."""
        await self.coordinator.async_sync_device_clock()

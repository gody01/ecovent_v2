"""EcoVent Fan mixin extracted from the vendored protocol client."""

import logging

try:
    from .schedule_helpers import SCHEDULE_SPEED_ICONS, SCHEDULE_SPEED_TO_OPTION
except ImportError:
    from schedule_helpers import SCHEDULE_SPEED_ICONS, SCHEDULE_SPEED_TO_OPTION


_LOGGER = logging.getLogger(__name__)


class FanCapabilitiesMixin:
    @property
    def device_profile(self):
        """Return the active device profile."""
        return self.device_profiles[self._profile_key]

    @property
    def profile_key(self):
        """Return the active device profile key."""
        return self.device_profile.key

    @property
    def fan_preset_modes(self):
        """Return the Home Assistant preset modes supported by this profile."""
        return list(self.device_profile.preset_modes)

    @property
    def supports_direction(self):
        """Return whether the profile exposes airflow direction control."""
        return self.device_profile.supports_direction

    @property
    def supports_oscillation(self):
        """Return whether the profile exposes heat-recovery oscillation control."""
        return self.device_profile.supports_oscillation

    @property
    def supports_preset_speed_settings(self):
        """Return whether the profile has separate preset speed settings."""
        return self.device_profile.supports_preset_speed_settings

    @property
    def supports_percentage_control(self):
        """Return whether HA may write arbitrary percentage speed commands."""
        return self.device_profile.supports_percentage_control

    @property
    def uses_operating_mode_presets(self):
        """Return whether speed maps to autonomous operating modes."""
        return self.device_profile.uses_operating_mode_presets

    def supports_capability(self, capability):
        """Return whether the active profile declares a named capability."""
        return capability in self.device_profile.capabilities

    def supports_parameter(self, parameter):
        """Return whether the active protocol profile knows a parameter."""
        return self.get_params_index(parameter) is not None

    def supports_entity(
        self,
        *,
        required_params=(),
        required_capabilities=(),
        excluded_params=(),
        excluded_capabilities=(),
    ):
        """Return whether an entity description applies to this profile."""
        return (
            all(self.supports_parameter(param) for param in required_params)
            and all(
                self.supports_capability(capability)
                for capability in required_capabilities
            )
            and not any(self.supports_parameter(param) for param in excluded_params)
            and not any(
                self.supports_capability(capability)
                for capability in excluded_capabilities
            )
        )

    def parameter_options(self, parameter):
        """Return enum options for a supported parameter, if it has any."""
        index = self.get_params_index(parameter)
        if index is None:
            return None

        param = self.params.get(index) or self.write_params.get(index)
        if param[1] is None:
            return None
        return list(param[1].values())

    def available_schedule_speed_options(self):
        """Return schedule speed options that make sense for the active device."""
        speed_modes = self.device_profile.schedule_speed_modes or tuple(
            preset for preset in self.fan_preset_modes if preset not in {"off", "manual"}
        )
        options = [
            SCHEDULE_SPEED_TO_OPTION[mode]
            for mode in speed_modes
            if mode in SCHEDULE_SPEED_TO_OPTION
        ]
        return options or ["Standby", "Low", "Medium", "High"]

    def available_schedule_speed_option_meta(self):
        """Return schedule speed options with icons for the custom editor."""
        speed_modes = self.device_profile.schedule_speed_modes or tuple(
            preset for preset in self.fan_preset_modes if preset not in {"off", "manual"}
        )
        items = []
        for mode in speed_modes:
            option = SCHEDULE_SPEED_TO_OPTION.get(mode)
            if option is None:
                continue
            items.append(
                {
                    "value": option,
                    "label": option,
                    "icon": SCHEDULE_SPEED_ICONS.get(mode, "mdi:fan"),
                }
            )
        return items or [
            {"value": "Standby", "label": "Standby", "icon": "mdi:power-sleep"},
            {"value": "Low", "label": "Low", "icon": "mdi:fan-speed-1"},
            {"value": "Medium", "label": "Medium", "icon": "mdi:fan-speed-2"},
            {"value": "High", "label": "High", "icon": "mdi:fan-speed-3"},
        ]

    def _profile_enum(self, enum_name):
        """Return a profile-specific enum map by class attribute name."""
        return getattr(type(self), enum_name)

    def _decode_uint(self, input, byteorder="little"):
        """Decode unsigned protocol integers from hex payload bytes."""
        return int.from_bytes(bytes.fromhex(input), byteorder=byteorder, signed=False)

    def _decode_signed_temperature(self, input):
        """Decode Breezy/Freshpoint signed tenths-of-degree temperature values."""
        value = int.from_bytes(bytes.fromhex(input), byteorder="little", signed=True)
        if value in (-32768, 32767):
            return None
        return round(value / 10, 1)

    def _decode_time_minutes_hours(self, input):
        """Decode two-byte minute/hour protocol time into HH:MM text."""
        value = bytes.fromhex(input)
        if len(value) < 2:
            return None
        return f"{value[1]:02d}:{value[0]:02d}"

    def _set_device_profile(self, profile_key):
        """Apply protocol maps for the selected device family."""
        profile = self.device_profiles[profile_key]
        previous_profile = getattr(self, "_profile_key", None)
        if previous_profile != profile_key:
            _LOGGER.info("EcoVentV2: using %s parameter profile", profile_key)

        self._profile_key = profile_key
        self.params = getattr(type(self), profile.params_name).copy()
        self.write_params = getattr(type(self), profile.write_params_name).copy()
        self._write_only_params = set(self.write_params)
        if previous_profile != profile_key:
            self._bulk_read_supported = None

    def _apply_device_profile(self):
        """Select parameter meanings after reading the model id."""
        model = self.device_models.get(self._unit_type_id)
        profile_key = model.profile_key if model is not None else "vento"
        self._set_device_profile(profile_key)

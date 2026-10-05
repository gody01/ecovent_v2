"""EcoVent Fan mixin extracted from the vendored protocol client."""

import logging
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)


_FIXED_VALUE_SIZES = {
    "air_quality": 2,
    "air_quality_treshold": 2,
    "analogV": 1,
    "analogV_treshold": 1,
    "boost_time": 1,
    "co2": 2,
    "co2_treshold": 2,
    "exhaust_speed_4": 1,
    "exhaust_speed_5": 1,
    "exhaust_speed_high": 1,
    "exhaust_speed_low": 1,
    "exhaust_speed_medium": 1,
    "humidity": 1,
    "humidity_treshold": 1,
    "interval_ventilation_speed_setpoint": 1,
    "man_speed": 1,
    "max_speed_setpoint": 1,
    "recovery_efficiency": 1,
    "screen_brightness": 1,
    "silent_speed_setpoint": 1,
    "supply_speed_4": 1,
    "supply_speed_5": 1,
    "supply_speed_high": 1,
    "supply_speed_low": 1,
    "supply_speed_medium": 1,
    "temperature": 1,
    "temperature_treshold": 1,
    "turn_on_delay_timer": 1,
    "voc": 2,
    "voc_treshold": 2,
}

# Both identities can reset cached controls; decode them before ordinary rows.
_PROFILE_SELECTING_PARAM_IDS = frozenset({0x0086, 0x00B9})


class FanProtocolParseMixin:
    def parse_response(self, data, *, allow_any_device_id=False, store=True):
        """Parse one response, optionally staging rows for transaction correlation.

        Direct callers keep the historic eager-store behaviour. Command
        transactions pass ``store=False`` so they can first correlate a
        response to their request and only then commit accepted rows.
        """
        self._last_response_param_ids = None
        self._last_raw_response_param_ids = None
        self._last_response_param_values = None
        self._last_unsupported_param_ids = None
        self._last_response_device_id = None
        self._last_parsed_responses = None
        if not self.validate_packet(data):
            return False
        pointer = 2  # discard frame marker
        length = len(data) - 2
        if len(data) < pointer + 2:
            return False
        packet_type = data[pointer]
        pointer += 1
        if packet_type != int(self._type, 16):
            return False
        id_size = data[pointer]
        pointer += 1
        if id_size != 0x10:
            return False
        if len(data) < pointer + id_size + 3:
            return False
        response_device_id = bytes(data[pointer : pointer + id_size]).decode(
            "latin-1"
        )
        expected_device_id = getattr(self, "_id", None)
        if (
            not allow_any_device_id
            and expected_device_id not in (None, "DEFAULT_DEVICEID")
            and response_device_id != expected_device_id
        ):
            return False
        pointer += id_size
        pwd_size = data[pointer]
        pointer += 1
        if pwd_size > 0x08:
            return False
        if len(data) < pointer + pwd_size + 3:
            return False
        pointer += pwd_size
        function = data[pointer]
        pointer += 1
        if function != int(self.func["resp"], 16):
            return False
        # from here parsing of parameters begin
        payload = data[pointer:length]
        response = bytearray()
        ext_function = 0
        value_counter = 1
        high_byte_value = 0
        parameter = 1
        response_param_ids = set()
        unsupported_param_ids = set()
        parsed_responses = []
        for p in payload:
            if parameter and ext_function == 2 and p >= 0xFC:
                return False
            marker_ready = parameter and ext_function in (0, 1)
            if marker_ready and p == 0xFC:
                return False
            if marker_ready and p == 0xFF:
                ext_function = 0xFF
                # print ( "def ext:" + hex(0xff) )
            elif marker_ready and p == 0xFE:
                ext_function = 0xFE
                # print ( "def ext:" + hex(0xfe) )
            elif marker_ready and p == 0xFD:
                ext_function = 0xFD
                # print ( "dev ext:" + hex(0xfd) )
            else:
                if ext_function == 0xFF:
                    high_byte_value = p
                    ext_function = 1
                elif ext_function == 0xFE:
                    if p <= 1:
                        return False
                    value_counter = p
                    ext_function = 2
                elif ext_function == 0xFD:
                    if p >= 0xFC:
                        return False
                    unsupported_param_id = (high_byte_value << 8) | p
                    if (
                        unsupported_param_id in response_param_ids
                        or unsupported_param_id in unsupported_param_ids
                    ):
                        return False
                    unsupported_param_ids.add(unsupported_param_id)
                    ext_function = 0
                    response = bytearray()
                else:
                    if parameter == 1:
                        # print ("appending: " + hex(high_byte_value))
                        response.append(high_byte_value)
                        parameter = 0
                        ext_function = 0
                    else:
                        value_counter -= 1
                    response.append(p)

            if value_counter <= 0:
                parameter = 1
                value_counter = 1
                ext_function = 0
                if len(response) < 2:
                    return False
                response_param_id = int(response[:2].hex(), 16)
                if (
                    response_param_id in response_param_ids
                    or response_param_id in unsupported_param_ids
                ):
                    return False
                response_param_ids.add(response_param_id)
                parsed_responses.append(bytes(response))
                response = bytearray()
        valid = (
            ext_function == 0 and parameter == 1 and value_counter == 1 and not response
        )
        if valid:
            self._last_response_param_values = {
                int.from_bytes(parsed_response[:2], byteorder="big"): parsed_response[2:]
                for parsed_response in parsed_responses
            }
            self._last_raw_response_param_ids = response_param_ids
            self._last_unsupported_param_ids = unsupported_param_ids
            self._last_response_device_id = response_device_id
            self._last_parsed_responses = tuple(parsed_responses)
            if store:
                self._store_staged_response_params(response_param_ids)
            else:
                self._last_response_param_ids = set()
        return valid

    def _store_staged_response_params(self, param_ids, *, record_unknown=True):
        """Commit selected staged rows and return the successfully decoded ids."""
        decoded_param_ids = set()
        selected_responses = [
            response
            for response in self._last_parsed_responses or ()
            if int.from_bytes(response[:2], byteorder="big") in param_ids
        ]
        profile_responses = [
            response
            for response in self._last_parsed_responses or ()
            if int.from_bytes(response[:2], byteorder="big")
            in _PROFILE_SELECTING_PARAM_IDS
        ]
        selected_responses.sort(
            key=lambda response: int.from_bytes(response[:2], byteorder="big")
            not in _PROFILE_SELECTING_PARAM_IDS
        )
        selected_profile_responses = [
            response
            for response in selected_responses
            if int.from_bytes(response[:2], byteorder="big")
            in _PROFILE_SELECTING_PARAM_IDS
        ]
        before = None
        if profile_responses:
            before = self.__dict__.copy()
            before["_unknown_params"] = self._unknown_params.copy()
            decoded_profile_ids = set()
            for response in profile_responses:
                param_id = int.from_bytes(response[:2], byteorder="big")
                if self._store_param(response, record_unknown=record_unknown):
                    decoded_profile_ids.add(param_id)
            profile_ids = {
                int.from_bytes(response[:2], byteorder="big")
                for response in profile_responses
            }
            if decoded_profile_ids != profile_ids:
                malformed_profile_values = {
                    int.from_bytes(response[:2], byteorder="big"): response[2:].hex()
                    for response in profile_responses
                }
                self.__dict__.clear()
                self.__dict__.update(before)
                if record_unknown:
                    self._unknown_params.update(malformed_profile_values)
                self._last_response_param_ids = set()
                return set()
            if not selected_profile_responses:
                self.__dict__.clear()
                self.__dict__.update(before)
            else:
                decoded_param_ids.update(decoded_profile_ids)
        for response in selected_responses:
            param_id = int.from_bytes(response[:2], byteorder="big")
            if param_id in _PROFILE_SELECTING_PARAM_IDS:
                continue
            if self._store_param(response, record_unknown=record_unknown):
                decoded_param_ids.add(param_id)
        self._last_response_param_ids = decoded_param_ids
        return decoded_param_ids

    def _store_staged_response_params_atomic(self, param_ids):
        """Commit every selected row or restore the pre-decode device state."""
        param_ids = set(param_ids)
        before = self.__dict__.copy()
        before["_unknown_params"] = self._unknown_params.copy()
        decoded_param_ids = self._store_staged_response_params(
            param_ids, record_unknown=False
        )
        if decoded_param_ids == param_ids:
            return decoded_param_ids

        self.__dict__.clear()
        self.__dict__.update(before)
        self._last_response_param_ids = set()
        return set()

    def _parameter_values_are_decodable(self, parameter_values):
        """Validate outbound values through the same setters used for replies."""
        before = self.__dict__.copy()
        before["_unknown_params"] = self._unknown_params.copy()
        try:
            for param_id, value in parameter_values.items():
                if param_id in self._write_only_params:
                    continue
                response = param_id.to_bytes(2, byteorder="big") + value
                if not self._store_param(response, record_unknown=False):
                    return False
            return True
        finally:
            self.__dict__.clear()
            self.__dict__.update(before)

    def _store_param(self, response, *, record_unknown=True):
        param_id = int(response[:2].hex(), 16)
        value = response[2:].hex()
        if param_id not in self.params:
            if record_unknown:
                self._unknown_params[param_id] = value
            return False
        definition = self.params[param_id]
        parameter = definition[0]
        expected_size = _FIXED_VALUE_SIZES.get(parameter)
        if definition[1] is not None and parameter != "unit_type":
            expected_size = 1
        reason = None
        if expected_size is not None and len(response) != expected_size + 2:
            reason = f"unexpected width {len(response) - 2}, expected {expected_size}"
        else:
            try:
                setattr(self, parameter, value)
            except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as err:
                reason = str(err) or type(err).__name__
        if reason is not None:
            if record_unknown:
                # Legacy store keeps raw hex so existing callers/tests are unaffected.
                self._unknown_params[param_id] = value
                self._record_rejected_param(param_id, parameter, value, reason)
            return False
        self._unknown_params.pop(param_id, None)
        self._close_rejection_episode(param_id, value)
        try:
            current = getattr(self, parameter, None)
        except AttributeError:
            current = None
        self._last_valid_param_values[param_id] = value if current is None else str(current)
        return True

    @staticmethod
    def _rejection_reason_class(reason):
        low = reason.lower()
        if "unexpected width" in low:
            return "unexpected_width"
        if "outside" in low:
            return "out_of_range"
        return reason.split(":")[0].strip().lower()[:60] or "rejected"

    def _record_rejected_param(self, param_id, parameter, raw_hex, reason):
        """Aggregate oscillating bad values under one (param, reason-class) key."""
        reason_class = self._rejection_reason_class(reason)
        key = (param_id, reason_class)
        poll_seen = getattr(self, "_rejected_value_poll_seen", None)
        if poll_seen is not None:
            poll_key = (key, raw_hex)
            if poll_key in poll_seen:
                return
            poll_seen.add(poll_key)
        try:
            raw_int = int(raw_hex, 16) if raw_hex else 0
        except ValueError:
            raw_int = 0
        now = datetime.now(timezone.utc).isoformat()
        reports = self._rejected_value_reports
        report = reports.get(key)
        if report is None:
            try:
                from .ecoventv2 import __version__
            except ImportError:
                from ecoventv2 import __version__
            report = reports[key] = {
                "id": f"0x{param_id:04X}",
                "name": parameter,
                "reason_class": reason_class,
                "reason": reason[:160],
                "count": 0,
                "first_seen": now,
                "last_seen": now,
                "min_raw_hex": raw_hex,
                "max_raw_hex": raw_hex,
                "min_raw_int": raw_int,
                "max_raw_int": raw_int,
                "raw_samples": [],
                "episodes": [],
                "integration_version": __version__.removeprefix("loc_"),
            }
        report["count"] += 1
        report["last_seen"] = now
        if raw_int < report["min_raw_int"]:
            report["min_raw_int"] = raw_int
            report["min_raw_hex"] = raw_hex
        if raw_int > report["max_raw_int"]:
            report["max_raw_int"] = raw_int
            report["max_raw_hex"] = raw_hex
        if raw_hex not in report["raw_samples"]:
            if len(report["raw_samples"]) < 5:
                report["raw_samples"].append(raw_hex)
        # One episode runs from the first bad value until the next valid one;
        # consecutive bad polls extend the open episode instead of opening one.
        open_ep = self._open_rejection_episodes.get(key)
        if open_ep is None:
            open_ep = self._open_rejection_episodes[key] = {
                "prev_valid": self._last_valid_param_values.get(param_id),
                "bad_samples": [],
                "next_valid": None,
                "started": now,
                "ended": None,
            }
        if raw_hex not in open_ep["bad_samples"]:
            if len(open_ep["bad_samples"]) < 5:
                open_ep["bad_samples"].append(raw_hex)
        if key not in self._logged_rejection_keys:
            self._logged_rejection_keys.add(key)
            _LOGGER.warning(
                "Rejected EcoVent device value: model=%s profile=%s unit_type=%s "
                "firmware=%s param_id=0x%04X param_name=%s raw_hex=%s reason=%s",
                getattr(self, "name", "unknown"),
                getattr(self, "profile_key", "unknown"),
                getattr(self, "unit_type", None) or "unknown",
                getattr(self, "firmware", None) or "unknown",
                param_id,
                parameter,
                raw_hex,
                reason,
            )
        else:
            _LOGGER.debug(
                "Rejected EcoVent value again 0x%04X (%s) count=%d",
                param_id,
                reason_class,
                report["count"],
            )

    def _close_rejection_episode(self, param_id, valid_value):
        """Close open episodes on next valid value; keep first 3 plus latest 1."""
        for key in [k for k in self._open_rejection_episodes if k[0] == param_id]:
            open_ep = self._open_rejection_episodes.pop(key)
            try:
                current = getattr(self, self.params[param_id][0], None)
            except (AttributeError, KeyError):
                current = None
            open_ep["next_valid"] = str(current) if current is not None else valid_value
            open_ep["ended"] = datetime.now(timezone.utc).isoformat()
            report = self._rejected_value_reports.get(key)
            if report is None:
                continue
            report["episodes"].append(open_ep)
            if len(report["episodes"]) > 4:
                report["episodes"] = report["episodes"][:3] + report["episodes"][-1:]


    def _map_value(self, mapping, value, label):
        mapped_value = mapping.get(value)
        if mapped_value is None:
            return f"Unknown {label} {value}"
        return mapped_value

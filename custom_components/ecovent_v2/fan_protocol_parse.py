"""EcoVent Fan mixin extracted from the vendored protocol client."""


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

_PROFILE_SELECTING_PARAM_IDS = frozenset({0x00B9})


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
        if expected_size is not None and len(response) != expected_size + 2:
            if record_unknown:
                self._unknown_params[param_id] = value
            return False
        try:
            setattr(self, parameter, value)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            if record_unknown:
                self._unknown_params[param_id] = value
            return False
        self._unknown_params.pop(param_id, None)
        return True

    def _map_value(self, mapping, value, label):
        mapped_value = mapping.get(value)
        if mapped_value is None:
            return f"Unknown {label} {value}"
        return mapped_value

"""EcoVent Fan mixin extracted from the vendored protocol client."""

class FanProtocolParseMixin:
    def parse_response(self, data, *, allow_any_device_id=False):
        self._last_response_param_ids = None
        self._last_raw_response_param_ids = None
        self._last_response_param_values = None
        self._last_unsupported_param_ids = None
        self._last_response_device_id = None
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
            decoded_param_ids = set()
            for parsed_response in parsed_responses:
                if self._store_param(parsed_response):
                    decoded_param_ids.add(
                        int.from_bytes(parsed_response[:2], byteorder="big")
                    )
            self._last_raw_response_param_ids = response_param_ids
            self._last_response_param_ids = decoded_param_ids
            self._last_unsupported_param_ids = unsupported_param_ids
            self._last_response_device_id = response_device_id
        return valid

    def _store_param(self, response):
        param_id = int(response[:2].hex(), 16)
        value = response[2:].hex()
        if param_id not in self.params:
            self._unknown_params[param_id] = value
            return False
        try:
            setattr(self, self.params[param_id][0], value)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            self._unknown_params[param_id] = value
            return False
        return True

    def _map_value(self, mapping, value, label):
        mapped_value = mapping.get(value)
        if mapped_value is None:
            return f"Unknown {label} {value}"
        return mapped_value

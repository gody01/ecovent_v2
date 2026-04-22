"""EcoVent Fan mixin extracted from the vendored protocol client."""

class FanProtocolParseMixin:
    def parse_response(self, data):
        if not self.validate_packet(data):
            return False
        pointer = 2  # discard frame marker
        length = len(data) - 2
        if len(data) < pointer + 2:
            return False
        pointer += 1  # packet type
        id_size = data[pointer]
        pointer += 1
        if len(data) < pointer + id_size + 3:
            return False
        pointer += id_size
        pwd_size = data[pointer]
        pointer += 1
        if len(data) < pointer + pwd_size + 3:
            return False
        pointer += pwd_size
        # function = data[pointer]  not used
        pointer += 1
        # from here parsing of parameters begin
        payload = data[pointer:length]
        response = bytearray()
        ext_function = 0
        value_counter = 1
        high_byte_value = 0
        parameter = 1
        for p in payload:
            if parameter and p == 0xFF:
                ext_function = 0xFF
                # print ( "def ext:" + hex(0xff) )
            elif parameter and p == 0xFE:
                ext_function = 0xFE
                # print ( "def ext:" + hex(0xfe) )
            elif parameter and p == 0xFD:
                ext_function = 0xFD
                # print ( "dev ext:" + hex(0xfd) )
            else:
                if ext_function == 0xFF:
                    high_byte_value = p
                    ext_function = 1
                elif ext_function == 0xFE:
                    value_counter = p
                    ext_function = 2
                elif ext_function == 0xFD:
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
                high_byte_value = 0
                ext_function = 0
                if len(response) < 2:
                    return False
                self._store_param(response)
                response = bytearray()
        return (
            ext_function == 0 and parameter == 1 and value_counter == 1 and not response
        )

    def _store_param(self, response):
        param_id = int(response[:2].hex(), 16)
        value = response[2:].hex()
        if param_id not in self.params:
            self._unknown_params[param_id] = value
            return
        try:
            setattr(self, self.params[param_id][0], value)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            self._unknown_params[param_id] = value

    def _map_value(self, mapping, value, label):
        mapped_value = mapping.get(value)
        if mapped_value is None:
            return f"Unknown {label} {value}"
        return mapped_value

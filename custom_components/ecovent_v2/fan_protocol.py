"""EcoVent Fan mixin extracted from the vendored protocol client."""

from datetime import datetime
import logging
import socket

try:
    from .schedule_helpers import WeeklyScheduleRecord
except ImportError:
    from schedule_helpers import WeeklyScheduleRecord


_LOGGER = logging.getLogger(__name__)


class FanProtocolMixin:
    def search_devices(self, addr="0.0.0.0", port=4000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((addr, port))
            sock.settimeout(0.5)
            ips = []
            target_host = self._host or "<broadcast>"
            target_port = self._port or port
            payload = bytes.fromhex(
                self.build_packet(
                    self.func["read"] + self.encode_params("007c"),
                    fan_id="DEFAULT_DEVICEID",
                )
            )
            i = 10
            while i > 1:
                i = i - 1
                self._device_search = self._id
                try:
                    sock.sendto(payload, (target_host, target_port))
                    data, addr = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                if (
                    self.parse_response(data)
                    and self._device_search != "DEFAULT_DEVICEID"
                ):
                    ips.append(addr[0])
                    ips = list(set(ips))
            return ips
        finally:
            sock.close()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.settimeout(0.4)
        self._socket_connected = False
        while not self._socket_connected:
            try:
                self.socket.connect((self._host, self._port))
                return self.socket
            except OSError:
                self.socket.close()
                return None

    def str2hex(self, str_msg):
        return "".join("{:02x}".format(ord(c)) for c in str_msg)

    def hex2str(self, hex_msg):
        return "".join(
            chr(int("0x" + hex_msg[i : (i + 2)], 16)) for i in range(0, len(hex_msg), 2)
        )

    def hexstr2tuple(self, hex_msg):
        return [int(hex_msg[i : (i + 2)], 16) for i in range(0, len(hex_msg), 2)]

    def chksum(self, hex_msg):
        checksum = sum(self.hexstr2tuple(hex_msg)) & 0xFFFF
        return f"{checksum & 0xFF:02x}{checksum >> 8:02x}"

    def get_size(self, str):
        return hex(len(str)).replace("0x", "").zfill(2)

    def get_header(self, fan_id=None, password=None, packet_type=None):
        fan_id = self._id if fan_id is None else fan_id
        password = self._password if password is None else password
        packet_type = self._type if packet_type is None else packet_type
        id_size = self.get_size(fan_id)
        pwd_size = self.get_size(password)
        id = self.str2hex(fan_id)
        password = self.str2hex(password)
        str = f"{packet_type}{id_size}{id}{pwd_size}{password}"
        return str

    def build_packet(self, data, fan_id=None, password=None, packet_type=None):
        payload = (
            self.get_header(fan_id=fan_id, password=password, packet_type=packet_type)
            + data
        )
        return self.HEADER + payload + self.chksum(payload)

    def validate_packet(self, data):
        if not isinstance(data, (bytes, bytearray)):
            return False
        if len(data) < 24:
            return False
        if bytes(data[:2]) != self.HEADER_BYTES:
            return False
        checksum = int.from_bytes(data[-2:], byteorder="little", signed=False)
        payload_sum = sum(data[2:-2]) & 0xFFFF
        return checksum == payload_sum

    def get_params_index(self, value):
        for params in (self.params, self.write_params):
            for i in params:
                if params[i][0] == value:
                    return i

    def get_params_values(self, idx, value):
        # print ( "EcoventV2: " + idx,  file = sys.stderr )
        index = self.get_params_index(idx)
        if index is not None:
            param = self.params.get(index) or self.write_params.get(index)
            if param[1] is not None:
                for i in param[1]:
                    if param[1][i] == value:
                        return [index, i]
            return [index, None]
        else:
            return [None, None]

    def encode_params(self, param, value=""):
        parameter = ""
        for i in range(0, len(param), 4):
            n_out = ""
            out = param[i : (i + 4)]
            if out == "0077" and value == "":
                value = "0101"
            if value != "":
                val_bytes = int(len(value) / 2)
            else:
                val_bytes = 0
            if out[:2] != "00":
                n_out = "ff" + out[:2]
            if val_bytes > 1:
                n_out += "fe" + hex(val_bytes).replace("0x", "").zfill(2) + out[2:4]
            else:
                n_out += out[2:4]
            parameter += n_out + value
            if out == "0077":
                value = ""
        return parameter

    def send(self, data):
        # print ( "EcoventV2: " + data , file = sys.stderr )
        try:
            self.socket = self.connect()
            if self.socket is None:
                return None
            payload = self.build_packet(data)
            response = self.socket.sendall(bytes.fromhex(payload))
        except socket.timeout:
            # print ( "EcoventV2: Connection timeout send to device: " + self._host , file = sys.stderr )
            return None
        except (
            OSError
        ):  # this shall include all connection errors like Aborted, Refused and Reset
            return None
        except TypeError:
            return (
                None  # this can happen if the socket connection fails and returns None
            )
        else:
            return response

    def receive(self):
        try:
            if self.socket is None:
                return False
            response = self.socket.recv(1024)
        except socket.timeout:
            # print ( "EcoventV2: Connection timeout receive from device: " + self._host , file = sys.stderr )
            return False
        except OSError:
            return False
        else:
            return response
        finally:
            if self.socket is not None:
                self.socket.close()

    def send_command(
        self,
        command,
        param,
        value="",
        retries=10,
        include_extra_write_parameters=True,
    ):
        _LOGGER.debug(
            "Executing command %s with param %s and value %s",
            command,
            param,
            value,
        )
        return self.send_encoded_command(
            command,
            self.encode_params(param, value),
            retries=retries,
            include_extra_write_parameters=include_extra_write_parameters,
        )

    def send_encoded_command(
        self,
        command,
        encoded_params,
        retries=10,
        include_extra_write_parameters=True,
    ):
        """Execute a protocol command with an already encoded parameter payload."""
        if include_extra_write_parameters:
            encoded_params += self._extra_write_parameters(command, encoded_params)

        data = command + encoded_params
        response = False
        i = 0
        while not response:
            i = i + 1
            self.send(data)
            response = self.receive()
            if response:
                if self.parse_response(response):
                    return True
                response = False
            if i >= retries:
                # print ("EcoventV2: Timeout device: " + self._host + " bail out after " + str(i) + " retries" , file = sys.stderr )
                return False

    def update(self):
        request = ""
        for param, definition in self.params.items():
            if param in self._write_only_params:
                continue
            if definition[0] == "weekly_schedule_setup":
                continue
            request += hex(param).replace("0x", "").zfill(4)
        success = self._read_params(request)
        return success

    def quick_update(self):
        # just update following states ...
        # 0x0006: ["boost_status", statuses],
        # 0x000B: ["timer_counter", None],
        # 0x002D: ["analogV", None],
        # 0x0032: ["relay_status", statuses],
        # 0x0044: ["man_speed", None],
        # 0x004A: ["fan1_speed", None],
        # 0x004B: ["fan2_speed", None],
        # 0x0304: ["humidity_status", statuses],
        # 0x0305: ["analogV_status", statuses],
        return self._read_params(self.device_profile.quick_update_request)

    def update_preset_speed_settings(self):
        if not self.supports_preset_speed_settings:
            return True

        request = "003A003B003C003D003E003F"
        return self._read_params(request)

    def _read_params(self, request):
        if self._bulk_read_supported is not False and self.send_command(
            self.func["read"], request, retries=3
        ):
            self._bulk_read_supported = True
            return True

        self._bulk_read_supported = False
        success = False
        for i in range(0, len(request), 4):
            success = (
                self.send_command(self.func["read"], request[i : i + 4], retries=1)
                or success
            )
        return success

    def set_param(self, param, value):
        valpar = self.get_params_values(param, value)
        # print ( "EcoventV2: " + " " + param + "/" + value , file = sys.stderr )
        if valpar[0] is not None:
            if valpar[1] is not None:
                return self.send_command(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    hex(valpar[1]).replace("0x", "").zfill(2),
                )
            else:
                return self.send_command(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    value,
                )
        return False

    def _encode_parameter_values(self, values):
        """Encode profile-mapped parameter values for one command payload."""
        request = ""
        for param, value in values.items():
            valpar = self.get_params_values(param, value)
            if valpar[0] is None:
                continue

            if valpar[1] is not None:
                value = hex(valpar[1]).replace("0x", "").zfill(2)
            else:
                value = str(value)
            request += self.encode_params(
                hex(valpar[0]).replace("0x", "").zfill(4),
                value,
            )
        return request

    def set_parameters(self, values, include_extra_write_parameters=True):
        """Write several profile-mapped parameters in one encoded command."""
        request = self._encode_parameter_values(values)

        if request:
            return self.send_encoded_command(
                self.func["write_return"],
                request,
                include_extra_write_parameters=include_extra_write_parameters,
            )
        return False

    set_params = set_parameters

    def _extra_write_parameters(self, command, encoded_params):
        """Return encoded opportunistic parameters for write commands."""
        if command != self.func["write_return"] or not encoded_params:
            return ""

        callback = getattr(self, "extra_write_parameters_callback", None)
        if callback is None:
            return ""

        return self._encode_parameter_values(callback())

    def get_param(self, param):
        idx = self.get_params_index(param)
        if idx is not None:
            #  _LOGGER.debug(f"Getting parameter {param} with index {idx}")
            return self.send_command(
                self.func["read"], hex(idx).replace("0x", "").zfill(4)
            )
        return False

    def read_weekly_schedule_record(self, day, period):
        """Read one weekly schedule period via the special 0x0077 request."""
        if not self.supports_parameter("weekly_schedule_setup"):
            return None

        if day < 1 or day > 7 or period < 1 or period > 4:
            raise ValueError(
                f"Invalid weekly schedule slot: day={day}, period={period}"
            )

        self._weekly_schedule_setup_record = None
        request_value = bytes([day, period]).hex()
        if not self.send_command(self.func["read"], "0077", request_value):
            return None
        return self._weekly_schedule_setup_record

    def read_weekly_schedule_day(self, day):
        """Read all four schedule periods for a day."""
        records = {}
        for period in range(1, 5):
            record = self.read_weekly_schedule_record(day, period)
            if record is not None:
                records[period] = record
        return records

    def write_weekly_schedule_record(self, record):
        """Write one weekly schedule period via 0x0077."""
        if not isinstance(record, WeeklyScheduleRecord):
            raise TypeError("record must be a WeeklyScheduleRecord")
        return self.send_command(
            self.func["write_return"], "0077", record.to_hex_payload()
        )

    def set_rtc_datetime(self, value: datetime):
        """Write the device RTC using local calendar/time rows."""
        if not (
            self.supports_parameter("rtc_time") and self.supports_parameter("rtc_date")
        ):
            return False

        return self.set_parameters(
            self.rtc_datetime_params(value),
            include_extra_write_parameters=False,
        )

    def rtc_datetime_params(self, value: datetime):
        """Return RTC write rows for the device's local calendar/time format."""
        return {
            "rtc_time": bytes([value.second, value.minute, value.hour]).hex(),
            "rtc_date": bytes(
                [value.day, value.isoweekday(), value.month, value.year % 100]
            ).hex(),
        }

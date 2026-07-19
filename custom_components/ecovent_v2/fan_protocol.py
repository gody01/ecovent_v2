"""EcoVent Fan mixin extracted from the vendored protocol client."""

from datetime import datetime
import logging
import socket

try:
    from .schedule_helpers import WeeklyScheduleRecord
except ImportError:
    from schedule_helpers import WeeklyScheduleRecord


_LOGGER = logging.getLogger(__name__)
MAX_BULK_READ_PARAMS = 12
OPTIONAL_PARAM_RETRY_BACKOFF_READS = 10
PRESERVE_ON_SOFT_MISS_PARAMS = frozenset(
    {
        0x007C,  # device_search
        0x0086,  # firmware
        0x009C,  # wifi_assigned_ip
        0x00A3,  # current_wifi_ip
        0x00B9,  # unit_type/profile identity
    }
)


def _format_param_ids(param_ids):
    """Return protocol parameter ids in the format users see in docs/logs."""
    if not param_ids:
        return "none"
    return ", ".join(f"0x{param_id:04X}" for param_id in sorted(param_ids))


def _request_param_ids(request):
    """Return parameter ids encoded in a read request string."""
    return {int(request[i : i + 4], 16) for i in range(0, len(request), 4)}


class FanProtocolMixin:
    @property
    def last_missing_required_params(self):
        """Return required parameters missing from the last protocol read."""
        return getattr(self, "_last_missing_required_params", frozenset())

    @property
    def last_missing_optional_params(self):
        """Return optional parameters missing from the last protocol read."""
        return getattr(self, "_last_missing_optional_params", frozenset())

    @property
    def last_unsupported_params(self):
        """Return parameters explicitly rejected by the last protocol read."""
        return getattr(self, "_last_unsupported_params", frozenset())

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

        if self._write_may_be_audible(command, encoded_params):
            self.audible_write_command_count += 1

        data = command + encoded_params
        response = False
        i = 0
        while not response:
            i = i + 1
            self._last_response_param_ids = None
            self._last_unsupported_param_ids = None
            self.send(data)
            response = self.receive()
            if response:
                if self.parse_response(response):
                    return True
                response = False
            if i >= retries:
                # print ("EcoventV2: Timeout device: " + self._host + " bail out after " + str(i) + " retries" , file = sys.stderr )
                return False

    def _write_may_be_audible(self, command, encoded_params):
        """Return whether a write is expected to make the device acknowledge.

        Read commands do not beep, and the only known quiet write is a single
        manual-speed register update (0x0044). Everything else is counted so
        silent-mode tests can assert that no audible command leaked in.
        """
        if command != self.func["write_return"] or not encoded_params:
            return False

        return not self._is_manual_speed_only_write(encoded_params)

    def _is_manual_speed_only_write(self, encoded_params):
        """Return whether encoded params contain exactly one 0x0044 write."""
        return len(encoded_params) == 4 and encoded_params[:2].lower() == "44"

    def _protocol_context(self):
        """Return non-secret device context for protocol diagnostics."""
        return (
            "name=%s host=%s profile=%s unit_type=%s unit_type_id=%s device_id=%s"
            % (
                self.name,
                self.host,
                self.device_profile.key,
                self.unit_type,
                f"0x{self._unit_type_id:04X}" if self._unit_type_id is not None else "unknown",
                "known" if self.id and self.id != "DEFAULT_DEVICEID" else "default",
            )
        )

    def update(self):
        request = ""
        for param, definition in self.params.items():
            if param in self._write_only_params:
                continue
            if definition[0] == "weekly_schedule_setup":
                continue
            request += hex(param).replace("0x", "").zfill(4)
        success = self._read_params(
            request,
            required_params=self.device_profile.poll_required_params,
            read_name="full poll",
        )
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
        return self._read_params(
            self.device_profile.quick_update_request,
            required_params=self.device_profile.poll_required_params,
            read_name="quick poll",
        )

    def update_preset_speed_settings(self):
        if not self.supports_preset_speed_settings:
            return True

        request = "003A003B003C003D003E003F"
        return self._read_params(request, read_name="preset speed settings")

    def _mark_param_unavailable(self, param_id):
        """Clear a missing soft-poll value so Home Assistant does not keep stale data."""
        if param_id in PRESERVE_ON_SOFT_MISS_PARAMS:
            return

        definition = self.params.get(param_id)
        if definition is None:
            return

        setattr(self, f"_{definition[0]}", None)

    def _optional_param_backoff(self):
        backoff = getattr(self, "_optional_read_backoff", None)
        if backoff is None:
            backoff = {}
            self._optional_read_backoff = backoff
        return backoff

    def _mark_param_available_for_retry(self, param_id):
        self._optional_param_backoff().pop(param_id, None)

    def _delay_optional_param_retry(self, param_id):
        self._optional_param_backoff()[param_id] = OPTIONAL_PARAM_RETRY_BACKOFF_READS

    def _optional_param_retry_delayed(self, param_id):
        backoff = self._optional_param_backoff()
        remaining = backoff.get(param_id, 0)
        if remaining <= 0:
            return False

        remaining -= 1
        if remaining:
            backoff[param_id] = remaining
        else:
            backoff.pop(param_id, None)
        return True

    def _read_params(self, request, *, required_params=None, read_name="custom read"):
        """Read parameters without trusting a valid but incomplete bulk reply.

        The Smart Home protocol limits a packet to 256 bytes. Keep each request
        bounded, then retry only parameters omitted from an otherwise valid
        response. An explicit 0xFD unsupported-parameter marker proves the
        device answered, but it is still treated as unavailable data: required
        rows fail the read, while optional rows are cleared and backed off.
        Poll callers may identify the parameters that prove the device itself
        is healthy; missing non-critical probes are retried and logged but do
        not make the whole device unavailable.
        """
        requested_params = _request_param_ids(request)
        if required_params is None:
            required_param_ids = requested_params
        else:
            required_param_ids = requested_params & set(required_params)
        complete = bool(request)
        received_response = False
        missing_required_params = set()
        missing_optional_params = set()
        unsupported_params = set()
        received_params = set()
        bulk_gap_params = set()
        individual_retry_params = set()
        no_response_params = set()
        untracked_response_chunks = 0
        self._last_missing_required_params = frozenset()
        self._last_missing_optional_params = frozenset()
        self._last_unsupported_params = frozenset()
        chunk_size = MAX_BULK_READ_PARAMS * 4

        def mark_unavailable(param_id, *, delay_optional_retry=False):
            nonlocal complete
            if param_id in required_param_ids:
                complete = False
                missing_required_params.add(param_id)
                return

            missing_optional_params.add(param_id)
            self._mark_param_unavailable(param_id)
            if delay_optional_retry:
                self._delay_optional_param_retry(param_id)

        for start in range(0, len(request), chunk_size):
            chunk = request[start : start + chunk_size]
            missing = [chunk[i : i + 4] for i in range(0, len(chunk), 4)]
            chunk_param_ids = {int(param, 16) for param in missing}

            if self._bulk_read_supported is not False:
                self._last_response_param_ids = None
                self._last_unsupported_param_ids = None
                if self.send_command(self.func["read"], chunk, retries=3):
                    received_response = True
                    self._bulk_read_supported = True
                    response_ids = self._last_response_param_ids
                    unsupported_ids = self._last_unsupported_param_ids
                    if response_ids is None and unsupported_ids is None:
                        untracked_response_chunks += 1
                        continue
                    response_ids = set(response_ids or ()) & chunk_param_ids
                    unsupported_ids = set(unsupported_ids or ()) & chunk_param_ids
                    received_params.update(response_ids)
                    for param_id in response_ids:
                        self._mark_param_available_for_retry(param_id)
                    for param_id in unsupported_ids:
                        unsupported_params.add(param_id)
                        mark_unavailable(param_id, delay_optional_retry=True)
                    missing = [
                        param
                        for param in missing
                        if int(param, 16) not in response_ids | unsupported_ids
                    ]
                    if missing:
                        bulk_gap_params.update(int(param, 16) for param in missing)
                        _LOGGER.debug(
                            "EcoVent %s bulk read returned %d of %d requested "
                            "parameters for %s; missing from bulk response: %s",
                            read_name,
                            len(response_ids),
                            len(chunk) // 4,
                            self._protocol_context(),
                            _format_param_ids(
                                int(param, 16) for param in missing
                            ),
                        )
                    else:
                        continue
                else:
                    self._bulk_read_supported = False

            for param in missing:
                param_id = int(param, 16)
                if (
                    param_id not in required_param_ids
                    and self._optional_param_retry_delayed(param_id)
                ):
                    missing_optional_params.add(param_id)
                    self._mark_param_unavailable(param_id)
                    _LOGGER.debug(
                        "Optional parameter 0x%04X still unavailable; "
                        "skipping individual retry during backoff",
                        param_id,
                    )
                    continue

                self._last_response_param_ids = None
                self._last_unsupported_param_ids = None
                individual_retry_params.add(param_id)
                param_complete = self.send_command(
                    self.func["read"], param, retries=1
                )
                response_ids = self._last_response_param_ids
                unsupported_ids = set(self._last_unsupported_param_ids or ())
                received_response = param_complete or received_response
                if param_complete and param_id in unsupported_ids:
                    unsupported_params.add(param_id)
                    mark_unavailable(param_id, delay_optional_retry=True)
                    continue
                if param_complete and response_ids is not None:
                    param_complete = param_id in response_ids
                if param_complete and response_ids is not None:
                    received_params.update(set(response_ids) & {param_id})
                if param_complete:
                    self._mark_param_available_for_retry(param_id)
                if not param_complete:
                    no_response_params.add(param_id)
                    mark_unavailable(param_id, delay_optional_retry=True)
                    if param_id not in required_param_ids:
                        _LOGGER.debug(
                            "EcoVent optional parameter 0x%04X did not respond "
                            "during %s for %s",
                            param_id,
                            read_name,
                            self._protocol_context(),
                        )
        self._last_missing_required_params = frozenset(missing_required_params)
        self._last_missing_optional_params = frozenset(missing_optional_params)
        self._last_unsupported_params = frozenset(unsupported_params)
        if missing_required_params or missing_optional_params or unsupported_params:
            log_level = logging.WARNING if missing_required_params else logging.DEBUG
            _LOGGER.log(
                log_level,
                "EcoVent %s incomplete for %s; requested parameters: %s; "
                "required availability parameters: %s; received parameters: %s; "
                "missing required parameters: %s; optional unavailable parameters: %s; "
                "unsupported parameters: %s; missing from bulk response: %s; "
                "individual retries attempted: %s; "
                "no-response individual retries: %s; untracked valid bulk chunks: %d; "
                "result: %s",
                read_name,
                self._protocol_context(),
                _format_param_ids(requested_params),
                _format_param_ids(required_param_ids),
                _format_param_ids(received_params),
                _format_param_ids(missing_required_params),
                _format_param_ids(missing_optional_params),
                _format_param_ids(unsupported_params),
                _format_param_ids(bulk_gap_params),
                _format_param_ids(individual_retry_params),
                _format_param_ids(no_response_params),
                untracked_response_chunks,
                "available" if complete and received_response else "unavailable",
            )
        return complete and received_response

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

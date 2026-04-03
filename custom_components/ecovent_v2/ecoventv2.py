"""Version"""

__version__ = "loc_0.9.28"

"""Library to handle communication with Wifi ecofan from TwinFresh / Blauberg"""
import socket
import sys
import time
import math
import logging

_LOGGER = logging.getLogger(__name__)

""""
# currently having entities in HA:
==================================
F       0x0001: ["state", states],
F       0x0002: ["speed", speeds],
B       0x0006: ["boost_status", statuses],
B       0x0007: ["timer_mode", timer_modes],
S       0x000B: ["timer_counter", None],
Sw      0x000F: ["humidity_sensor_state", states],
Sw      0x0014: ["relay_sensor_state", states],
Sw      0x0016: ["analogV_sensor_state", states],
F N     0x0019: ["humidity_treshold", None],
S       0x0024: ["battery_voltage", None],
S       0x0025: ["humidity", None],
S       0x002D: ["analogV", None],
B       0x0032: ["relay_status", statuses],
F       0x0044: ["man_speed", None],
S       0x004A: ["fan1_speed", None],
S       0x004B: ["fan2_speed", None],
S       0x0064: ["filter_timer_countdown", None],
F N     0x0066: ["boost_time", None],
        0x006F: ["rtc_time", None],
        0x0070: ["rtc_date", None],
I       0x007C: ["device_search", None],   # this is actually the fan serial number
        0x007D: ["device_password", None],
S       0x007E: ["machine_hours", None],
        0x0081: ["heater_status", statuses],
B       0x0083: ["alarm_status", alarms],
B       0x0085: ["cloud_server_state", states],
I       0x0086: ["firmware", None],
B       0x0088: ["filter_replacement_status", statuses],
I S     0x00A3: ["current_wifi_ip", None],
F S     0x00B7: ["airflow", airflows],
F N     0x00B8: ["analogV_treshold", None],
I       0x00B9: ["unit_type", unit_types],
        # Write only parameters
FC      0x0065: ["filter_timer_reset", None],  # WRITE ONLY
        0x0072: ["weekly_schedule_state", states],
        0x0077: ["weekly_schedule_setup", None],
FC      0x0080: ["reset_alarms", None],  # WRITE ONLY
        0x0094: ["wifi_operation_mode", wifi_operation_modes],
        # 0x0095: ["wifi_name", None],  # propose not to transfer this data over network
        # 0x0096: ["wifi_pasword", None], # propose not to transfer this data over network
        # 0x0099: ["wifi_enc_type", wifi_enc_types], # propose not to transfer this data over network
        0x009A: ["wifi_freq_channel", None],
        0x009B: ["wifi_dhcp", wifi_dhcps],
I       0x009C: ["wifi_assigned_ip", None],
        0x009D: ["wifi_assigned_netmask", None],
        0x009E: ["wifi_main_gateway", None],
        0x0302: ["night_mode_timer", None],
        0x0303: ["party_mode_timer", None],
B       0x0304: ["humidity_status", statuses],
B       0x0305: ["analogV_status", statuses],
        0x0306: ["beeper", bstatuses]        # beeper seems not to work on V2 eco vents, needs firmware 1.xxx or higher

B used as binary sensor
I used for initialization and discovery
F used for fan properties
FC used for fan commands
N used for number
S used for sensor
Sw used for switch

"""





class Fan(object):
    """Class to communicate with the ecofan"""

    HEADER = f"FDFD"

    func = {
        "read": "01",
        "write": "02",
        "write_return": "03",
        "inc": "04",
        "dec": "05",
        "resp": "06",
    }

    states = {0: "off", 1: "on", 2: "togle"}

    speeds = {0: "standby", 1: "low", 2: "medium", 3: "high", 0xFF: "manual"}

    timer_modes = {0: "off", 1: "night", 2: "party"}

    statuses = {0: "off", 1: "on"}

    bstatuses = {0: "off", 1: "on", 2: "silent"}  # for beeper, values unknown

    boost_statuses = {0: "off", 1: "on", 2: "delay"}

    airflows = {0: "ventilation", 1: "heat_recovery", 2: "air_supply", 3: "something"}

    alarms = {0: "no", 1: "alarm", 2: "warning"}

    days_of_week = {
        0: "all days",
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
        8: "Mon-Fri",
        9: "Sat-Sun",
    }

    filters = {0: "filter replacement not required", 1: "replace filter"}

    unit_types = {
        0x0300: "Vento Expert A50-1/A85-1/A100-1 W V.2",
        0x0400: "Vento Expert Duo A30-1 W V.2",
        0x0500: "Vento Expert A30 W V.2",
        0x0E00: "TwinFresh Style Wifi V.2",
        0x1100: "Vents Breezy 160-E",
        0x1B00: "Vento inHome S11 W",
    }

    wifi_operation_modes = {1: "client", 2: "ap"}

    wifi_enc_types = {48: "Open", 50: "wpa-psk", 51: "wpa2_psk", 52: "wpa_wpa2_psk"}

    wifi_dhcps = {0: "STATIC", 1: "DHCP", 2: "Invert"}

    params = {
        0x0001: ["state", states],
        0x0002: ["speed", speeds],
        0x0006: ["boost_status", statuses],
        0x0007: ["timer_mode", timer_modes],
        0x000B: ["timer_counter", None],
        0x000F: ["humidity_sensor_state", states],
        0x0014: ["relay_sensor_state", states],
        0x0016: ["analogV_sensor_state", states],
        0x0019: ["humidity_treshold", None],
        0x0024: ["battery_voltage", None],
        0x0025: ["humidity", None],
        0x002D: ["analogV", None],
        0x0032: ["relay_status", statuses],
        0x0044: ["man_speed", None],
        0x004A: ["fan1_speed", None],
        0x004B: ["fan2_speed", None],
        0x0064: ["filter_timer_countdown", None],
        0x0066: ["boost_time", None],
     #   0x006F: ["rtc_time", None],  according stats not used in integration
     #   0x0070: ["rtc_date", None],  according stats not used in integration
        0x007C: ["device_search", None],  # this is the fan serial number
     #   0x007D: ["device_password", None],  according stats not used in integration
        0x007E: ["machine_hours", None],
     #   0x0081: ["heater_status", statuses], according stats not used in integration
        0x0083: ["alarm_status", alarms],
        0x0085: ["cloud_server_state", states],
        0x0086: ["firmware", None],
        0x0088: ["filter_replacement_status", statuses],
        0x00A3: ["current_wifi_ip", None],
        0x00B7: ["airflow", airflows],
        0x00B8: ["analogV_treshold", None],
        0x00B9: ["unit_type", unit_types],
        # Write only parameters
        0x0065: ["filter_timer_reset", None],  # WRITE ONLY
     #   0x0072: ["weekly_schedule_state", states], according stats not used in integration
     #   0x0077: ["weekly_schedule_setup", None], according stats not used in integration
        0x0080: ["reset_alarms", None],  # WRITE ONLY
        #        0x0087: [ 'factory_reset', None ],
        #        0x00a0: [ 'wifi_apply_and_quit', None ],
        #        0x00a2: [ 'wifi_discard_and_quit', None ],
      #  0x0094: ["wifi_operation_mode", wifi_operation_modes],  according stats not used in integration
      #  # 0x0095: ["wifi_name", None],  # propose not to transfer this data over network   according stats not used in integration
      #  # 0x0096: ["wifi_pasword", None], # propose not to transfer this data over network  according stats not used in integration
      #  # 0x0099: ["wifi_enc_type", wifi_enc_types], # propose not to transfer this data over network  according stats not used in integration
      #  0x009A: ["wifi_freq_channel", None],  according stats not used in integration
      #  0x009B: ["wifi_dhcp", wifi_dhcps],  according stats not used in integration
        0x009C: ["wifi_assigned_ip", None],
      #  0x009D: ["wifi_assigned_netmask", None],  according stats not used in integration
      #  0x009E: ["wifi_main_gateway", None],  according stats not used in integration
      #  0x0302: ["night_mode_timer", None],  according stats not used in integration
      #  0x0303: ["party_mode_timer", None],  according stats not used in integration
        0x0304: ["humidity_status", statuses],
        0x0305: ["analogV_status", statuses],
      #  0x0306: ["beeper", bstatuses]        # beeper seems not to work on V2 eco vents, needs firmware 1.xxx or higher
         #  beeper according stats not used in integration
    }

    _name = None
    _host = None
    _port = None
    _id = None
    _password = None
    _state = None
    _speed = None
    _boost_status = None
    _heater_status = None
    _timer_mode = None
    _timer_counter = None
    _humidity_sensor_state = None
    _relay_sensor_state = None
    _analogV_sensor_state = None
    _humidity_treshold = None
    _battery_voltage = 0
    _humidity = None
    _analogV = None
    _relay_status = None
    _man_speed = None
    _fan1_speed = None
    _fan2_speed = None
    _filter_timer_countdown = None
    _boost_time = None
    _rtc_time = None
    _rtc_date = None
    _weekly_schedule_state = None
    _weekly_schedule_setup = None
    _device_search = None
    _device_password = None
    _machine_hours = None
    _alarm_status = None
    _cloud_server_state = None
    _firmware = None
    _filter_replacement_status = None
    _wifi_operation_mode = None
    _wifi_name = None
    _wifi_pasword = None
    _wifi_enc_type = None
    _wifi_freq_channel = None
    _wifi_dhcp = None
    _wifi_assigned_ip = None
    _wifi_assigned_netmask = None
    _wifi_main_gateway = None
    _current_wifi_ip = None
    _airflow = None
    _analogV_treshold = None
    _unit_type = None
    _night_mode_timer = None
    _party_mode_timer = None
    _humidity_status = None
    _analogV_status = None
    _beeper = None

    def __init__(
        self,
        host,
        password="1111",
        fan_id="DEFAULT_DEVICEID",
        name="ecofanv2",
        port=4000,
    ):
        self._name = name
        self._host = host
        self._port = port
        self._type = "02"
        self._id = fan_id
        self._pwd_size = 0
        self._password = password

    def init_device(self):
        if self._id == "DEFAULT_DEVICEID":
            self.get_param("device_search")
            self._id = self.device_search
        _LOGGER.debug("EcoventV2: Initialized fan with ID: %s", self._id)
        if not self._id:
            return False
        return self.update()

    def search_devices(self, addr="0.0.0.0", port=4000):
        payload = "FDFD021044454641554c545f44455649434549440431313131017cf805"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((addr, port))
        sock.settimeout(0.5)
        ips = []
        i = 10
        while i > 1:
            i = i - 1
            self._device_search = self._id
            if self._host is None:
                self._host = "<broadcast>"
            if self._port is None:
                self._port = port
            sock.sendto(bytes.fromhex(payload), (self._host, self._port))
            data, addr = sock.recvfrom(1024)
            self.parse_response(data)
            if self._device_search != "DEFAULT_DEVICEID":
                ips.append(addr[0])
                ips = list(set(ips))
            time.sleep(0.2)
        sock.close()
        return ips

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
        checksum = hex(sum(self.hexstr2tuple(hex_msg))).replace("0x", "").zfill(4)
        byte_array = bytearray.fromhex(checksum)
        chksum = hex(byte_array[1]).replace("0x", "").zfill(2) + hex(
            byte_array[0]
        ).replace("0x", "").zfill(2)
        return f"{chksum}"

    def get_size(self, str):
        return hex(len(str)).replace("0x", "").zfill(2)

    def get_header(self):
        id_size = self.get_size(self._id)
        pwd_size = self.get_size(self._password)
        id = self.str2hex(self._id)
        password = self.str2hex(self._password)
        str = f"{self._type}{id_size}{id}{pwd_size}{password}"
        return str

    def get_params_index(self, value):
        for i in self.params:
            if self.params[i][0] == value:
                return i

    def get_params_values(self, idx, value):
        # print ( "EcoventV2: " + idx,  file = sys.stderr )
        index = self.get_params_index(idx)
        if index != None:
            if self.params[index][1] != None:
                for i in self.params[index][1]:
                    if self.params[index][1][i] == value:
                        return [index, i]
            return [index, None]
        else:
            return [None, None]

    def send(self, data):
        # print ( "EcoventV2: " + data , file = sys.stderr )
        try:
            self.socket = self.connect()
            payload = self.get_header() + data
            payload = self.HEADER + payload + self.chksum(payload)
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
            response = self.socket.recv(1024)
        except socket.timeout:
            # print ( "EcoventV2: Connection timeout receive from device: " + self._host , file = sys.stderr )
            return False
        except OSError:
            return False
        else:
            return response
        finally:
            self.socket.close()

    def do_func(self, func, param, value=""):
        out = ""
        parameter = ""
        _LOGGER.debug(f"Executing function {func} with param {param} and value {value}")
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
            # _LOGGER.debug(f"Constructed parameter: {n_out + value}")
        data = func + parameter
        response = False
        i = 0
        while not response:
            i = i + 1
            self.send(data)
            response = self.receive()
            if response:
                self.parse_response(response)
                return True
            if i > 10:
                # print ("EcoventV2: Timeout device: " + self._host + " bail out after " + str(i) + " retries" , file = sys.stderr )
                return False
            time.sleep(
                0.5
            )  # wait for network calm down and prevent receiving old responses

    def update(self):
        request = ""
        for param in self.params:
            request += hex(param).replace("0x", "").zfill(4)
        return self.do_func(self.func["read"], request)

    def quick_update(self):
        request = "00060007000B000F00320016004A004B006403040305"
        # just update following states ...
        # 0x0006: ["boost_status", statuses],
        # 0x0007: ["timer_mode", timer_modes],
        # 0x000B: ["timer_counter", None],
        # 0x000F: ["humidity_sensor_state", states],
        # 0x0032: ["relay_status", statuses],
        # 0x004A: ["fan1_speed", None],
        # 0x004B: ["fan2_speed", None],
        # 0x0064: ["filter_timer_countdown", None],
        # 0x0304: ["humidity_status", statuses],
        # 0x0305: ["analogV_status", statuses],
        return self.do_func(self.func["read"], request)

    def set_param(self, param, value):
        valpar = self.get_params_values(param, value)
        # print ( "EcoventV2: " + " " + param + "/" + value , file = sys.stderr )
        if valpar[0] != None:
            if valpar[1] != None:
                self.do_func(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    hex(valpar[1]).replace("0x", "").zfill(2),
                )
            else:
                self.do_func(
                    self.func["write_return"],
                    hex(valpar[0]).replace("0x", "").zfill(4),
                    value,
                )

    def get_param(self, param):
        idx = self.get_params_index(param)
        if idx != None:
            #  _LOGGER.debug(f"Getting parameter {param} with index {idx}")
            self.do_func(self.func["read"], hex(idx).replace("0x", "").zfill(4))

    def set_state_on(self):
        request = "0001"
        value = "01"
        if self.state == "off":
            self.do_func(self.func["write_return"], request, value)

    def set_state_off(self):
        request = "0001"
        value = "00"
        if self.state == "on":
            self.do_func(self.func["write_return"], request, value)

    def set_speed(self, speed):
        if speed >= 1 and speed <= 3:
            request = "0002"
            value = hex(speed).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    def set_man_speed_percent(self, speed):
        if speed >= 2 and speed <= 100:
            request = "0044"
            value = math.ceil(255 / 100 * speed)
            value = hex(value).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.do_func ( self.func['write_return'], request, value )

    def set_man_speed(self, speed):
        if speed >= 14 and speed <= 255:
            request = "0044"
            value = speed
            value = hex(value).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    #            request = "0002"
    #            value = "ff"
    #            self.do_func ( self.func['write_return'], request, value )

    def set_airflow(self, val):
        if val >= 0 and val <= 2:
            request = "00b7"
            value = hex(val).replace("0x", "").zfill(2)
            self.do_func(self.func["write_return"], request, value)

    def parse_response(self, data):
        pointer = 20  # discard header bytes
        length = len(data) - 2
        pwd_size = data[pointer]
        pointer += 1
        password = data[pointer:pwd_size]
        pointer += pwd_size
        function = data[pointer]
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
                    None
                else:
                    if parameter == 1:
                        # print ("appending: " + hex(high_byte_value))
                        response.append(high_byte_value)
                        parameter = 0
                    else:
                        value_counter -= 1
                    response.append(p)

            if value_counter <= 0:
                parameter = 1
                value_counter = 1
                high_byte_value = 0
                setattr(self, self.params[int(response[:2].hex(), 16)][0], response[2:].hex() )
                # _LOGGER.debug(f"Updated parameter {self.params[int(response[:2].hex(), 16)][0]} with value {response[2:].hex()}")
                response = bytearray()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, ip):
        try:
            socket.inet_aton(ip)
            self._host = ip
        except socket.error:
            sys.exit()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, pwd):
        self._password = pwd

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = self.states[int(val)]

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, input):
        val = int(input, 16)
        self._speed = self.speeds[val]

    @property
    def boost_status(self):
        return self._boost_status

    @boost_status.setter
    def boost_status(self, input):
        val = int(input, 16)
        self._boost_status = self.boost_statuses.get(val, "Unknown %s" % val)

    @property
    def heater_status(self):
        return self._heater_status

    @heater_status.setter
    def heater_status(self, input):
        val = int(input, 16)
        self._heater_status = self.heater_status.get(val, "Unknown %s" % val)

    @property
    def timer_mode(self):
        return self._timer_mode

    @timer_mode.setter
    def timer_mode(self, input):
        val = int(input, 16)
        self._timer_mode = self.timer_modes[val]

    @property
    def timer_counter(self):
        return self._timer_counter

    @timer_counter.setter
    def timer_counter(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._timer_counter = (
            str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "
        )

    @property
    def humidity_sensor_state(self):
        return self._humidity_sensor_state

    @humidity_sensor_state.setter
    def humidity_sensor_state(self, input):
        val = int(input, 16)
        self._humidity_sensor_state = self.states.get(val, "Unknown %s" % val)

    @property
    def relay_sensor_state(self):
        return self._relay_sensor_state

    @relay_sensor_state.setter
    def relay_sensor_state(self, input):
        val = int(input, 16)
        self._relay_sensor_state = self.states.get(val, "Unknown %s" % val)

    @property
    def analogV_sensor_state(self):
        return self._analogV_sensor_state

    @analogV_sensor_state.setter
    def analogV_sensor_state(self, input):
        val = int(input, 16)
        self._analogV_sensor_state = self.states.get(val, "Unknown %s" % val)

    @property
    def humidity_treshold(self):
        return self._humidity_treshold

    @humidity_treshold.setter
    def humidity_treshold(self, input):
        val = int(input, 16)
        self._humidity_treshold = str(val)

    @property
    def battery_voltage(self):
        return self._battery_voltage

    @battery_voltage.setter
    def battery_voltage(self, input):
        val = int.from_bytes(
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._battery_voltage = str(val) + " mV"

    @property
    def humidity(self):
        return self._humidity

    @humidity.setter
    def humidity(self, input):
        val = int(input, 16)
        self._humidity = str(val)

    @property
    def analogV(self):
        return self._analogV

    @analogV.setter
    def analogV(self, input):
        val = int(input, 16)
        self._analogV = str(val)

    @property
    def relay_status(self):
        return self._relay_status

    @relay_status.setter
    def relay_status(self, input):
        val = int(input, 16)
        self._relay_status = self.statuses[val]

    @property
    def man_speed(self):
        return self._man_speed

    @man_speed.setter
    def man_speed(self, input):
        val = int(input, 16)
        if val >= 0 and val <= 255:
            self._man_speed = int(val / 255 * 100)

    @property
    def fan1_speed(self):
        return self._fan1_speed

    @fan1_speed.setter
    def fan1_speed(self, input):
        val = int.from_bytes(
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._fan1_speed = str(val)

    @property
    def fan2_speed(self):
        return self._fan2_speed

    @fan2_speed.setter
    def fan2_speed(self, input):
        val = int.from_bytes(
            int(input, 16).to_bytes(2, "big"), byteorder="little", signed=False
        )
        self._fan2_speed = str(val)

    @property
    def filter_timer_countdown(self):
        return self._filter_timer_countdown

    @filter_timer_countdown.setter
    def filter_timer_countdown(self, input):
        if len(input) == 8:
            input = input[:-2]
        # print ( "EcoventV2: " + input , file = sys.stderr )
        val = int(input, 16).to_bytes(3, "big")
        self._filter_timer_countdown = (
            str(val[2]) + "d " + str(val[1]) + "h " + str(val[0]) + "m "
        )
        # self._filter_timer_countdown = str(int(input[4:6],16)) + "d " + str(int(input[2:4],16)) + "h " +str(int(input[0:2],16)) + "m "

    @property
    def boost_time(self):
        return self._boost_time

    @boost_time.setter
    def boost_time(self, input):
        val = int(input, 16)
        self._boost_time = str(val) + " m"

    @property
    def rtc_time(self):
        return self._rtc_time

    @rtc_time.setter
    def rtc_time(self, input):
        val = int(input, 16).to_bytes(3, "big")
        self._rtc_time = str(val[2]) + "h " + str(val[1]) + "m " + str(val[0]) + "s "

    @property
    def rtc_date(self):
        return self._rtc_date

    @rtc_date.setter
    def rtc_date(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._rtc_date = (
            str(val[1])
            + " 20"
            + str(val[3])
            + "-"
            + str(val[2]).zfill(2)
            + "-"
            + str(val[0]).zfill(2)
        )

    @property
    def weekly_schedule_state(self):
        return self._weekly_schedule_state

    @weekly_schedule_state.setter
    def weekly_schedule_state(self, val):
        self._weekly_schedule_state = self.states[int(val)]

    @property
    def weekly_schedule_setup(self):
        return self._weekly_schedule_setup

    @weekly_schedule_setup.setter
    def weekly_schedule_setup(self, input):
        val = int(input, 16).to_bytes(6, "big")
        self._weekly_schedule_setup = (
            self.days_of_week[val[0]]
            + "/"
            + str(val[1])
            + ": to "
            + str(val[5])
            + "h "
            + str(val[4])
            + "m "
            + self.speeds[val[2]]
        )

    @property
    def device_search(self):
        return self._device_search

    @device_search.setter
    def device_search(self, val):
        self._device_search = self.hex2str(val)

    @property
    def device_password(self):
        return self._device_password

    @device_password.setter
    def device_password(self, val):
        self._device_password = self.hex2str(val)

    @property
    def machine_hours(self):
        return self._machine_hours

    @machine_hours.setter
    def machine_hours(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._machine_hours = (
            str(int.from_bytes(val[2:3], "big"))
            + "d "
            + str(val[1])
            + "h "
            + str(val[0])
            + "m "
        )

    @property
    def alarm_status(self):
        return self._alarm_status

    @alarm_status.setter
    def alarm_status(self, input):
        val = int(input, 16)
        self._alarm_status = self.alarms[val]

    @property
    def cloud_server_state(self):
        return self._cloud_server_state

    @cloud_server_state.setter
    def cloud_server_state(self, input):
        val = int(input, 16)
        self._cloud_server_state = self.states[val]

    @property
    def firmware(self):
        return self._firmware

    @firmware.setter
    def firmware(self, input):
        val = int(input, 16).to_bytes(6, "big")
        self._firmware = (
            str(val[0])
            + "."
            + str(val[1])
            + " "
            + str(int.from_bytes(val[4:6], byteorder="little", signed=False))
            + "-"
            + str(val[3]).zfill(2)
            + "-"
            + str(val[2]).zfill(2)
        )

    @property
    def filter_replacement_status(self):
        return self._filter_replacement_status

    @filter_replacement_status.setter
    def filter_replacement_status(self, input):
        val = int(input, 16)
        self._filter_replacement_status = self.statuses[val]

    @property
    def wifi_operation_mode(self):
        return self._wifi_operation_mode

    @wifi_operation_mode.setter
    def wifi_operation_mode(self, input):
        val = int(input, 16)
        self._wifi_operation_mode = self.wifi_operation_modes[val]

    @property
    def wifi_name(self):
        return self._wifi_name

    @wifi_name.setter
    def wifi_name(self, input):
        self._wifi_name = self.hex2str(input)

    @property
    def wifi_pasword(self):
        return self._wifi_pasword

    @wifi_pasword.setter
    def wifi_pasword(self, input):
        self._wifi_pasword = self.hex2str(input)

    @property
    def wifi_enc_type(self):
        return self._wifi_enc_type

    @wifi_enc_type.setter
    def wifi_enc_type(self, input):
        val = int(input, 16)
        self._wifi_enc_type = self.wifi_enc_types[val]

    @property
    def wifi_freq_channel(self):
        return self._wifi_freq_channel

    @wifi_freq_channel.setter
    def wifi_freq_channel(self, input):
        val = int(input, 16)
        self._wifi_freq_channel = str(val)

    @property
    def wifi_dhcp(self):
        return self._wifi_dhcp

    @wifi_dhcp.setter
    def wifi_dhcp(self, input):
        val = int(input, 16)
        self._wifi_dhcp = self.wifi_dhcps[val]

    @property
    def wifi_assigned_ip(self):
        return self._wifi_assigned_ip

    @wifi_assigned_ip.setter
    def wifi_assigned_ip(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_assigned_ip = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def wifi_assigned_netmask(self):
        return self._wifi_assigned_netmask

    @wifi_assigned_netmask.setter
    def wifi_assigned_netmask(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_assigned_netmask = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def wifi_main_gateway(self):
        return self._wifi_main_gateway

    @wifi_main_gateway.setter
    def wifi_main_gateway(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._wifi_main_gateway = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def current_wifi_ip(self):
        return self._current_wifi_ip

    @current_wifi_ip.setter
    def current_wifi_ip(self, input):
        val = int(input, 16).to_bytes(4, "big")
        self._current_wifi_ip = (
            str(val[0]) + "." + str(val[1]) + "." + str(val[2]) + "." + str(val[3])
        )

    @property
    def airflow(self):
        return self._airflow

    @airflow.setter
    def airflow(self, input):
        val = int(input, 16)
        self._airflow = self.airflows[val]

    @property
    def analogV_treshold(self):
        return self._analogV_treshold

    @analogV_treshold.setter
    def analogV_treshold(self, input):
        val = int(input, 16)
        self._analogV_treshold = str(val)

    @property
    def unit_type(self):
        return self._unit_type

    @unit_type.setter
    def unit_type(self, input):
        val = int(input, 16)
        self._unit_type = self.unit_types.get(val, "Unknown model %s" % val)

    @property
    def night_mode_timer(self):
        return self._night_mode_timer

    @night_mode_timer.setter
    def night_mode_timer(self, input):
        val = int(input, 16).to_bytes(2, "big")
        self._night_mode_timer = (
            str(val[1]).zfill(2) + "h " + str(val[0]).zfill(2) + "m"
        )

    @property
    def party_mode_timer(self):
        return self._party_mode_timer

    @party_mode_timer.setter
    def party_mode_timer(self, input):
        val = int(input, 16).to_bytes(2, "big")
        self._party_mode_timer = (
            str(val[1]).zfill(2) + "h " + str(val[0]).zfill(2) + "m"
        )

    @property
    def humidity_status(self):
        return self._humidity_status

    @humidity_status.setter
    def humidity_status(self, input):
        val = int(input, 16)
        self._humidity_status = self.statuses[val]

    @property
    def analogV_status(self):
        return self._analogV_status

    @analogV_status.setter
    def analogV_status(self, input):
        val = int(input, 16)
        self._analogV_status = self.statuses[val]

    @property
    def beeper(self):
        return self._beeper

    @beeper.setter
    def beeper(self, input):
        val = int(input, 16)
        self._beeper = self.bstatuses.get(val,"Unknown %s" % val)

    def reset_filter_timer(self):
        self.set_param("filter_timer_reset", "")

    def reset_alarms(self):
        self.set_param("reset_alarms", "")

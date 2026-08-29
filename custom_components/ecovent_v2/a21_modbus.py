"""VENTS A21 Modbus TCP/RTU transport and Home Assistant device adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
import logging
import re
from threading import RLock
from types import MappingProxyType
from typing import Any

from .a21_registers import (
    A21_IDENTITY_REGISTER,
    A21_IDENTITY_VALUE,
    Firmware,
    FilterTimer,
    REGISTERS,
    RtcCalendar,
    RtcTime,
    Runtime,
    ScheduleEnd,
    SchedulePeriod,
    Table,
    Timer,
    get_by_address,
    get_register,
)
from .const import (
    A21_BAUD_RATES,
    A21_STOP_BITS,
    CONF_BAUDRATE,
    CONF_DEVICE_MODEL,
    CONF_PARITY,
    CONF_SERIAL_PORT,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    CONF_UNIT_ID,
    TRANSPORT_MODBUS_RTU,
    TRANSPORT_MODBUS_TCP,
)
from .ecoventv2 import Fan
from .protocol_metadata import DeviceProfile
from .schedule_helpers import WeeklyScheduleRecord

_LOGGER = logging.getLogger(__name__)

_A21_PROFILE = DeviceProfile(
    key="a21_modbus",
    params_name="",
    write_params_name="",
    quick_update_request="",
    preset_modes=(
        "off",
        "speed_1",
        "speed_2",
        "speed_3",
        "speed_4",
        "speed_5",
        "manual",
    ),
    boost_statuses_name="statuses",
    humidity_sensor_states_name="states",
    schedule_speed_modes=(
        "standby",
        "speed_1",
        "speed_2",
        "speed_3",
        "speed_4",
        "speed_5",
    ),
    capabilities=frozenset(
        {
            "a21_modbus",
            "battery_voltage",
            "binary_diagnostics",
            "co2",
            "filter_maintenance",
            "five_speed_setpoints",
            "heater",
            "sensor_switches",
            "temperature",
            "temperature_probes",
            "timer_mode",
            "voc",
        }
    ),
    supports_preset_speed_settings=True,
    speed_percent_scale="percent",
)

_TABLE_READ_METHOD = {
    Table.COIL: "read_coils",
    Table.DISCRETE_INPUT: "read_discrete_inputs",
    Table.INPUT_REGISTER: "read_input_registers",
    Table.HOLDING_REGISTER: "read_holding_registers",
}
_TABLE_LENGTH = {
    Table.COIL: 26,
    Table.DISCRETE_INPUT: 72,
    Table.INPUT_REGISTER: 54,
    Table.HOLDING_REGISTER: 183,
}
_SENSITIVE_REGISTER_KEYS = frozenset({"HR_ENGINEER_PWD"})
_REQUIRED_POLL_SLOTS = frozenset(
    {
        (Table.COIL, 0),
        (Table.INPUT_REGISTER, 37),
        (Table.HOLDING_REGISTER, 2),
        (Table.HOLDING_REGISTER, 17),
    }
)
_MAX_ILLEGAL_ADDRESS_SPLITS = 32
_A21_SPEEDS = {
    0: "standby",
    1: "speed_1",
    2: "speed_2",
    3: "speed_3",
    4: "speed_4",
    5: "speed_5",
    0xFF: "manual",
}
_A21_SPEED_VALUES = {value: key for key, value in _A21_SPEEDS.items()}
_A21_TIMER_MODES = {
    0: "standby",
    1: "speed_1",
    2: "speed_2",
    3: "speed_3",
    4: "speed_4",
    5: "speed_5",
}
_A21_TIMER_VALUES = {value: key for key, value in _A21_TIMER_MODES.items()}

# These names are the stable semantic surface already consumed by the HA
# entities. The underlying keys remain available through read_register() and
# write_register(), so this adapter does not hide the rest of the A21 table.
_SEMANTIC_REGISTERS = MappingProxyType(
    {
        "state": "CL_POWER",
        "weekly_schedule_state": "CL_WEEK",
        "boost_status": "CL_Boost_MODE",
        "humidity_sensor_state": "CL_IntRH_CTRL",
        "co2_sensor_state": "CL_IntCO2_CTRL",
        "voc_sensor_state": "CL_IntVOC_CTRL",
        "analogV_sensor_state": "CL_10V_SENSOR_CTRL",
        "filter_timer_reset": "CL_RESET_FILTER_TIMER",
        "reset_alarms": "CL_RESET_ALARM",
        "temperature": "IR_CurSelTEMP",
        "room_temperature": "IR_CurTEMP_ExAirIn",
        "outdoor_temperature": "IR_CurTEMP_SuAirIn",
        "supply_temperature": "IR_CurTEMP_SuAirOut",
        "exhaust_in_temperature": "IR_CurTEMP_ExAirIn",
        "exhaust_out_temperature": "IR_CurTEMP_ExAirOut",
        "battery_voltage": "IR_CurVBAT",
        "humidity": "IR_CurRH_Int",
        "co2": "IR_CurCO2_Int",
        "voc": "IR_CurVOC_Int",
        "fan1_speed": "IR_SuRPM",
        "fan2_speed": "IR_ExRPM",
        "timer_counter": "IR_CurTIMER_TIME",
        "filter_timer_countdown": "IR_CurFILTER_TIMER",
        "machine_hours": "IR_TotalWorkingTime",
        "filter_replacement_status": "IR_StateFILTER",
        "schedule_speed": "IR_CurWeekSpeed",
        "firmware": "IR_VerMAIN_FMW",
        "alarm_status": "IR_ALARM",
        "speed": "HR_SPEED_MODE",
        "supply_speed_low": "HR_SuSPEED1",
        "exhaust_speed_low": "HR_ExSPEED1",
        "supply_speed_medium": "HR_SuSPEED2",
        "exhaust_speed_medium": "HR_ExSPEED2",
        "supply_speed_high": "HR_SuSPEED3",
        "exhaust_speed_high": "HR_ExSPEED3",
        "supply_speed_4": "HR_SuSPEED4",
        "exhaust_speed_4": "HR_ExSPEED4",
        "supply_speed_5": "HR_SuSPEED5",
        "exhaust_speed_5": "HR_ExSPEED5",
        "man_speed": "HR_ManualSPEED",
        "temperature_treshold": "HR_SetTEMP",
        "humidity_treshold": "HR_SetRH",
        "co2_treshold": "HR_SetCO2",
        "voc_treshold": "HR_SetVOC",
        "timer_mode": "HR_TIMER_MODE",
        "filter_timer_setpoint": "HR_SetFILTER_TIMER",
        "rtc_time": "HR_RTC_TIME",
        "rtc_date": "HR_RTC_CALENDAR",
        "weekly_schedule_setup": "HR_SetWEEK_Mo_P1",
        "heater_status": "DI_StatusHEATER",
        "humidity_status": "DI_StatusRH",
    }
)


class A21ModbusError(ConnectionError):
    """Base error raised for an unusable A21 Modbus response."""


class A21IdentityError(A21ModbusError):
    """A Modbus server answered but did not identify as controller A21."""


class A21IllegalAddressError(A21ModbusError):
    """A controller rejected a range because at least one address is absent."""


def _safe_identity(value: str) -> str:
    """Return an identifier containing only stable registry-safe characters."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")


def _as_raw_number(value: Any) -> int:
    """Accept entity numeric writes, including their existing hex encoding."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"numeric A21 value required, got {value!r}")
    if isinstance(value, str):
        return int(value, 16)
    if int(value) != value:
        raise ValueError(f"integer A21 value required, got {value!r}")
    return int(value)


class A21ModbusDevice(Fan):
    """A complete A21 register client with the integration's Fan interface."""

    def __init__(
        self,
        *,
        transport: str,
        endpoint: str,
        name: str,
        model: str,
        unit_id: int = 1,
        port: int = 502,
        baudrate: int = 115200,
        parity: str = "N",
        stopbits: float = 2,
        timeout: float = 3,
        client: Any | None = None,
        device_id: str | None = None,
    ) -> None:
        if transport not in {TRANSPORT_MODBUS_TCP, TRANSPORT_MODBUS_RTU}:
            raise ValueError(f"Unsupported A21 transport: {transport}")
        if not 1 <= int(unit_id) <= 16:
            raise ValueError("A21 Modbus unit id must be 1..16")
        if int(baudrate) not in A21_BAUD_RATES:
            raise ValueError(f"Unsupported A21 baud rate: {baudrate}")
        if float(stopbits) not in A21_STOP_BITS:
            raise ValueError(f"Unsupported A21 stop bits: {stopbits}")

        # Initialize the inherited property surface, but never its BGCP socket.
        super().__init__(endpoint, "", "DEFAULT_DEVICEID", name, port)
        self.transport = transport
        self.endpoint = endpoint
        self.unit_id = int(unit_id)
        self.baudrate = int(baudrate)
        self.parity = str(parity).upper()
        self.stopbits = float(stopbits)
        self.timeout = float(timeout)
        self._client = client
        self._lock = RLock()
        self._raw: dict[tuple[Table, int], int] = {}
        self._decoded: dict[str, Any] = {}
        self._unavailable: set[tuple[Table, int]] = set()
        self.last_poll_complete = False
        self.identity_probe_failed = False
        self.extra_write_parameters_callback = None
        self._unit_type = model
        self._unit_type_id = A21_IDENTITY_VALUE
        self._manufacturer = self._manufacturer_for_model(model)
        self._current_wifi_ip = endpoint if transport == TRANSPORT_MODBUS_TCP else None
        self._wifi_assigned_ip = self._current_wifi_ip
        self.configuration_url = None
        self.connection_description = self._connection_description()
        self._configured_device_id = device_id
        self._id = "DEFAULT_DEVICEID"
        self._initialize_semantic_state()

    @classmethod
    def from_config(
        cls, data: Mapping[str, Any], *, device_id: str | None = None
    ) -> "A21ModbusDevice":
        """Build an A21 client from one config-entry data mapping."""
        transport = str(data[CONF_TRANSPORT])
        endpoint = str(
            data["ip_address"]
            if transport == TRANSPORT_MODBUS_TCP
            else data[CONF_SERIAL_PORT]
        )
        return cls(
            transport=transport,
            endpoint=endpoint,
            port=int(data.get("port", 502)),
            unit_id=int(data.get(CONF_UNIT_ID, 1)),
            baudrate=int(data.get(CONF_BAUDRATE, 115200)),
            parity=str(data.get(CONF_PARITY, "N")),
            stopbits=float(data.get(CONF_STOPBITS, 2)),
            name=str(data.get("name", "VENTS A21")),
            model=str(data.get(CONF_DEVICE_MODEL, "Generic VENTS A21 controller")),
            device_id=device_id,
        )

    @staticmethod
    def _manufacturer_for_model(model: str) -> str:
        if model.upper().startswith("ECONOPRIME"):
            return "ECONOPRIME"
        return "VENTS"

    def _connection_description(self) -> str:
        if self.transport == TRANSPORT_MODBUS_TCP:
            return f"Modbus TCP: {self.endpoint}:{self.port}, unit {self.unit_id}"
        return (
            f"Modbus RTU: {self.endpoint}, {self.baudrate} {self.parity}"
            f"8{self.stopbits:g}, unit {self.unit_id}"
        )

    def _initialize_semantic_state(self) -> None:
        self._clear_semantic_state()
        self._profile_key = "a21_modbus"
        self.audible_write_command_count = 0

    def _clear_semantic_state(self) -> None:
        """Clear HA-facing values before rebuilding them from decoded registers."""
        for semantic in _SEMANTIC_REGISTERS:
            setattr(self, f"_{semantic}", None)
        self._alarm_list = None
        self._firmware = None

    @property
    def device_profile(self) -> DeviceProfile:
        return _A21_PROFILE

    @property
    def manufacturer(self) -> str:
        return self._manufacturer

    @property
    def raw_registers(self) -> Mapping[tuple[Table, int], int]:
        """Return a read-only snapshot of all successfully read raw addresses."""
        return MappingProxyType(dict(self._raw))

    @property
    def decoded_registers(self) -> Mapping[str, Any]:
        """Return a read-only snapshot indexed by the official register keys."""
        return MappingProxyType(dict(self._decoded))

    @property
    def unavailable_addresses(self) -> frozenset[tuple[Table, int]]:
        return frozenset(self._unavailable)

    def supports_capability(self, capability: str) -> bool:
        return capability in self.device_profile.capabilities

    def supports_parameter(self, parameter: str) -> bool:
        return parameter in _SEMANTIC_REGISTERS

    def profile_supports_capability(self, capability: str) -> bool:
        """Return an A21 capability; Modbus support is not learned per poll."""
        return self.supports_capability(capability)

    def profile_supports_parameter(self, parameter: str) -> bool:
        """Return an A21 parameter; Modbus support is not learned per poll."""
        return self.supports_parameter(parameter)

    def parameter_range(self, parameter: str) -> tuple[int, int] | None:
        """Return the A21 limits for a semantic HA number parameter."""
        key = _SEMANTIC_REGISTERS.get(parameter)
        if key is None:
            return None
        spec = get_register(key)
        if spec.minimum is None or spec.maximum is None:
            return None
        # HA NumberEntity cannot express the published disjoint range
        # ``0 or 70..365``. Keep 0 available through the typed API and expose
        # only the continuous timer setpoint interval in the UI.
        if key == "HR_SetFILTER_TIMER":
            return (70, 365)
        return (spec.minimum, spec.maximum)

    def supports_entity(
        self,
        *,
        required_params: Iterable[str] = (),
        required_capabilities: Iterable[str] = (),
        excluded_params: Iterable[str] = (),
        excluded_capabilities: Iterable[str] = (),
    ) -> bool:
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

    def parameter_options(self, parameter: str) -> list[str] | None:
        if parameter == "timer_mode":
            return list(_A21_TIMER_VALUES)
        return None

    def _build_client(self):
        try:
            from pymodbus.client import ModbusSerialClient, ModbusTcpClient
        except ImportError as err:  # pragma: no cover - HA installs requirements
            raise A21ModbusError("pymodbus is not installed") from err

        if self.transport == TRANSPORT_MODBUS_TCP:
            return ModbusTcpClient(
                self.endpoint,
                port=self.port,
                timeout=self.timeout,
                retries=3,
            )
        return ModbusSerialClient(
            port=self.endpoint,
            baudrate=self.baudrate,
            bytesize=8,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=self.timeout,
            retries=3,
        )

    def _ensure_connected(self) -> None:
        if self._client is None:
            self._client = self._build_client()
        if getattr(self._client, "connected", False):
            return
        if not self._client.connect():
            raise A21ModbusError(f"Cannot connect to {self.connection_description}")

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()

    @staticmethod
    def _check_response(response: Any, operation: str) -> Any:
        if response is None:
            raise A21ModbusError(f"A21 Modbus {operation} failed: {response!r}")
        if callable(getattr(response, "isError", None)) and response.isError():
            if getattr(response, "exception_code", None) == 2:
                raise A21IllegalAddressError(
                    f"A21 Modbus {operation} rejected an address: {response!r}"
                )
            raise A21ModbusError(f"A21 Modbus {operation} failed: {response!r}")
        return response

    @staticmethod
    def _invoke(method, *args, **kwargs) -> Any:
        """Call pymodbus while preserving programming errors as programming errors."""
        try:
            return method(*args, **kwargs)
        except (OSError, ConnectionError, TimeoutError) as err:
            raise A21ModbusError(f"A21 Modbus transport failed: {err}") from err
        except Exception as err:
            if err.__class__.__module__.startswith("pymodbus"):
                raise A21ModbusError(f"A21 Modbus transport failed: {err}") from err
            raise

    def read_raw(self, table: Table, address: int, count: int = 1) -> tuple[int, ...]:
        """Read arbitrary published A21 addresses using functions 1/2/3/4."""
        table = Table(table)
        if address < 0 or count < 1 or address + count > _TABLE_LENGTH[table]:
            raise ValueError(f"A21 {table.value} range outside published table")
        with self._lock:
            self._ensure_connected()
            method = getattr(self._client, _TABLE_READ_METHOD[table])
            response = self._check_response(
                self._invoke(method, address, count=count, device_id=self.unit_id),
                f"read {table.value} {address}:{address + count - 1}",
            )
            values = (
                tuple(int(value) for value in response.bits[:count])
                if table in {Table.COIL, Table.DISCRETE_INPUT}
                else tuple(int(value) for value in response.registers[:count])
            )
            if len(values) != count:
                raise A21ModbusError(
                    f"A21 Modbus short {table.value} response: "
                    f"expected {count}, got {len(values)}"
                )
            for offset, value in enumerate(values):
                self._raw[(table, address + offset)] = value
                self._unavailable.discard((table, address + offset))
            return values

    def write_raw(
        self, table: Table, address: int, values: Sequence[int | bool]
    ) -> bool:
        """Write published A21 coils/registers using functions 5/6/15/16."""
        table = Table(table)
        if table not in {Table.COIL, Table.HOLDING_REGISTER}:
            raise PermissionError(f"{table.value} is read-only")
        if not values or address < 0 or address + len(values) > _TABLE_LENGTH[table]:
            raise ValueError(f"A21 {table.value} write outside published table")
        for offset in range(len(values)):
            spec = get_by_address(table, address + offset)
            if not spec.access.writable:
                raise PermissionError(
                    f"{spec.key} at {table.value}/{address + offset} is read-only"
                )

        with self._lock:
            self._ensure_connected()
            if table is Table.COIL:
                if any(value not in {False, True, 0, 1} for value in values):
                    raise ValueError("Modbus coil values must be boolean")
                bool_values = tuple(bool(value) for value in values)
                if len(bool_values) == 1:
                    response = self._invoke(
                        self._client.write_coil,
                        address,
                        bool_values[0],
                        device_id=self.unit_id,
                    )
                else:
                    response = self._invoke(
                        self._client.write_coils,
                        address,
                        list(bool_values),
                        device_id=self.unit_id,
                    )
                cached = tuple(int(value) for value in bool_values)
            else:
                words = tuple(int(value) for value in values)
                if any(value < 0 or value > 0xFFFF for value in words):
                    raise ValueError("Modbus register values must be 0..65535")
                if len(words) == 1:
                    response = self._invoke(
                        self._client.write_register,
                        address,
                        words[0],
                        device_id=self.unit_id,
                    )
                else:
                    response = self._invoke(
                        self._client.write_registers,
                        address,
                        list(words),
                        device_id=self.unit_id,
                    )
                cached = words
            self._check_response(response, f"write {table.value} {address}")
            for offset, value in enumerate(cached):
                self._raw[(table, address + offset)] = value
            return True

    def read_register(self, key: str) -> Any:
        """Read and decode one official A21 register definition."""
        spec = get_register(key)
        if not spec.access.readable:
            raise PermissionError(f"{key} is write-only")
        words = self.read_raw(spec.table, spec.address, spec.word_count)
        value = spec.decode(words)
        self._decoded[key] = value
        self._apply_semantics()
        return value

    def write_register(self, key: str, value: Any) -> bool:
        """Validate and write one official A21 register definition."""
        spec = get_register(key)
        if not spec.access.writable:
            raise PermissionError(f"{key} is read-only")
        if spec.enum is not None and isinstance(value, int) and value not in spec.enum:
            raise ValueError(f"{key} has no documented enum value {value}")
        words = spec.encode(value)
        self.write_raw(spec.table, spec.address, words)
        self._decoded[key] = value
        self._apply_semantics()
        return True

    def _read_resilient(
        self,
        table: Table,
        address: int,
        count: int,
        split_budget: list[int] | None = None,
    ) -> bool:
        if split_budget is None:
            split_budget = [_MAX_ILLEGAL_ADDRESS_SPLITS]
        try:
            self.read_raw(table, address, count)
            return True
        except A21IllegalAddressError:
            if split_budget[0] <= 0:
                raise A21ModbusError(
                    f"A21 {table.value} returned too many illegal-address responses"
                )
            split_budget[0] -= 1
            if count == 1:
                slot = (table, address)
                self._unavailable.add(slot)
                self._raw.pop(slot, None)
                self._decoded.pop(get_by_address(table, address).key, None)
                _LOGGER.debug("A21 address unavailable: %s/%d", table.value, address)
                return False
            left = count // 2
            return self._read_resilient(
                table, address, left, split_budget
            ) & self._read_resilient(table, address + left, count - left, split_budget)

    def _decode_cache(self) -> None:
        for spec in REGISTERS:
            if not spec.access.readable or spec.key in _SENSITIVE_REGISTER_KEYS:
                continue
            slots = [
                (spec.table, spec.address + offset) for offset in range(spec.word_count)
            ]
            if not all(slot in self._raw for slot in slots):
                continue
            try:
                self._decoded[spec.key] = spec.decode(self._raw[slot] for slot in slots)
            except ValueError:
                self._decoded.pop(spec.key, None)
                _LOGGER.debug("Invalid A21 value for %s", spec.key, exc_info=True)
        self._clear_semantic_state()
        self._apply_semantics()

    def read_all_registers(self, *, include_sensitive: bool = False) -> bool:
        """Poll the complete readable published surface.

        Write-only action coils are skipped. The engineering password is only
        read after an explicit opt-in; raw read/write methods still implement
        its documented two-register protocol.
        """
        ranges = (
            (Table.COIL, 0, 17),
            (Table.COIL, 20, 6),
            (Table.DISCRETE_INPUT, 0, 72),
            (Table.INPUT_REGISTER, 0, 54),
            (Table.HOLDING_REGISTER, 0, 124),
            (Table.HOLDING_REGISTER, 126, 57),
        )
        complete = True
        for table, address, count in ranges:
            complete = self._read_resilient(table, address, count) and complete
        if include_sensitive:
            complete = self._read_resilient(Table.HOLDING_REGISTER, 124, 2) and complete
        self._decode_cache()
        self._verify_cached_identity()
        self.last_poll_complete = complete
        return not bool(_REQUIRED_POLL_SLOTS & self._unavailable)

    def _verify_cached_identity(self) -> None:
        identity = self._decoded.get(A21_IDENTITY_REGISTER.key)
        identity_slot = (
            A21_IDENTITY_REGISTER.table,
            A21_IDENTITY_REGISTER.address,
        )
        if identity is None and identity_slot in self._unavailable:
            return
        if identity != A21_IDENTITY_VALUE:
            self.identity_probe_failed = True
            raise A21IdentityError(
                f"Controller identity register 37 is {identity!r}; expected A21 value 1"
            )

    def init_device(self) -> bool:
        """Connect and accept only a controller that reports A21 at IR37."""
        self.identity_probe_failed = False
        try:
            identity = self.read_register(A21_IDENTITY_REGISTER.key)
        except A21ModbusError:
            raise
        if identity != A21_IDENTITY_VALUE:
            self.identity_probe_failed = True
            return False

        endpoint_id = _safe_identity(
            f"{self.transport}-{self.endpoint}-{self.port}-{self.unit_id}"
        )
        self._id = self._configured_device_id or f"a21-{endpoint_id}"
        return self.update()

    def update(self) -> bool:
        """Refresh every non-sensitive readable address in the A21 table."""
        return self.read_all_registers()

    def quick_update(self) -> bool:
        """Refresh the high-frequency operational portion of the table."""
        ranges = (
            (Table.COIL, 0, 17),
            (Table.DISCRETE_INPUT, 0, 19),
            (Table.INPUT_REGISTER, 0, 54),
            (Table.HOLDING_REGISTER, 0, 76),
        )
        complete = True
        for table, address, count in ranges:
            complete = self._read_resilient(table, address, count) and complete
        self._decode_cache()
        self._verify_cached_identity()
        self.last_poll_complete = complete
        return not bool(_REQUIRED_POLL_SLOTS & self._unavailable)

    def update_preset_speed_settings(self) -> bool:
        return self._read_resilient(Table.HOLDING_REGISTER, 5, 13)

    @staticmethod
    def _valid_temperature(value: Any) -> float | None:
        if value in (-3276.8, 3276.7):
            return None
        return value

    def _apply_semantics(self) -> None:
        value = self._decoded.get
        if "CL_POWER" in self._decoded:
            self._state = "on" if value("CL_POWER") else "off"
        if "HR_SPEED_MODE" in self._decoded:
            self._speed = _A21_SPEEDS.get(
                value("HR_SPEED_MODE"), f"unknown_{value('HR_SPEED_MODE')}"
            )
        if "HR_ManualSPEED" in self._decoded:
            self._man_speed = value("HR_ManualSPEED")

        speed_attributes = {
            "_supply_speed_low": "HR_SuSPEED1",
            "_exhaust_speed_low": "HR_ExSPEED1",
            "_supply_speed_medium": "HR_SuSPEED2",
            "_exhaust_speed_medium": "HR_ExSPEED2",
            "_supply_speed_high": "HR_SuSPEED3",
            "_exhaust_speed_high": "HR_ExSPEED3",
            "_supply_speed_4": "HR_SuSPEED4",
            "_exhaust_speed_4": "HR_ExSPEED4",
            "_supply_speed_5": "HR_SuSPEED5",
            "_exhaust_speed_5": "HR_ExSPEED5",
        }
        for attribute, key in speed_attributes.items():
            if key in self._decoded:
                setattr(self, attribute, value(key))

        temperatures = {
            "_temperature": "IR_CurSelTEMP",
            "_room_temperature": "IR_CurTEMP_ExAirIn",
            "_outdoor_temperature": "IR_CurTEMP_SuAirIn",
            "_supply_temperature": "IR_CurTEMP_SuAirOut",
            "_exhaust_in_temperature": "IR_CurTEMP_ExAirIn",
            "_exhaust_out_temperature": "IR_CurTEMP_ExAirOut",
        }
        for attribute, key in temperatures.items():
            if key in self._decoded:
                setattr(self, attribute, self._valid_temperature(value(key)))

        direct = {
            "_humidity": "IR_CurRH_Int",
            "_co2": "IR_CurCO2_Int",
            "_voc": "IR_CurVOC_Int",
            "_fan1_speed": "IR_SuRPM",
            "_fan2_speed": "IR_ExRPM",
            "_humidity_treshold": "HR_SetRH",
            "_temperature_treshold": "HR_SetTEMP",
            "_co2_treshold": "HR_SetCO2",
            "_voc_treshold": "HR_SetVOC",
        }
        for attribute, key in direct.items():
            if key in self._decoded:
                setattr(self, attribute, value(key))

        bool_states = {
            "_weekly_schedule_state": "CL_WEEK",
            "_boost_status": "CL_Boost_MODE",
            "_humidity_sensor_state": "CL_IntRH_CTRL",
            "_co2_sensor_state": "CL_IntCO2_CTRL",
            "_voc_sensor_state": "CL_IntVOC_CTRL",
            "_analogV_sensor_state": "CL_10V_SENSOR_CTRL",
            "_heater_status": "DI_StatusHEATER",
            "_humidity_status": "DI_StatusRH",
        }
        for attribute, key in bool_states.items():
            if key in self._decoded:
                setattr(self, attribute, "on" if value(key) else "off")

        if "IR_CurVBAT" in self._decoded:
            self._battery_voltage = f"{value('IR_CurVBAT')} mV"
        if isinstance(value("IR_CurTIMER_TIME"), Timer):
            timer = value("IR_CurTIMER_TIME")
            self._timer_counter = f"{timer.hours}h {timer.minutes}m {timer.seconds}s "
        if isinstance(value("IR_CurFILTER_TIMER"), FilterTimer):
            timer = value("IR_CurFILTER_TIMER")
            self._filter_timer_countdown = (
                f"{timer.days}d {timer.hours}h {timer.minutes}m "
            )
        if "HR_SetFILTER_TIMER" in self._decoded:
            self._filter_timer_setpoint = f"{value('HR_SetFILTER_TIMER')} d"
        if isinstance(value("IR_TotalWorkingTime"), Runtime):
            runtime = value("IR_TotalWorkingTime")
            self._machine_hours = (
                f"{runtime.days}d {runtime.hours}h {runtime.minutes}m "
            )
        if isinstance(value("IR_VerMAIN_FMW"), Firmware):
            firmware = value("IR_VerMAIN_FMW")
            self._firmware = (
                f"{firmware.major}.{firmware.minor} "
                f"{firmware.year:04d}-{firmware.month:02d}-{firmware.day:02d}"
            )
        if "IR_StateFILTER" in self._decoded:
            self._filter_replacement_status = (
                "off" if value("IR_StateFILTER") == 0 else "on"
            )
        if "IR_ALARM" in self._decoded:
            self._alarm_status = {0: "no", 1: "alarm", 2: "warning"}.get(
                value("IR_ALARM"), f"unknown_{value('IR_ALARM')}"
            )
        alarm_keys = [f"DI_AlarmCODE{code}" for code in range(53)]
        if all(key in self._decoded for key in alarm_keys):
            alarm_codes = [
                str(code) for code, key in enumerate(alarm_keys) if value(key) is True
            ]
            self._alarm_list = ", ".join(alarm_codes) if alarm_codes else "none"
        if "IR_CurWeekSpeed" in self._decoded:
            self._schedule_speed = _A21_SPEEDS.get(
                value("IR_CurWeekSpeed"),
                f"unknown_{value('IR_CurWeekSpeed')}",
            )
        if "HR_TIMER_MODE" in self._decoded:
            self._timer_mode = _A21_TIMER_MODES.get(
                value("HR_TIMER_MODE"), f"unknown_{value('HR_TIMER_MODE')}"
            )
        if isinstance(value("HR_RTC_TIME"), RtcTime):
            rtc = value("HR_RTC_TIME")
            self._rtc_time = f"{rtc.hours:02d}:{rtc.minutes:02d}:{rtc.seconds:02d}"
        if isinstance(value("HR_RTC_CALENDAR"), RtcCalendar):
            rtc = value("HR_RTC_CALENDAR")
            self._rtc_weekday = rtc.weekday
            self._rtc_date = f"20{rtc.year:02d}-{rtc.month:02d}-{rtc.day:02d}"

    def get_param(self, parameter: str) -> bool:
        key = _SEMANTIC_REGISTERS.get(parameter)
        if key is None:
            return False
        self.read_register(key)
        return True

    def _semantic_value(self, parameter: str, value: Any) -> Any:
        if parameter in {
            "state",
            "weekly_schedule_state",
            "humidity_sensor_state",
            "co2_sensor_state",
            "voc_sensor_state",
            "analogV_sensor_state",
        }:
            if value not in {"on", "off", True, False, 0, 1}:
                raise ValueError(f"Invalid {parameter} state: {value!r}")
            return value in {"on", True, 1}
        if parameter in {"filter_timer_reset", "reset_alarms"}:
            return True
        if parameter == "speed":
            if value == "off":
                self.write_register("CL_POWER", False)
                return None
            if value not in _A21_SPEED_VALUES:
                raise ValueError(f"Invalid A21 speed: {value!r}")
            return _A21_SPEED_VALUES[value]
        if parameter == "timer_mode":
            if value not in _A21_TIMER_VALUES:
                raise ValueError(f"Invalid A21 timer mode: {value!r}")
            return _A21_TIMER_VALUES[value]
        if parameter in {"rtc_time", "rtc_date"}:
            return value
        return _as_raw_number(value)

    def set_param(self, parameter: str, value: Any) -> bool:
        key = _SEMANTIC_REGISTERS.get(parameter)
        if key is None:
            return False
        converted = self._semantic_value(parameter, value)
        if converted is None:
            return True
        return self.write_register(key, converted)

    def set_parameters(
        self,
        values: Mapping[str, Any],
        include_extra_write_parameters: bool = True,
    ) -> bool:
        targets = dict(values)
        extra_parameters = {}
        if include_extra_write_parameters and self.extra_write_parameters_callback:
            extra_parameters = self.extra_write_parameters_callback()
            for key, value in extra_parameters.items():
                targets.setdefault(key, value)
        if not targets:
            return False
        success = all(self.set_param(key, value) for key, value in targets.items())
        if extra_parameters and (
            result_callback := getattr(
                self, "extra_write_parameters_result_callback", None
            )
        ):
            result_callback(success)
        return success

    set_params = set_parameters

    def set_man_speed_percent(self, speed: int) -> bool:
        target = max(0, min(100, int(speed)))
        return self.write_register("HR_ManualSPEED", target)

    def read_weekly_schedule_day(self, day: int) -> dict[int, WeeklyScheduleRecord]:
        if day not in range(1, 8):
            raise ValueError(f"Invalid schedule day: {day}")
        labels = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
        label = labels[day - 1]
        base = 126 + (day - 1) * 8
        self.read_raw(Table.HOLDING_REGISTER, base, 8)
        self._decode_cache()
        records: dict[int, WeeklyScheduleRecord] = {}
        for period in range(1, 5):
            schedule = self._decoded[f"HR_SetWEEK_{label}_P{period}"]
            end = self._decoded[f"HR_SetWEEK_{label}_P{period}_END"]
            records[period] = WeeklyScheduleRecord(
                day=day,
                period=period,
                speed=_A21_SPEEDS[schedule.speed],
                end_hour=end.hour,
                end_minute=end.minute,
                reserved=schedule.temperature,
            )
        return records

    def write_weekly_schedule_record(self, record: WeeklyScheduleRecord) -> bool:
        if not isinstance(record, WeeklyScheduleRecord):
            raise TypeError("record must be a WeeklyScheduleRecord")
        if record.day not in range(1, 8) or record.period not in range(1, 5):
            raise ValueError("Invalid A21 weekly schedule slot")
        labels = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
        prefix = f"HR_SetWEEK_{labels[record.day - 1]}_P{record.period}"
        speed = _A21_SPEED_VALUES[record.speed]
        written = self.write_register(
            prefix, SchedulePeriod(speed=speed, temperature=record.reserved)
        )
        if record.period < 4:
            written = (
                self.write_register(
                    f"{prefix}_END",
                    ScheduleEnd(hour=record.end_hour, minute=record.end_minute),
                )
                and written
            )
        return written

    def rtc_datetime_params(self, value: datetime) -> dict[str, Any]:
        return {
            "rtc_time": RtcTime(value.hour, value.minute, value.second),
            "rtc_date": RtcCalendar(
                value.day, value.isoweekday(), value.month, value.year % 100
            ),
        }

    def set_rtc_datetime(self, value: datetime) -> bool:
        return self.set_parameters(
            self.rtc_datetime_params(value), include_extra_write_parameters=False
        )

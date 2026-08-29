"""Protocol-level tests for the VENTS A21 Modbus transport."""

from __future__ import annotations

from datetime import datetime
import importlib
from pathlib import Path
import sys
import types

import pytest


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
PACKAGE = "ecovent_v2_a21_test"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT_PATH)]
sys.modules.setdefault(PACKAGE, package)

a21_modbus = importlib.import_module(f"{PACKAGE}.a21_modbus")
a21_registers = importlib.import_module(f"{PACKAGE}.a21_registers")
number_helpers = importlib.import_module(f"{PACKAGE}.number_helpers")
schedule_helpers = importlib.import_module(f"{PACKAGE}.schedule_helpers")

A21ModbusDevice = a21_modbus.A21ModbusDevice
A21ModbusError = a21_modbus.A21ModbusError
Table = a21_registers.Table
WeeklyScheduleRecord = schedule_helpers.WeeklyScheduleRecord


class Response:
    def __init__(self, *, registers=None, bits=None, error=False, exception_code=None):
        self.registers = registers
        self.bits = bits
        self._error = error
        self.exception_code = exception_code

    def isError(self):
        return self._error


class FakeModbusClient:
    def __init__(self, *, identity=1, fail_slots=()):
        self.connected = False
        self.closed = False
        self.calls = []
        self.fail_slots = set(fail_slots)
        self.coils = [False] * 26
        self.discrete_inputs = [False] * 72
        self.input_registers = [0] * 54
        self.holding_registers = [0] * 183
        self.input_registers[0:5] = [230, 50, 210, 220, 70]
        self.input_registers[9:18] = [3000, 55, 0, 900, 0, 12, 0, 37, 0]
        self.input_registers[23:25] = [1234, 1200]
        self.input_registers[25:27] = [0x0506, 4]
        self.input_registers[27:29] = [0x173B, 365]
        self.input_registers[29:31] = [0x173B, 42]
        self.input_registers[31:39] = [0, 1, 23, 0x0102, 0x0304, 2026, identity, 0]
        self.holding_registers[2] = 1
        self.holding_registers[5:18] = [
            0,
            0,
            40,
            40,
            70,
            70,
            100,
            100,
            100,
            100,
            100,
            100,
            50,
        ]
        self.holding_registers[44:61] = [
            23,
            60,
            1200,
            400,
            40,
            1,
            23,
            0x001E,
            7,
            2,
            0,
            0,
            0,
            0,
            90,
            0,
            0,
        ]
        self.holding_registers[61:65] = [0x0506, 4, 0x1004, 0x071A]
        for day in range(7):
            base = 126 + day * 8
            self.holding_registers[base : base + 8] = [
                0x0117,
                0x0600,
                0x0217,
                0x0900,
                0x0317,
                0x1300,
                0x0417,
                0x173B,
            ]

    def connect(self):
        self.calls.append(("connect",))
        self.connected = True
        return True

    def close(self):
        self.calls.append(("close",))
        self.closed = True
        self.connected = False

    def _read(self, name, values, address, count, device_id):
        self.calls.append((name, address, count, device_id))
        slots = {(name, slot) for slot in range(address, address + count)}
        if slots & self.fail_slots:
            return Response(error=True, exception_code=2)
        payload = values[address : address + count]
        if name in {"read_coils", "read_discrete_inputs"}:
            return Response(bits=payload)
        return Response(registers=payload)

    def read_coils(self, address, *, count, device_id):
        return self._read("read_coils", self.coils, address, count, device_id)

    def read_discrete_inputs(self, address, *, count, device_id):
        return self._read(
            "read_discrete_inputs", self.discrete_inputs, address, count, device_id
        )

    def read_input_registers(self, address, *, count, device_id):
        return self._read(
            "read_input_registers", self.input_registers, address, count, device_id
        )

    def read_holding_registers(self, address, *, count, device_id):
        return self._read(
            "read_holding_registers", self.holding_registers, address, count, device_id
        )

    def write_coil(self, address, value, *, device_id):
        self.calls.append(("write_coil", address, value, device_id))
        self.coils[address] = value
        return Response()

    def write_coils(self, address, values, *, device_id):
        self.calls.append(("write_coils", address, list(values), device_id))
        self.coils[address : address + len(values)] = values
        return Response()

    def write_register(self, address, value, *, device_id):
        self.calls.append(("write_register", address, value, device_id))
        self.holding_registers[address] = value
        return Response()

    def write_registers(self, address, values, *, device_id):
        self.calls.append(("write_registers", address, list(values), device_id))
        self.holding_registers[address : address + len(values)] = values
        return Response()


def device(client=None, **kwargs):
    return A21ModbusDevice(
        transport="modbus_tcp",
        endpoint="192.0.2.10",
        port=502,
        unit_id=7,
        name="Test A21",
        model="VENTS VUT 270 V5B EC A21",
        client=client or FakeModbusClient(),
        **kwargs,
    )


def test_identity_gate_rejects_non_a21_before_any_write():
    client = FakeModbusClient(identity=2)
    fan = device(client)

    assert fan.init_device() is False
    assert fan.identity_probe_failed is True
    assert fan.id == "DEFAULT_DEVICEID"
    assert [call[0] for call in client.calls] == ["connect", "read_input_registers"]


def test_init_reads_complete_non_sensitive_surface_and_populates_semantics():
    client = FakeModbusClient()
    fan = device(client)

    assert fan.init_device() is True
    assert fan.id == "a21-modbus_tcp-192.0.2.10-502-7"
    assert fan.state == "off"
    assert fan.speed == "speed_1"
    assert fan.man_speed == 50
    assert fan.temperature == 23.0
    assert fan.room_temperature == 22.0
    assert fan.outdoor_temperature == 5.0
    assert fan.humidity == 55
    assert fan.co2 == 900
    assert fan.fan1_speed == 1234
    assert fan.fan2_speed == 1200
    assert fan.firmware == "1.2 2026-04-03"
    assert fan.rtc_time == "04:05:06"
    assert fan.rtc_date == "2026-07-16"
    assert fan.filter_timer_countdown == "365d 23h 59m "
    assert fan.machine_hours == "42d 23h 59m "
    assert fan.unavailable_addresses == frozenset()

    holding_reads = [
        call for call in client.calls if call[0] == "read_holding_registers"
    ]
    assert holding_reads
    assert all(
        not ({124, 125} & set(range(address, address + count)))
        for _, address, count, _ in holding_reads
    )
    assert not any(call[0].startswith("write_") for call in client.calls)


def test_configured_device_id_survives_endpoint_reconfiguration():
    fan = device(device_id="a21-original-endpoint-502-7")

    assert fan.init_device() is True
    assert fan.id == "a21-original-endpoint-502-7"


def test_profile_entity_requirements_use_modbus_semantics():
    fan = device()

    assert fan.profile_has_entity_requirements(
        required_params=("temperature",),
        required_capabilities=("a21_modbus",),
    )
    assert not fan.profile_has_entity_requirements(
        required_params=("analogV",),
    )


def test_raw_api_uses_all_published_modbus_function_shapes():
    client = FakeModbusClient()
    fan = device(client)

    assert fan.read_raw(Table.COIL, 0) == (0,)
    assert fan.read_raw(Table.DISCRETE_INPUT, 0) == (0,)
    assert fan.read_raw(Table.INPUT_REGISTER, 37) == (1,)
    assert fan.read_raw(Table.HOLDING_REGISTER, 2) == (1,)
    assert fan.write_raw(Table.COIL, 0, (True,))
    assert fan.write_raw(Table.COIL, 5, (True, False))
    assert fan.write_raw(Table.HOLDING_REGISTER, 2, (3,))
    assert fan.write_raw(Table.HOLDING_REGISTER, 61, (0x0102, 3))

    names = {call[0] for call in client.calls}
    assert {
        "read_coils",
        "read_discrete_inputs",
        "read_input_registers",
        "read_holding_registers",
        "write_coil",
        "write_coils",
        "write_register",
        "write_registers",
    } <= names
    assert all(call[-1] == 7 for call in client.calls if call[0] != "connect")


def test_write_permissions_ranges_and_enum_are_enforced():
    fan = device(FakeModbusClient())

    with pytest.raises(PermissionError):
        fan.write_raw(Table.INPUT_REGISTER, 37, (1,))
    with pytest.raises(PermissionError):
        fan.write_raw(Table.HOLDING_REGISTER, 0, (1,))
    with pytest.raises(ValueError, match="coil values"):
        fan.write_raw(Table.COIL, 0, (2,))
    with pytest.raises(PermissionError):
        fan.write_register("IR_DeviceTYPE", 1)
    with pytest.raises(ValueError):
        fan.write_register("HR_SetTEMP", 99)
    with pytest.raises(ValueError, match="enum value"):
        fan.write_register("HR_OPERATION_MODE", 9)
    with pytest.raises(ValueError, match="documented range"):
        fan.write_register("CL_RESET_FILTER_TIMER", False)
    with pytest.raises(ValueError, match="allowed ranges"):
        fan.write_register("HR_SetFILTER_TIMER", 69)
    assert fan.write_register("HR_SetFILTER_TIMER", 0)
    assert fan.write_register("HR_SetFILTER_TIMER", 70)


def test_resilient_full_poll_records_one_missing_optional_address():
    client = FakeModbusClient(fail_slots={("read_holding_registers", 150)})
    fan = device(client)
    fan.read_register("IR_DeviceTYPE")

    assert fan.update() is True
    assert fan.last_poll_complete is False
    assert (Table.HOLDING_REGISTER, 150) in fan.unavailable_addresses
    assert fan.state == "off"
    assert fan.id == "DEFAULT_DEVICEID"


def test_resilient_poll_clears_stale_optional_semantic_value():
    client = FakeModbusClient()
    fan = device(client)
    fan.read_register("IR_DeviceTYPE")

    assert fan.update() is True
    assert fan.outdoor_temperature == 5.0
    assert fan.decoded_registers["IR_CurTEMP_SuAirIn"] == 5.0

    client.fail_slots.add(("read_input_registers", 1))
    client.input_registers[1] = 2500

    assert fan.update() is True
    assert fan.last_poll_complete is False
    assert (Table.INPUT_REGISTER, 1) in fan.unavailable_addresses
    assert (Table.INPUT_REGISTER, 1) not in fan.raw_registers
    assert "IR_CurTEMP_SuAirIn" not in fan.decoded_registers
    assert fan.outdoor_temperature is None


def test_poll_fails_when_a_required_operational_address_is_missing():
    client = FakeModbusClient(fail_slots={("read_coils", 0)})
    fan = device(client)
    fan.read_register("IR_DeviceTYPE")

    assert fan.update() is False
    assert fan.last_poll_complete is False
    assert (Table.COIL, 0) in fan.unavailable_addresses


def test_transport_wide_error_fails_fast_without_recursive_address_splitting():
    class FailedServerClient(FakeModbusClient):
        def read_coils(self, address, *, count, device_id):
            self.calls.append(("read_coils", address, count, device_id))
            return Response(error=True, exception_code=4)

    client = FailedServerClient()
    fan = device(client)

    with pytest.raises(A21ModbusError, match="failed"):
        fan.update()
    assert [call[0] for call in client.calls] == ["connect", "read_coils"]


def test_illegal_address_scan_has_a_hard_request_budget():
    class RejectAllAddressesClient(FakeModbusClient):
        def read_holding_registers(self, address, *, count, device_id):
            self.calls.append(("read_holding_registers", address, count, device_id))
            return Response(error=True, exception_code=2)

    client = RejectAllAddressesClient()

    with pytest.raises(A21ModbusError, match="too many illegal-address"):
        device(client).update()
    reads = [call for call in client.calls if call[0] == "read_holding_registers"]
    assert len(reads) <= 34


def test_ha_number_values_stay_numeric_and_use_a21_ranges():
    client = FakeModbusClient()
    fan = device(client)
    encode = number_helpers.encode_number_write_value

    assert fan.parameter_range("temperature_treshold") == (15, 30)
    assert fan.parameter_range("filter_timer_setpoint") == (70, 365)
    assert fan.parameter_range("voc_treshold") == (20, 100)
    assert fan.parameter_range("supply_speed_low") == (0, 100)

    assert fan.set_param("filter_timer_setpoint", encode(90, 2, native_numeric=True))
    assert fan.set_param("co2_treshold", encode(1200, 2, native_numeric=True))
    assert fan.set_param("voc_treshold", encode(60, 2, native_numeric=True))
    assert client.holding_registers[58] == 90
    assert client.holding_registers[46] == 1200
    assert client.holding_registers[48] == 60


def test_semantic_writes_schedule_and_rtc_preserve_a21_encoding():
    client = FakeModbusClient()
    fan = device(client)
    fan.read_all_registers()

    assert fan.set_param("state", "on")
    assert fan.set_param("speed", "manual")
    assert fan.set_man_speed_percent(63)
    assert client.coils[0] is True
    assert client.holding_registers[2] == 255
    assert client.holding_registers[17] == 63

    monday = fan.read_weekly_schedule_day(1)
    assert monday[2].speed == "speed_2"
    assert monday[2].reserved == 23
    assert fan.write_weekly_schedule_record(
        WeeklyScheduleRecord(1, 2, "speed_5", 10, 30, reserved=24)
    )
    assert client.holding_registers[128:130] == [0x0518, 0x0A1E]
    assert ("write_registers", 128, [0x0518, 0x0A1E], 7) in client.calls

    assert fan.set_rtc_datetime(datetime(2026, 7, 16, 12, 34, 56))
    assert client.holding_registers[61:65] == [0x2238, 12, 0x1004, 0x071A]
    assert ("write_registers", 61, [0x2238, 12, 0x1004, 0x071A], 7) in client.calls


def test_grouped_a21_writes_fail_without_partial_state():
    class RejectGroupedWrites(FakeModbusClient):
        def write_registers(self, address, values, *, device_id):
            self.calls.append(("write_registers", address, list(values), device_id))
            return Response(error=True)

    client = RejectGroupedWrites()
    fan = device(client)
    rtc_before = list(client.holding_registers[61:65])
    schedule_before = list(client.holding_registers[128:130])

    with pytest.raises(A21ModbusError):
        fan.set_rtc_datetime(datetime(2026, 7, 16, 12, 34, 56))
    assert client.holding_registers[61:65] == rtc_before
    assert "HR_RTC_TIME" not in fan.decoded_registers
    assert "HR_RTC_CALENDAR" not in fan.decoded_registers

    with pytest.raises(A21ModbusError):
        fan.write_weekly_schedule_record(
            WeeklyScheduleRecord(1, 2, "speed_5", 10, 30, reserved=24)
        )
    assert client.holding_registers[128:130] == schedule_before
    assert "HR_SetWEEK_Mo_P2" not in fan.decoded_registers
    assert "HR_SetWEEK_Mo_P2_END" not in fan.decoded_registers


def test_opportunistic_a21_write_reports_transport_result():
    fan = device()
    results = []
    fan.extra_write_parameters_callback = lambda: {
        "rtc_time": "1e2d13",
        "rtc_date": "1704041a",
    }
    fan.extra_write_parameters_result_callback = results.append
    fan.set_param = lambda _key, _value: False

    assert not fan.set_parameters({"state": "on"})
    assert results == [False]

    fan.set_param = lambda _key, _value: True
    assert fan.set_parameters({"state": "on"})
    assert results == [False, True]


def test_short_or_error_response_is_not_accepted_as_success():
    class ShortClient(FakeModbusClient):
        def read_input_registers(self, address, *, count, device_id):
            return Response(registers=[])

    with pytest.raises(A21ModbusError, match="short"):
        device(ShortClient()).read_raw(Table.INPUT_REGISTER, 37)

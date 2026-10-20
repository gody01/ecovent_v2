"""Regression tests for issue #122 A21 RTC weekday and transport resets."""

from __future__ import annotations

import ast
import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest

COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
COORDINATOR_PATH = COMPONENT_PATH / "coordinator.py"
PACKAGE = "ecovent_v2_issue122_test"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT_PATH)]
sys.modules.setdefault(PACKAGE, package)

a21_modbus = importlib.import_module(f"{PACKAGE}.a21_modbus")
a21_registers = importlib.import_module(f"{PACKAGE}.a21_registers")

A21ModbusDevice = a21_modbus.A21ModbusDevice
A21ModbusError = a21_modbus.A21ModbusError
RtcCalendar = a21_registers.RtcCalendar


def test_rtc_calendar_decode_ignores_device_weekday():
    """A device read with a non-ISO weekday must decode (issue #122)."""
    spec = a21_registers.get_register("HR_RTC_CALENDAR")
    # 2026-04-23 is a Thursday (ISO 4); the field device reports weekday 1.
    assert spec.decode((0x1701, 0x041A)) == RtcCalendar(23, 1, 4, 26)
    with pytest.raises(ValueError, match="weekday does not match"):
        spec.encode(RtcCalendar(23, 1, 4, 26))


def _coordinator_method(name):
    tree = ast.parse(COORDINATOR_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "EcoVentCoordinator":
            for item in node.body:
                if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    if item.name == name:
                        return item
    raise AssertionError(f"EcoVentCoordinator.{name} not found")


def test_periodic_clock_check_decode_failure_skips_sync():
    """A clock-check ValueError must never fail the coordinator update."""
    method = _coordinator_method("_async_maybe_sync_clock")
    namespace = {"_LOGGER": types.SimpleNamespace(debug=lambda *_a: None)}
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
            str(COORDINATOR_PATH),
            "exec",
        ),
        namespace,
    )
    events = []

    class Hass:
        async def async_add_executor_job(self, callback, *args):
            return callback(*args)

    coordinator = types.SimpleNamespace(
        hass=Hass(),
        _fan=types.SimpleNamespace(name="Test fan"),
        _silent_mode=False,
        _last_clock_sync_check=None,
        _device_clock_now=lambda: "NOW",
        _clock_sync_check_due=lambda _now: True,
        _recently_synced_clock=lambda _now: False,
        _host_clock_synchronized=lambda: True,
        _refresh_device_clock_state=lambda: (_ for _ in ()).throw(
            ValueError("calendar weekday does not match calendar date")
        ),
        _record_clock_sync=lambda now: events.append(("record", now)),
    )
    asyncio.run(namespace["_async_maybe_sync_clock"](coordinator))
    assert events == []


class StickyResetClient:
    """Stay broken after a transport reset until close() releases the slot."""

    def __init__(self):
        self.connected = False
        self.calls = []
        self.broken = False
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
        self.input_registers[31:39] = [0, 1, 23, 0x0102, 0x0304, 2026, 1, 0]
        self.holding_registers[2] = 1
        self.holding_registers[5:18] = [0, 0, 40, 40, 70, 70, 100, 100, 100, 100, 100, 100, 50]
        self.holding_registers[44:61] = [23, 60, 1200, 400, 40, 1, 23, 0x001E, 7, 2, 0, 0, 0, 0, 90, 0, 0]
        # Valid RTC rows: 04:05:06 and Thursday 2026-07-16 (ISO 4).
        self.holding_registers[61:65] = [0x0506, 4, 0x1004, 0x071A]
        for day in range(7):
            base = 126 + day * 8
            self.holding_registers[base : base + 8] = [0x0117, 0x0600, 0x0217, 0x0900, 0x0317, 0x1300, 0x0417, 0x173B]

    def connect(self):
        self.calls.append(("connect",))
        self.connected = True
        return True

    def close(self):
        self.calls.append(("close",))
        self.connected = False
        self.broken = False

    def _read(self, name, values, address, count, device_id):
        if self.broken:
            raise ConnectionResetError(104, "Connection reset by peer")
        self.calls.append((name, address, count, device_id))
        payload = values[address : address + count]
        if name in {"read_coils", "read_discrete_inputs"}:
            return types.SimpleNamespace(isError=lambda: False, bits=list(payload))
        return types.SimpleNamespace(isError=lambda: False, registers=list(payload))

    def read_coils(self, address, *, count, device_id):
        return self._read("read_coils", self.coils, address, count, device_id)

    def read_discrete_inputs(self, address, *, count, device_id):
        return self._read("read_discrete_inputs", self.discrete_inputs, address, count, device_id)

    def read_input_registers(self, address, *, count, device_id):
        return self._read("read_input_registers", self.input_registers, address, count, device_id)

    def read_holding_registers(self, address, *, count, device_id):
        return self._read("read_holding_registers", self.holding_registers, address, count, device_id)


def _a21_device(client):
    return A21ModbusDevice(
        transport="modbus_tcp",
        endpoint="192.0.2.10",
        port=502,
        unit_id=7,
        name="Test A21",
        model="VENTS VUT 270 V5B EC A21",
        client=client,
    )


def test_transport_failure_closes_client_so_next_poll_recovers():
    """After ECONNRESET the next update must reconnect instead of failing."""
    client = StickyResetClient()
    fan = _a21_device(client)
    assert fan.update() is True

    client.broken = True
    with pytest.raises(A21ModbusError, match="transport failed"):
        fan.update()
    assert ("close",) in client.calls

    assert fan.update() is True

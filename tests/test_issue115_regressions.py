"""Issue #115: Vento countdown formats and acknowledged write-only actions."""

import ast
import asyncio
import re
import types
from typing import Any

import pytest

from ecovent_test_helpers import COMPONENT_PATH, Fan, packet_with_payload
from protocol_diagnostics import rejected_device_value_details, rejected_device_value_issue_body


def _runtime_methods(filename, class_name, names, functions=()):
    """Execute production methods without importing Home Assistant's runtime."""
    path = COMPONENT_PATH / filename
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
    nodes += [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    namespace = {"re": re, "Any": Any}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


SENSOR_METHODS = _runtime_methods(
    "sensor.py", "VentoSensor", {"filter_timer_countdown", "filter_remaining"},
    {"_parse_hours", "_parse_days"},
)
FAN_METHODS = _runtime_methods(
    "fan.py", "VentoExpertFan", {"_set_param", "async_reset_filter_timer", "async_reset_alarms"},
)


def _fan(unit="0300"):
    fan = Fan("192.0.2.1")
    fan.unit_type = unit
    fan.send = lambda _data: True
    return fan


@pytest.mark.parametrize("unit", ["0300", "0500", "0e00"])
@pytest.mark.parametrize("countdown", [[17, 8, 45], [17, 8, 45, 0]])
def test_bulk_countdown_populates_hours_and_remaining(unit, countdown):
    fan = _fan(unit)
    fan.firmware = "00090807e807"
    # Setpoint, timer counter and machine hours already use their documented widths.
    fan.receive = lambda: packet_with_payload([
        0xFE, 2, 0x63, 90, 0,
        0xFE, len(countdown), 0x64, *countdown,
        0xFE, 3, 0x0B, 30, 15, 2,
        0xFE, 4, 0x7E, 17, 8, 45, 0,
    ])
    assert fan._read_params("00630064000b007e", required_params=frozenset())
    assert not fan.last_missing_optional_params
    assert fan.filter_timer_setpoint == "90 d"
    assert fan.timer_counter == "2h 15m 30s "
    assert fan.machine_hours == "45d 8h 17m "
    sensor = types.SimpleNamespace(_fan=fan)
    sensor.filter_timer_countdown = types.MethodType(SENSOR_METHODS["filter_timer_countdown"], sensor)
    assert sensor.filter_timer_countdown() == 1088.3
    assert SENSOR_METHODS["filter_remaining"](sensor) == 50


@pytest.mark.parametrize("bulk", [False, True])
@pytest.mark.parametrize("raw", [
    [60, 0, 45, 0], [0, 24, 45, 0], [0, 0, 110, 1],
    [0, 0], [1, 0, 0, 45, 0], [0, 0, 0, 0, 45, 0],
])
def test_invalid_countdown_poll_reports_raw_bytes(raw, bulk):
    fan = _fan()
    fan.receive = lambda: packet_with_payload([0xFE, len(raw), 0x64, *raw])
    if bulk:
        assert not fan._read_params("0064", required_params=frozenset())
    else:
        assert not fan.get_param("filter_timer_countdown")
    assert fan.filter_timer_countdown is None
    report, = rejected_device_value_details(fan)
    assert report["id"] == "0x0064"
    assert report["raw_samples"] == [bytes(raw).hex()]
    assert bytes(raw).hex() in rejected_device_value_issue_body(fan)
    assert fan.unknown_params == {}


@pytest.mark.parametrize("service", ["async_reset_filter_timer", "async_reset_alarms"])
@pytest.mark.parametrize("answer", [[], [0x02, 1]])
def test_reset_service_accepts_acknowledgment_without_action_echo(service, answer):
    fan = _fan()
    fan.receive = lambda: packet_with_payload(answer)
    refreshes = []

    async def executor(func, *args):
        return func(*args)

    async def refresh():
        refreshes.append(True)

    entity = types.SimpleNamespace(
        _fan=fan,
        hass=types.SimpleNamespace(async_add_executor_job=executor),
        coordinator=types.SimpleNamespace(async_refresh_confirmed=refresh),
    )
    entity._set_param = types.MethodType(FAN_METHODS["_set_param"], entity)
    asyncio.run(FAN_METHODS[service](entity, None))
    assert refreshes == [True]


@pytest.mark.parametrize("service", ["async_reset_filter_timer", "async_reset_alarms"])
def test_reset_service_still_raises_on_no_response(service):
    fan = _fan()
    fan.receive = lambda: False
    refreshes = []

    async def executor(func, *args):
        return func(*args)

    async def refresh():
        refreshes.append(True)

    entity = types.SimpleNamespace(
        _fan=fan,
        hass=types.SimpleNamespace(async_add_executor_job=executor),
        coordinator=types.SimpleNamespace(async_refresh_confirmed=refresh),
    )
    entity._set_param = types.MethodType(FAN_METHODS["_set_param"], entity)
    with pytest.raises(RuntimeError, match="Failed to write"):
        asyncio.run(FAN_METHODS[service](entity, None))
    assert refreshes == [True]


@pytest.mark.parametrize("unit", ["0300", "1100", "0200", "0600"])
def test_all_bgcp_profiles_confirm_write_only_actions(unit):
    fan = _fan(unit)
    fan.receive = lambda: packet_with_payload([])
    for name, _values in fan.write_params.values():
        assert fan.set_param(name, "01")
    fan.receive = lambda: False
    for name, _values in fan.write_params.values():
        assert not fan.set_param(name, "01")


@pytest.mark.parametrize("answer", [False, [0xFD, 0x65], [0x65, 0], [0xFE]])
def test_write_only_failure_controls(answer):
    fan = _fan()
    fan.receive = lambda: packet_with_payload(answer) if answer is not False else False
    assert not fan.set_param("filter_timer_reset", "01")


@pytest.mark.parametrize("answer", [[], [0x65, 1], [0x02, 3]])
def test_mixed_write_still_requires_matching_readable_row(answer):
    fan = _fan()
    fan.receive = lambda: packet_with_payload(answer)
    assert not fan.set_parameters({"filter_timer_reset": "01", "speed": "low"})


def test_mixed_write_and_extra_write_only_acknowledgment():
    fan = _fan()
    fan.receive = lambda: packet_with_payload([0x02, 1])
    assert fan.set_parameters({"filter_timer_reset": "01", "speed": "low"})
    results = []
    fan.extra_write_parameters_callback = lambda: {"reset_alarms": "01"}
    fan.extra_write_parameters_result_callback = results.append
    assert fan.set_param("speed", "low")
    assert results == [True]


@pytest.mark.parametrize("parameter", ["filter_timer_reset", "reset_alarms"])
@pytest.mark.parametrize("answered", [True, False])
def test_a21_actions_use_modbus_acknowledgment_without_readback(parameter, answered):
    from test_a21_modbus import FakeModbusClient, Response, device

    class ActionClient(FakeModbusClient):
        def write_coil(self, address, value, *, device_id):
            self.calls.append(("write_coil", address, value, device_id))
            return Response() if answered else None

    client = ActionClient()
    fan = device(client)
    assert fan.set_param(parameter, "01") is answered
    assert len([call for call in client.calls if call[0] == "write_coil"]) == 1
    assert not any(call[0] == "read_coils" for call in client.calls)


def test_outbound_validation_does_not_create_device_rejection_report():
    fan = _fan()
    assert not fan.set_param("humidity_treshold", "ff")
    assert rejected_device_value_details(fan) == ()

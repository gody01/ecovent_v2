"""Identity-gated startup and wire-width measurement regressions (#129/#131)."""

import pytest
from ecovent_test_helpers import Fan, packet_with_payload


def _extract_wire(fan):
    commands = []
    identity_available = [False]

    def send(command):
        commands.append(command)
        return True

    def receive():
        if commands[-1] == "01b9" and not identity_available[0]:
            return False
        # Exact #129 rows remain readable even while identity replies are lost.
        payload = [
            0x01, 1, 0x02, 1, 0xFE, 2, 0x04, 0xB0, 0x04,
            0x05, 1, 0xFE, 3, 0x06, 0, 0, 0, 0x24, 0,
            0xFE, 6, 0x86, 2, 2, 16, 6, 0xE6, 0x07,
        ]
        if identity_available[0]:
            payload += [0xFE, 2, 0xB9, 6, 0]
        return packet_with_payload(payload, device_id=fan.id.encode())

    fan.send = send
    fan.receive = receive
    return commands, identity_available


def test_issue129_failed_identity_does_not_poll_with_default_vento_map():
    # A known device ID bypasses discovery, not the unit-type probe.
    fan = Fan("192.0.2.1", fan_id="0123456789ABCDEF")
    commands, _available = _extract_wire(fan)

    assert fan.init_device() is False
    assert commands and set(commands) == {"01b9"}
    assert fan._unit_type_id is None
    assert not fan._rejected_value_reports


def test_issue129_retry_initializes_extract_rows_without_false_rejections():
    fan = Fan("192.0.2.1")
    commands, available = _extract_wire(fan)
    # Keep discovery on its real command path, but let it return the default ID.
    packet_receive = fan.receive
    fan.receive = lambda: (
        packet_with_payload([0xFE, 16, 0x7C, *b"DEFAULT_DEVICEID"])
        if commands[-1] == "017c" else packet_receive()
    )
    assert fan.init_device() is False
    available[0] = True
    assert fan.init_device() is True
    assert fan.profile_key == "extract_fan"
    assert fan.firmware == "2.2 2022-06-16"
    assert fan.boost_status == "on"
    assert fan.boost_timer_countdown == "0h 0m 0s "
    assert fan.turn_on_delay_timer == "0 m"
    assert fan.battery_voltage is None
    assert not fan._rejected_value_reports


@pytest.mark.parametrize("param, payload", [
    ("boost_timer_countdown", [0xFE, 2, 0x06, 0, 0]),
    ("turn_on_delay_timer", [0xFE, 2, 0x24, 0, 0]),
])
def test_issue129_extract_malformed_widths_remain_reportable(param, payload):
    fan = Fan("192.0.2.1")
    fan.unit_type = "0600"
    fan.send = lambda _command: True
    fan.receive = lambda: packet_with_payload(payload)
    assert fan.get_param(param) is False
    assert any(report["name"] == param for report in fan._rejected_value_reports.values())


@pytest.mark.parametrize("value", [500, 501, 505, 65535])
def test_issue131_voc_measurement_accepts_unsigned_wire_range(value):
    fan = Fan("192.0.2.1")
    fan.unit_type = "1100"
    fan.firmware = "000c0109e907"
    fan.send = lambda _command: True
    fan.receive = lambda: packet_with_payload([
        0xFF, 3, 0xFE, 2, 0x20, *value.to_bytes(2, "little"),
    ])
    assert fan.get_param("voc") is True
    assert fan.voc == value
    assert not fan._rejected_value_reports


@pytest.mark.parametrize("raw", [b"\xf9", b"\xf9\x01\x00"])
def test_issue131_voc_wrong_width_still_rejects_without_overwriting(raw):
    fan = Fan("192.0.2.1")
    fan.unit_type = "1100"
    fan.voc = "f401"
    fan.send = lambda _command: True
    fan.receive = lambda: packet_with_payload([
        0xFF, 3, *([0xFE, len(raw)] if len(raw) > 1 else []), 0x20, *raw,
    ])
    assert fan.get_param("voc") is False
    assert fan.voc == 500
    assert any(report["name"] == "voc" for report in fan._rejected_value_reports.values())


def test_issue131_voc_threshold_bounds_remain_independent():
    fan = Fan("192.0.2.1")
    fan.unit_type = "1100"
    commands = []
    fan.send = lambda command: commands.append(command) or True
    assert fan.parameter_range("voc_treshold") == (50, 250)
    assert fan.set_param("voc_treshold", "f901") is False
    assert commands == []

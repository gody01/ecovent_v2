"""Shared test helpers for EcoVent protocol tests."""

from pathlib import Path
import importlib.util
import sys


COMPONENT_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
MODULE_PATH = COMPONENT_PATH / "ecoventv2.py"
PROTOCOL_REFERENCE_PATH = COMPONENT_PATH.parents[1] / "protocol.md"
sys.path.insert(0, str(COMPONENT_PATH))
SPEC = importlib.util.spec_from_file_location("vendored_ecoventv2", MODULE_PATH)
ecoventv2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ecoventv2)
Fan = ecoventv2.Fan


def packet_with_payload(
    payload,
    *,
    packet_type=0x02,
    device_id=b"DEFAULT_DEVICEID",
    password=b"",
    function=0x06,
):
    body = (
        bytes([packet_type, len(device_id)])
        + device_id
        + bytes([len(password)])
        + password
        + bytes([function])
        + bytes(payload)
    )
    checksum = sum(body) & 0xFFFF
    return b"\xfd\xfd" + body + checksum.to_bytes(2, byteorder="little")


def packet_for_write_command(command):
    """Echo one FUNC 0x03 request as the documented FUNC 0x06 response."""
    if not command.startswith("03"):
        raise ValueError("command must use BGCP write-with-response function 0x03")
    return packet_with_payload(bytes.fromhex(command[2:]))

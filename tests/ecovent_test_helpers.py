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


def packet_with_payload(payload):
    body = (
        bytes([0x02, 0x10]) + b"DEFAULT_DEVICEID" + bytes([0x00, 0x06]) + bytes(payload)
    )
    checksum = sum(body) & 0xFFFF
    return b"\xfd\xfd" + body + checksum.to_bytes(2, byteorder="little")

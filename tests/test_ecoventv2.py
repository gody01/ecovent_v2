"""Regression tests for the vendored EcoVent V2 protocol client."""

from pathlib import Path
import importlib.util
import socket
import unittest
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "ecovent_v2"
    / "ecoventv2.py"
)
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


class ParseResponseTest(unittest.TestCase):
    def test_parse_response_names_shared_oxxify_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x0E, 0x00])))
        self.assertEqual(fan.unit_type, "TwinFresh Style Wifi V.2 / Oxxify smart 50")

    def test_parse_response_names_newer_atmo_unit_type(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0xB9, 0x1A, 0x00]))
        )
        self.assertEqual(fan.unit_type, "TwinFresh Atmo / newer Blauberg Vento")

    def test_parse_response_skips_unknown_parameter_ids(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFF, 0x12, 0x34, 0xAB, 0x01, 0x01])
            )
        )
        self.assertEqual(fan.unknown_params, {0x1234: "ab"})
        self.assertEqual(fan.state, "on")

    def test_parse_response_rejects_bad_header_and_checksum(self):
        fan = Fan("192.0.2.1")
        good_packet = packet_with_payload([0x01, 0x01])
        bad_header = b"\x00\x00" + good_packet[2:]
        bad_checksum = good_packet[:-1] + bytes([good_packet[-1] ^ 0xFF])

        self.assertFalse(fan.parse_response(bad_header))
        self.assertIsNone(fan.state)
        self.assertFalse(fan.parse_response(bad_checksum))
        self.assertIsNone(fan.state)

    def test_parse_response_rejects_short_packet(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(b"\xfd\xfd"))

    def test_parse_response_keeps_unknown_enum_values(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0x02, 0x99, 0xB7, 0x44])))
        self.assertEqual(fan.speed, "Unknown speed 153")
        self.assertEqual(fan.airflow, "Unknown airflow 68")

    def test_heater_status_setter_does_not_recurse(self):
        fan = Fan("192.0.2.1")
        fan.heater_status = "01"
        self.assertEqual(fan.heater_status, "on")

    def test_parse_response_reads_filter_timer_setpoint(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(packet_with_payload([0xFE, 0x02, 0x63, 0x6D, 0x01]))
        )
        self.assertEqual(fan.filter_timer_setpoint, "365 d")

    def test_parse_response_reads_four_byte_filter_timer_countdown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x04, 0x64, 0x11, 0x08, 0x48, 0x00])
            )
        )
        self.assertEqual(fan.filter_timer_countdown, "72d 8h 17m ")

    def test_parse_response_reads_padded_filter_timer_countdown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x05, 0x64, 0x00, 0x11, 0x08, 0x48, 0x00])
            )
        )
        self.assertEqual(fan.filter_timer_countdown, "72d 8h 17m ")

    def test_parse_response_rejects_dangling_extended_marker(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.parse_response(packet_with_payload([0xFF])))

    def test_parse_response_keeps_known_params_with_bad_value_as_unknown(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(
            fan.parse_response(
                packet_with_payload([0xFE, 0x03, 0x24, 0x01, 0x02, 0x03, 0x01, 0x01])
            )
        )
        self.assertEqual(fan.unknown_params, {0x0024: "010203"})
        self.assertEqual(fan.state, "on")

    def test_parse_response_skips_no_value_parameter_markers(self):
        fan = Fan("192.0.2.1")
        self.assertTrue(fan.parse_response(packet_with_payload([0xFD, 0x65, 0x01, 0x01])))
        self.assertEqual(fan.unknown_params, {})
        self.assertEqual(fan.state, "on")


class PacketBuilderTest(unittest.TestCase):
    def test_builds_default_discovery_packet(self):
        fan = Fan("192.0.2.1")
        packet = fan.build_packet(
            fan.func["read"] + fan.encode_params("007c"),
            fan_id="DEFAULT_DEVICEID",
        )
        self.assertEqual(
            packet.upper(),
            "FDFD021044454641554C545F44455649434549440431313131017CF805",
        )

    def test_checksum_wraps_to_16_bits_little_endian(self):
        fan = Fan("192.0.2.1")
        payload = "ff" * 300
        checksum = (0xFF * 300) & 0xFFFF
        self.assertEqual(fan.chksum(payload), checksum.to_bytes(2, "little").hex())

    def test_encodes_extended_and_multibyte_params(self):
        fan = Fan("192.0.2.1")
        self.assertEqual(fan.encode_params("0302"), "ff0302")
        self.assertEqual(fan.encode_params("00b9", "0e00"), "fe02b90e00")
        self.assertEqual(fan.encode_params("0302", "0102"), "ff03fe02020102")

    def test_update_does_not_read_write_only_reset_params(self):
        fan = Fan("192.0.2.1")
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((func, param, value))
            return True

        fan.do_func = do_func
        self.assertTrue(fan.update())
        _, params, _ = calls[0]
        self.assertNotIn("0065", params)
        self.assertNotIn("0080", params)

    def test_update_falls_back_to_individual_reads_after_bulk_failure(self):
        fan = Fan("192.0.2.1")
        calls = []

        def do_func(func, param, value="", retries=10):
            calls.append((param, retries))
            return len(param) == 4 and param == "0001"

        fan.params = {0x0001: ["state", fan.states], 0x0002: ["speed", fan.speeds]}
        fan.do_func = do_func

        self.assertTrue(fan.update())
        self.assertEqual(calls, [("00010002", 3), ("0001", 1), ("0002", 1)])
        self.assertFalse(fan._bulk_read_supported)


class DiscoveryTest(unittest.TestCase):
    def test_search_devices_times_out_cleanly_without_mutating_host(self):
        fan = Fan(None)

        class TimeoutSocket:
            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

            def settimeout(self, *args):
                pass

            def sendto(self, *args):
                pass

            def recvfrom(self, *args):
                raise socket.timeout()

            def close(self):
                self.closed = True

        sock = TimeoutSocket()
        with patch("socket.socket", return_value=sock):
            self.assertEqual(fan.search_devices(), [])
        self.assertIsNone(fan.host)


class TransportTest(unittest.TestCase):
    def test_receive_before_send_returns_false(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.receive())

    def test_do_func_retries_invalid_packet_before_success(self):
        fan = Fan("192.0.2.1")
        good_packet = packet_with_payload([0x01, 0x01])
        bad_packet = good_packet[:-1] + bytes([good_packet[-1] ^ 0xFF])
        responses = [bad_packet, good_packet]
        sent = []

        def send(data):
            sent.append(data)

        def receive():
            return responses.pop(0)

        fan.send = send
        fan.receive = receive

        self.assertTrue(fan.do_func(fan.func["read"], "0001"))
        self.assertEqual(len(sent), 2)
        self.assertEqual(fan.state, "on")


if __name__ == "__main__":
    unittest.main()

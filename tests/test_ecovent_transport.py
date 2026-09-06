"""Regression tests for EcoVent discovery and transport."""

import socket
import threading
import unittest
from unittest.mock import patch

from ecovent_test_helpers import Fan, packet_with_payload


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

    def test_search_devices_requires_device_id_and_does_not_store_other_rows(self):
        fan = Fan("192.0.2.1", fan_id="OWN_DEVICE_00001")
        fan._device_search = "OWN_DEVICE_00001"
        foreign_profile = packet_with_payload(
            [0xFE, 0x02, 0xB9, 0x11, 0x00],
            device_id=b"OTHER_DEVICE_001",
        )

        class ForeignResponseSocket:
            def __init__(self):
                self.responses = [(foreign_profile, ("192.0.2.99", 4000))]

            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

            def settimeout(self, *args):
                pass

            def sendto(self, *args):
                pass

            def recvfrom(self, *args):
                if self.responses:
                    return self.responses.pop(0)
                raise socket.timeout()

            def close(self):
                self.closed = True

        with patch("socket.socket", return_value=ForeignResponseSocket()):
            self.assertEqual(fan.search_devices(), [])
        self.assertEqual(fan.profile_key, "vento")
        self.assertIsNone(fan.unit_type)
        self.assertEqual(fan._device_search, "OWN_DEVICE_00001")

    def test_search_devices_commits_only_the_requested_device_id(self):
        discovered_id = b"OTHER_DEVICE_001"
        response = packet_with_payload(
            [
                0xFE,
                len(discovered_id),
                0x7C,
                *discovered_id,
                0xFE,
                0x02,
                0xB9,
                0x11,
                0x00,
            ],
            device_id=discovered_id,
        )
        fan = Fan("192.0.2.1", fan_id="OWN_DEVICE_00001")
        fan._device_search = "OWN_DEVICE_00001"

        class DiscoverySocket:
            def __init__(self):
                self.responses = [(response, ("192.0.2.99", 4000))]

            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

            def settimeout(self, *args):
                pass

            def sendto(self, *args):
                pass

            def recvfrom(self, *args):
                if self.responses:
                    return self.responses.pop(0)
                raise socket.timeout()

            def close(self):
                self.closed = True

        with patch("socket.socket", return_value=DiscoverySocket()):
            self.assertEqual(fan.search_devices(), ["192.0.2.99"])
        self.assertEqual(fan.profile_key, "vento")
        self.assertIsNone(fan.unit_type)
        self.assertEqual(fan._device_search, "OWN_DEVICE_00001")

    def test_search_devices_waits_for_an_active_command_transaction(self):
        discovered_id = b"OTHER_DEVICE_001"
        response = packet_with_payload(
            [0xFE, len(discovered_id), 0x7C, *discovered_id],
            device_id=discovered_id,
        )
        response_received = threading.Event()
        result = []

        class DiscoverySocket:
            def __init__(self):
                self.responses = [(response, ("192.0.2.99", 4000))]

            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

            def settimeout(self, *args):
                pass

            def sendto(self, *args):
                pass

            def recvfrom(self, *args):
                if self.responses:
                    response_received.set()
                    return self.responses.pop(0)
                raise socket.timeout()

            def close(self):
                self.closed = True

        fan = Fan("192.0.2.1", fan_id="OWN_DEVICE_00001")
        fan._command_lock.acquire()
        try:
            with patch("socket.socket", return_value=DiscoverySocket()):
                thread = threading.Thread(
                    target=lambda: result.extend(fan.search_devices())
                )
                thread.start()
                self.assertTrue(response_received.wait(timeout=1))
                thread.join(timeout=0.05)
                self.assertTrue(thread.is_alive())
        finally:
            fan._command_lock.release()

        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, ["192.0.2.99"])


class TransportTest(unittest.TestCase):
    def test_poll_result_cannot_be_replaced_by_a_concurrent_write(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0e00"
        response_ready = threading.Event()
        writer_started = threading.Event()
        writer_done = threading.Event()
        results = []
        sent = []
        fan.send = lambda data: sent.append(data) or True
        fan.receive = lambda: packet_with_payload([0x25, 55] if sent[-1].startswith("01") else [1, 1])
        original = fan.send_command

        def send_command(command, *args, **kwargs):
            result = original(command, *args, **kwargs)
            if command == fan.func["read"]:
                response_ready.set()
                self.assertTrue(writer_started.wait(1))
                writer_done.wait(0.05)
            return result

        fan.send_command = send_command
        def write():
            response_ready.wait(1)
            writer_started.set()
            try:
                results.append(fan.set_param("state", "on"))
            finally:
                writer_done.set()

        thread = threading.Thread(target=write)
        thread.start()
        try:
            poll_ok = fan._read_params("0025", required_params=frozenset())
        finally:
            thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertTrue(poll_ok)
        self.assertEqual(results, [True])
        self.assertEqual(sum(data.startswith("01") for data in sent), 1)

    def test_receive_before_send_returns_false(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.receive())

    def test_send_reports_success_after_socket_sendall(self):
        fan = Fan("192.0.2.1")

        class FakeSocket:
            payload = None

            def sendall(self, payload):
                self.payload = payload

        sock = FakeSocket()
        fan.connect = lambda: sock
        fan.build_packet = lambda _data: "0001"

        self.assertTrue(fan.send("request"))
        self.assertEqual(sock.payload, b"\x00\x01")

    def test_send_failure_closes_the_socket(self):
        fan = Fan("192.0.2.1")

        class FailingSocket:
            closed = False

            def sendall(self, _payload):
                raise OSError("synthetic send failure")

            def close(self):
                self.closed = True

        sock = FailingSocket()
        fan.connect = lambda: sock
        fan.build_packet = lambda _data: "0001"

        self.assertFalse(fan.send("request"))
        self.assertTrue(sock.closed)
        self.assertIsNone(fan.socket)

    def test_send_command_retries_invalid_packet_before_success(self):
        fan = Fan("192.0.2.1")
        good_packet = packet_with_payload([0x01, 0x01])
        bad_packet = good_packet[:-1] + bytes([good_packet[-1] ^ 0xFF])
        responses = [bad_packet, good_packet]
        sent = []

        def send(data):
            sent.append(data)
            return True

        def receive():
            return responses.pop(0)

        fan.send = send
        fan.receive = receive

        self.assertTrue(fan.send_command(fan.func["read"], "0001"))
        self.assertEqual(len(sent), 2)
        self.assertEqual(fan.state, "on")

    def test_failed_send_cannot_be_confirmed_by_a_stale_response(self):
        fan = Fan("192.0.2.1")
        receive_calls = []
        fan.send = lambda _data: False
        fan.receive = lambda: receive_calls.append(True) or packet_with_payload(
            [0x01, 0x01]
        )

        self.assertFalse(
            fan.send_encoded_command(
                fan.func["write_return"], "0101", retries=1
            )
        )
        self.assertEqual(receive_calls, [])

    def test_read_commits_only_requested_decoded_rows(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x01, 0x02, 0x03])

        self.assertTrue(fan.send_command(fan.func["read"], "0001", retries=1))
        self.assertEqual(fan.state, "on")
        self.assertIsNone(fan.speed)

    def test_read_ignores_unrelated_unknown_row_without_recording_it(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x01, 0xAA, 0x55])

        self.assertTrue(fan.send_command(fan.func["read"], "0001", retries=1))
        self.assertEqual(fan.state, "on")
        self.assertEqual(fan.unknown_params, {})

    def test_value_mismatched_write_response_cannot_change_properties(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x00, 0x02, 0x03])

        self.assertFalse(
            fan.send_command(fan.func["write_return"], "0001", "01", retries=1)
        )
        self.assertIsNone(fan.state)
        self.assertIsNone(fan.speed)

    def test_rejected_write_does_not_record_unrelated_unknown_row(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x00, 0xAA, 0x55])

        self.assertFalse(
            fan.send_command(fan.func["write_return"], "0001", "01", retries=1)
        )
        self.assertIsNone(fan.state)
        self.assertEqual(fan.unknown_params, {})

    def test_write_commits_only_exactly_acknowledged_rows(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x01, 0x02, 0x03])

        self.assertTrue(
            fan.send_command(fan.func["write_return"], "0001", "01", retries=1)
        )
        self.assertEqual(fan.state, "on")
        self.assertIsNone(fan.speed)

    def test_partial_multi_write_ack_does_not_commit_any_requested_row(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x01, 0x01])

        self.assertFalse(
            fan.send_command(
                fan.func["write_return"], "00010002", "01", retries=1
            )
        )
        self.assertIsNone(fan.state)
        self.assertIsNone(fan.speed)

    def test_semantically_invalid_write_ack_is_not_success_or_cached(self):
        fan = Fan("192.0.2.1")
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload([0x77, 0x01])

        self.assertFalse(
            fan.send_command(fan.func["write_return"], "0077", "01", retries=1)
        )
        self.assertIsNone(fan.weekly_schedule_setup)

    def test_command_transaction_serializes_socket_exchange(self):
        fan = Fan("192.0.2.1")
        first_receive_entered = threading.Event()
        release_first_receive = threading.Event()
        second_send_entered = threading.Event()
        sent = []
        responses = [
            packet_with_payload([0x01, 0x01]),
            packet_with_payload([0x01, 0x00]),
        ]
        results = []

        def send(data):
            sent.append(data)
            if len(sent) == 2:
                second_send_entered.set()
            return True

        def receive():
            if len(sent) == 1:
                first_receive_entered.set()
                self.assertTrue(release_first_receive.wait(timeout=1))
            return responses.pop(0)

        def command(value):
            results.append(
                fan.send_command(fan.func["write_return"], "0001", value, retries=1)
            )

        fan.send = send
        fan.receive = receive
        first = threading.Thread(target=command, args=("01",))
        second = threading.Thread(target=command, args=("00",))

        first.start()
        self.assertTrue(first_receive_entered.wait(timeout=1))
        second.start()
        self.assertFalse(second_send_entered.wait(timeout=0.1))
        self.assertEqual(len(sent), 1)

        release_first_receive.set()
        first.join(timeout=1)
        second.join(timeout=1)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(results, [True, True])


if __name__ == "__main__":
    unittest.main()

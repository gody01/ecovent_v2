"""Regression tests for EcoVent discovery and transport."""

import socket
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


class TransportTest(unittest.TestCase):
    def test_receive_before_send_returns_false(self):
        fan = Fan("192.0.2.1")
        self.assertFalse(fan.receive())

    def test_send_command_retries_invalid_packet_before_success(self):
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

        self.assertTrue(fan.send_command(fan.func["read"], "0001"))
        self.assertEqual(len(sent), 2)
        self.assertEqual(fan.state, "on")


if __name__ == "__main__":
    unittest.main()

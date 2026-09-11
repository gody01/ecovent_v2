"""Replay real TwinFresh replies through the production poll/parser path.

Only parameter payloads are stored; header credentials are excluded. Device
identity and IP values inside payloads are replaced with same-width fixtures.
Recorded omissions are natural, not injected.
"""

import json
from pathlib import Path
import unittest

from ecovent_test_helpers import Fan, packet_with_payload


class TwinFreshCaptureTest(unittest.TestCase):
    def test_reported_schedule_final_frames_are_accepted_for_both_identities(self):
        """Replay #102's posted 0x0077 frames; this is not device-I/O proof."""
        frames = (
            ("fe06770101020f0006", 1, 6, 0),
            ("fe06770102020f0008", 2, 8, 0),
            ("fe06770103000f0015", 3, 21, 0),
            ("fe06770104020f3b17", 4, 23, 59),
            ("fe06770104020f0000", 4, 0, 0),
        )
        for firmware in ("00050a07e807", "0003040ae507"):
            for payload, period, hour, minute in frames:
                with self.subTest(firmware=firmware, payload=payload):
                    fan = Fan("192.0.2.1")
                    fan.unit_type = "0e00"
                    fan.firmware = firmware
                    self.assertTrue(
                        fan.parse_response(packet_with_payload(bytes.fromhex(payload)))
                    )
                    record = fan._weekly_schedule_setup_record
                    self.assertIsNotNone(record)
                    self.assertEqual(
                        (record.period, record.end_hour, record.end_minute, record.reserved),
                        (period, hour, minute, 15),
                    )

    def test_reported_firmware_05_accepts_the_captured_filter_frame(self):
        """Apply the #101 identity to the physical 0.3 frame format replay."""
        capture = json.loads(
            (Path(__file__).parent / "fixtures/twinfresh_style_wifi_poll_capture.json").read_text()
        )
        filter_transaction = next(
            transaction
            for transaction in capture["polls"][0]["transactions"]
            if transaction["request"] == "0064"
        )
        frame = filter_transaction["frames"][0]

        fan = Fan("192.0.2.1")
        fan.unit_type = "0e00"
        fan.firmware = "00050a07e807"
        fan.send = lambda _data: True
        fan.receive = lambda: packet_with_payload(bytes.fromhex(frame["payload"]))

        self.assertTrue(fan._read_params("0064", required_params=frozenset()))
        self.assertEqual(fan.filter_timer_countdown, "151d 11h 36m ")
        self.assertFalse(fan.last_missing_optional_params)
        self.assertNotIn(0x0064, fan._optional_param_backoff())

    def test_full_and_quick_polls_match_recorded_hardware(self):
        capture = json.loads(
            (Path(__file__).parent / "fixtures/twinfresh_style_wifi_poll_capture.json").read_text()
        )
        fan = Fan("192.0.2.1")
        queue = list(capture["identity_transactions"])
        for poll in capture["polls"]:
            queue.extend(poll["transactions"])

        def send(command, param, *args, **kwargs):
            # Old capture retried 0x0064 because the old decoder rejected its
            # valid width. The corrected client accepts the bulk row directly.
            while queue and queue[0]["request"] == "0064" and param != "0064":
                queue.pop(0)
            expected = queue.pop(0)
            self.assertEqual(command, fan.func["read"])
            self.assertEqual(param.lower(), expected["request"].lower())
            frames = iter(expected["frames"])

            def receive():
                frame = next(frames)
                if frame is None:
                    return False
                self.assertTrue(frame["valid_checksum"])
                return packet_with_payload(bytes.fromhex(frame["payload"]))

            fan.send = lambda _data: True
            fan.receive = receive
            return Fan.send_command(fan, command, param, *args, **kwargs)

        fan.send_command = send
        self.assertTrue(fan._read_params("00b90086"))
        self.assertEqual(fan._unit_type_id, capture["unit_type_id"])
        self.assertEqual(fan.firmware, capture["firmware"])
        for poll in capture["polls"]:
            with self.subTest(at=poll["at"], mode=poll["mode"]):
                result = fan.update() if poll["mode"] == "full" else fan.quick_update()
                self.assertEqual(result, poll["ok"])
                self.assertEqual(
                    (fan.state, fan.speed, fan.man_speed),
                    (poll["state"], poll["speed"], poll["man_speed"]),
                )
                self.assertFalse(fan.last_missing_optional_params)
                self.assertIsNotNone(fan.filter_timer_countdown)
                self.assertEqual(sorted(fan.last_unsupported_params), poll["unsupported"])
        self.assertFalse(queue)
        self.assertEqual(fan.audible_write_command_count, 0)

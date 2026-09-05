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

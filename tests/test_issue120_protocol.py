"""Freshbox register controls retain their documented wire meanings (issue #120)."""

import unittest

from ecovent_test_helpers import Fan, packet_for_write_command, packet_with_payload


def _fan_with_echo_wire(unit_type="0200"):
    """Exercise the real encoder, response correlation and setters without UDP."""
    fan = Fan("192.0.2.1")
    fan.unit_type = unit_type
    commands = []

    def send(command):
        commands.append(command)
        return True

    fan.send = send
    fan.receive = lambda: packet_for_write_command(commands[-1])
    return fan, commands


class Issue120ProtocolTest(unittest.TestCase):
    def test_freshbox_temperature_setpoint_decodes_raw_one_byte(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"
        self.assertEqual(fan.parameter_range("temperature_setpoint"), (15, 30))

        for value in (15, 22, 30):
            with self.subTest(value=value):
                self.assertTrue(
                    fan.parse_response(packet_with_payload([0x18, value]))
                )
                self.assertEqual(fan.temperature_setpoint, value)
                self.assertIn(0x0018, fan._last_response_param_ids)
                self.assertNotIn(0x0018, fan.unknown_params)

    def test_freshbox_temperature_setpoint_writes_raw_one_byte(self):
        fan, commands = _fan_with_echo_wire()

        for value in (15, 22, 30):
            with self.subTest(value=value):
                self.assertTrue(fan.set_param("temperature_setpoint", f"{value:02x}"))
                self.assertEqual(commands[-1], f"0318{value:02x}")
                self.assertEqual(fan.temperature_setpoint, value)

    def test_freshbox_temperature_setpoint_rejects_bounds_and_wrong_width(self):
        fan, commands = _fan_with_echo_wire()
        self.assertTrue(fan.set_param("temperature_setpoint", "16"))
        commands.clear()

        for raw in ("0e", "1f", "", "1600"):
            with self.subTest(raw=raw):
                self.assertFalse(fan.set_param("temperature_setpoint", raw))
                self.assertEqual(commands, [])
                self.assertEqual(fan.temperature_setpoint, 22)

        for payload, raw in (([0x18, 14], "0e"), ([0x18, 31], "1f"),
                             ([0xFE, 2, 0x18, 22, 0], "1600")):
            with self.subTest(payload=payload):
                self.assertTrue(fan.parse_response(packet_with_payload(payload)))
                self.assertNotIn(0x0018, fan._last_response_param_ids)
                self.assertEqual(fan.unknown_params[0x0018], raw)
                self.assertEqual(fan.temperature_setpoint, 22)

    def test_freshbox_heater_control_decodes_off_on_invert(self):
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"
        self.assertEqual(fan.parameter_options("heater_state"), ["off", "on", "invert"])

        for raw, value in enumerate(("off", "on", "invert")):
            with self.subTest(value=value):
                self.assertTrue(fan.parse_response(packet_with_payload([0x68, raw])))
                self.assertIn(0x0068, fan._last_response_param_ids)
                self.assertEqual(fan.heater_state, value)

    def test_freshbox_heater_control_writes_off_on_invert(self):
        fan, commands = _fan_with_echo_wire()

        for raw, value in enumerate(("off", "on", "invert")):
            with self.subTest(value=value):
                self.assertTrue(fan.set_param("heater_state", value))
                self.assertEqual(commands[-1], f"0368{raw:02x}")
                self.assertEqual(fan.heater_state, value)

        commands.clear()
        self.assertFalse(fan.set_param("heater_state", "toggle"))
        self.assertEqual(commands, [])
        self.assertEqual(fan.heater_state, "invert")

    def test_combined_controls_use_the_same_registers_and_decoders(self):
        fan, commands = _fan_with_echo_wire()
        self.assertTrue(
            fan.set_parameters(
                {"temperature_setpoint": "1e", "heater_state": "invert"},
                include_extra_write_parameters=False,
            )
        )
        self.assertEqual(commands, ["03181e6802"])
        self.assertEqual((fan.temperature_setpoint, fan.heater_state), (30, "invert"))

        commands.clear()
        self.assertFalse(
            fan.set_parameters(
                {"temperature_setpoint": "1f", "heater_state": "off"},
                include_extra_write_parameters=False,
            )
        )
        self.assertEqual(commands, [])
        self.assertEqual((fan.temperature_setpoint, fan.heater_state), (30, "invert"))

    def test_neighboring_freshbox_registers_keep_separate_meanings(self):
        fan, commands = _fan_with_echo_wire()
        self.assertTrue(
            fan.parse_response(
                packet_with_payload(
                    [0x01, 2, 0x02, 5, 0x06, 1, 0x18, 22, 0x32, 0,
                     0x66, 12, 0x68, 2, 0x81, 1]
                )
            )
        )
        self.assertEqual(fan.state, "toggle")
        self.assertEqual(fan.speed, "speed_5")
        self.assertEqual(fan.boost_status, "on")
        self.assertEqual(fan.boost_switch_status, "off")
        self.assertEqual(fan.boost_time, "12 m")
        self.assertEqual(fan.temperature_setpoint, 22)
        self.assertEqual(fan.heater_state, "invert")
        self.assertEqual(fan.heater_status, "on")

        self.assertTrue(fan.set_param("state", "toggle"))
        self.assertTrue(fan.set_param("boost_time", "0d"))
        self.assertEqual(commands, ["030102", "03660d"])
        self.assertEqual(fan.boost_time, "13 m")
        self.assertEqual((fan.heater_state, fan.heater_status), ("invert", "on"))

    def test_breezy_heater_control_retains_toggle_not_invert(self):
        fan, commands = _fan_with_echo_wire("1100")
        self.assertTrue(fan.parse_response(packet_with_payload([0x68, 2, 0x81, 0])))
        self.assertEqual(fan.heater_state, "toggle")
        self.assertEqual(fan.heater_status, "off")
        self.assertEqual(fan.parameter_options("heater_state"), ["off", "on", "toggle"])
        self.assertIsNone(fan.parameter_range("temperature_setpoint"))
        self.assertFalse(fan.supports_parameter("temperature_setpoint"))
        self.assertFalse(fan.set_param("heater_state", "invert"))
        self.assertFalse(fan.set_param("temperature_setpoint", "16"))
        self.assertEqual(commands, [])
        self.assertTrue(fan.set_param("heater_state", "toggle"))
        self.assertEqual(commands, ["036802"])
        self.assertEqual(fan.heater_state, "toggle")

    def test_freshbox_quick_poll_without_0006_keeps_device_available(self):
        # Issue #120: VENTS Micra ERV2 100 WiFi never answers boost_status
        # (0x0006). The quick poll must not request it, must require only
        # speed (0x0002), and must leave the device available.
        fan = Fan("192.0.2.1")
        fan.unit_type = "0200"
        profile = fan.device_profile
        self.assertEqual(profile.quick_update_request, "000B003200330081008300A100B6")
        quick_ids = {
            int(profile.quick_update_request[offset : offset + 4], 16)
            for offset in range(0, len(profile.quick_update_request), 4)
        }
        self.assertNotIn(0x0006, quick_ids)
        self.assertEqual(profile.poll_required_params, frozenset({0x0002}))
        for capability in (
            "heater",
            "temperature_probes",
            "five_speed_setpoints",
            "estimated_recovery_efficiency",
            "filter_maintenance",
        ):
            with self.subTest(capability=capability):
                self.assertIn(capability, profile.capabilities)
        # Reply to every requested row; 0x0006 is never answered, matching
        # the reporting unit, and must not affect availability.
        values = {
            0x000B: b"\x2a\x00\x00",
            0x0032: b"\x01",
            0x0033: b"\x00",
            0x0081: b"\x01",
            0x0083: b"\x00",
            0x00A1: b"\x01",
            0x00B6: b"\x01",
        }

        def send_command(function, params, value="", retries=10):
            payload = []
            for offset in range(0, len(params), 4):
                param_id = int(params[offset : offset + 4], 16)
                if param_id == 0x0006:
                    continue
                raw = values.get(param_id)
                if raw is None:
                    continue
                if len(raw) > 1:
                    payload.extend([0xFE, len(raw), param_id & 0xFF, *raw])
                else:
                    payload.extend([param_id & 0xFF, *raw])
            if not payload:
                return False
            return fan.parse_response(packet_with_payload(payload))

        fan.send_command = send_command
        self.assertTrue(fan.quick_update())
        self.assertEqual(fan._last_missing_required_params, frozenset())



if __name__ == "__main__":
    unittest.main()

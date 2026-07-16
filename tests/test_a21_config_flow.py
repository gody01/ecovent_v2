"""Static regressions for the A21 transport config flow."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
CONFIG_FLOW = COMPONENT / "config_flow.py"


class A21ConfigFlowTest(unittest.TestCase):
    """Keep the non-BGCP onboarding boundary explicit."""

    def test_config_flow_has_three_transport_paths_and_migration_version(self):
        source = CONFIG_FLOW.read_text()
        tree = ast.parse(source)

        self.assertIn("VERSION = 2", source)
        self.assertIn("TRANSPORT_BGCP_UDP", source)
        self.assertIn("TRANSPORT_MODBUS_TCP", source)
        self.assertIn("TRANSPORT_MODBUS_RTU", source)
        self.assertIn("CONF_TRANSPORT not in user_input", source)
        self.assertIn("create_device(config)", source)
        self.assertIn("identity_probe_failed", source)
        self.assertIn("UnsupportedDevice", source)
        self.assertIn("current_wifi_ip", source)
        self.assertIn("A21_BAUD_RATES", source)
        self.assertIn("A21_STOP_BITS", source)
        self.assertIn("vol.Range(min=1, max=16)", source)
        self.assertIn("defaults.get(CONF_STOPBITS, 2)", source)
        self.assertTrue(
            any(
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "async_step_modbus_tcp"
                for node in ast.walk(tree)
            )
        )

    def test_all_translations_label_every_new_transport_form(self):
        expected_steps = {"user", "bgcp", "modbus_tcp", "modbus_rtu", "reconfigure"}
        expected_modbus_fields = {
            "unit_id",
            "device_model",
            "serial_port",
            "baudrate",
            "parity",
            "stopbits",
        }

        for path in [
            COMPONENT / "strings.json",
            *(COMPONENT / "translations").glob("*.json"),
        ]:
            with self.subTest(path=path.name):
                config = json.loads(path.read_text())["config"]
                steps = config["step"]
                self.assertTrue(expected_steps <= steps.keys())
                self.assertEqual(
                    set(steps["modbus_tcp"]["data"]) & {"unit_id", "device_model"},
                    {"unit_id", "device_model"},
                )
                self.assertTrue(
                    expected_modbus_fields <= steps["reconfigure"]["data"].keys()
                )
                self.assertIn("unsupported_device", config["error"])


if __name__ == "__main__":
    unittest.main()

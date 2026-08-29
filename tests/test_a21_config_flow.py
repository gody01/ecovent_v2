"""Static regressions for the A21 transport config flow."""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
import types
import unittest


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
CONFIG_FLOW = COMPONENT / "config_flow.py"


def _class_method(tree, class_name, method_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    if item.name == method_name:
                        return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _module_function(tree, method_name):
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            if node.name == method_name:
                return node
    raise AssertionError(f"{method_name} not found")


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

    def test_bgcp_reconfigure_rejects_another_device_but_a21_keeps_stable_id(self):
        tree = ast.parse(CONFIG_FLOW.read_text())
        method = _class_method(tree, "ConfigFlow", "async_step_reconfigure")

        class CannotConnect(Exception):
            pass

        class InvalidAuth(Exception):
            pass

        class UnsupportedDevice(Exception):
            pass

        async def validate_input(_hass, _data):
            return {"id": "new-device", "title": "New device"}

        namespace = {
            "FlowResult": object,
            "TRANSPORT_BGCP_UDP": "bgcp_udp",
            "CONF_TRANSPORT": "transport",
            "UPDATE_INTERVAL": "update_interval",
            "CannotConnect": CannotConnect,
            "InvalidAuth": InvalidAuth,
            "UnsupportedDevice": UnsupportedDevice,
            "_LOGGER": types.SimpleNamespace(exception=lambda *_args: None),
            "_schema_for_transport": lambda _transport, _defaults=None: (
                lambda data: data
            ),
            "validate_input": validate_input,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(CONFIG_FLOW),
                "exec",
            ),
            namespace,
        )
        reconfigure = namespace["async_step_reconfigure"]

        class Flow:
            hass = object()

            def __init__(self, transport, unique_id="old-device"):
                self.entry = types.SimpleNamespace(
                    data={"transport": transport, "update_interval": 30},
                    unique_id=unique_id,
                )

            def _get_reconfigure_entry(self):
                return self.entry

            def async_abort(self, *, reason):
                return ("aborted", reason)

            def async_update_reload_and_abort(self, entry, *, data_updates):
                return ("updated", entry.unique_id, data_updates)

            def async_show_form(self, **kwargs):
                return ("form", kwargs)

        bgcp_result = asyncio.run(
            reconfigure(Flow("bgcp_udp"), {"update_interval": 30})
        )
        same_bgcp_result = asyncio.run(
            reconfigure(
                Flow("bgcp_udp", unique_id="new-device"), {"update_interval": 30}
            )
        )
        a21_result = asyncio.run(
            reconfigure(Flow("modbus_tcp"), {"update_interval": 30})
        )

        self.assertEqual(bgcp_result, ("aborted", "wrong_device"))
        self.assertEqual(same_bgcp_result[0], "updated")
        self.assertEqual(a21_result[0], "updated")
        for path in [
            COMPONENT / "strings.json",
            *(COMPONENT / "translations").glob("*.json"),
        ]:
            self.assertIn(
                "wrong_device", json.loads(path.read_text())["config"]["abort"]
            )

    def test_validation_cleanup_failure_does_not_replace_success(self):
        tree = ast.parse(CONFIG_FLOW.read_text())
        function = _module_function(tree, "validate_input")
        warnings = []

        class Device:
            id = "device-1"
            name = "Fan"
            current_wifi_ip = "192.0.2.1"
            identity_probe_failed = False

            def init_device(self):
                return True

            def close(self):
                raise OSError("close failed")

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        namespace = {
            "HomeAssistant": object,
            "Any": object,
            "CONF_TRANSPORT": "transport",
            "CONF_NAME": "name",
            "TRANSPORT_BGCP_UDP": "bgcp_udp",
            "CannotConnect": type("CannotConnect", (Exception,), {}),
            "InvalidAuth": type("InvalidAuth", (Exception,), {}),
            "UnsupportedDevice": type("UnsupportedDevice", (Exception,), {}),
            "create_device": lambda _config: Device(),
            "_LOGGER": types.SimpleNamespace(
                warning=lambda *args, **_kwargs: warnings.append(args)
            ),
        }
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(body=[function], type_ignores=[])
                ),
                str(CONFIG_FLOW),
                "exec",
            ),
            namespace,
        )

        result = asyncio.run(
            namespace["validate_input"](
                Hass(), {"transport": "bgcp_udp", "name": "Fan"}
            )
        )

        self.assertEqual(result, {"title": "Fan device-1", "id": "device-1"})
        self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()

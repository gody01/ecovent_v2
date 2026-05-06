"""Regression tests for issue #49 device clock synchronization."""

from pathlib import Path
import ast
import unittest


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
CONFIG_FLOW_PATH = COMPONENT_PATH / "config_flow.py"
COORDINATOR_PATH = COMPONENT_PATH / "coordinator.py"
FAN_PATH = COMPONENT_PATH / "fan.py"
INIT_PATH = COMPONENT_PATH / "__init__.py"


def _tree(path):
    return ast.parse(path.read_text())


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


class Issue49RegressionTest(unittest.TestCase):
    def test_auto_clock_sync_defaults_to_enabled_but_can_be_disabled(self):
        config_source = CONFIG_FLOW_PATH.read_text()
        init_source = INIT_PATH.read_text()
        coordinator_source = COORDINATOR_PATH.read_text()

        self.assertIn("CONF_AUTO_CLOCK_SYNC", config_source)
        self.assertIn("default=True", config_source)
        self.assertIn("entry.data.get(CONF_AUTO_CLOCK_SYNC, True)", init_source)
        self.assertIn("config.data.get(CONF_AUTO_CLOCK_SYNC, True)", coordinator_source)

    def test_periodic_clock_sync_is_gated_and_uses_ha_local_time(self):
        tree = _tree(COORDINATOR_PATH)
        update_data = _class_method(tree, "EcoVentCoordinator", "_async_update_data")
        clock_now = _class_method(tree, "EcoVentCoordinator", "_device_clock_now")
        clock_needed = _class_method(tree, "EcoVentCoordinator", "_clock_sync_needed")
        source = COORDINATOR_PATH.read_text()

        self.assertIn("_auto_clock_sync", source)
        self.assertIn("CLOCK_SYNC_DRIFT", source)
        self.assertIn("CLOCK_SYNC_INTERVAL", source)
        self.assertIn("_device_clock_datetime", source)
        self.assertIn("_local_wall_clock", source)
        self.assertIn("extra_write_parameters_callback", source)
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "_supports_device_clock_sync"
                for node in ast.walk(update_data)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute) and node.attr == "now"
                for node in ast.walk(clock_now)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Name) and node.id == "CLOCK_SYNC_DRIFT"
                for node in ast.walk(clock_needed)
            )
        )
        self.assertNotIn("replace(tzinfo=None)", source)

    def test_periodic_clock_sync_compares_existing_rtc_before_writing(self):
        tree = _tree(COORDINATOR_PATH)
        maybe_sync = _class_method(
            tree, "EcoVentCoordinator", "_async_maybe_sync_clock"
        )
        sync_params = _class_method(
            tree, "EcoVentCoordinator", "_clock_sync_params_if_needed"
        )
        clock_needed = _class_method(tree, "EcoVentCoordinator", "_clock_sync_needed")
        device_clock = _class_method(
            tree, "EcoVentCoordinator", "_device_clock_datetime"
        )

        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "_device_clock_datetime"
                for node in ast.walk(clock_needed)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute) and node.attr == "fromisoformat"
                for node in ast.walk(device_clock)
            )
        )
        maybe_sync_source = ast.get_source_segment(
            COORDINATOR_PATH.read_text(), maybe_sync
        )
        self.assertLess(
            maybe_sync_source.index("_clock_sync_check_due"),
            maybe_sync_source.index("_clock_sync_needed"),
        )
        self.assertLess(
            maybe_sync_source.index("_recently_synced_clock"),
            maybe_sync_source.index("set_rtc_datetime"),
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute) and node.attr == "rtc_datetime_params"
                for node in ast.walk(sync_params)
            )
        )

    def test_manual_clock_sync_service_is_registered(self):
        tree = _tree(FAN_PATH)
        setup = _module_function(tree, "async_setup_entry")
        sync_method = _class_method(tree, "VentoExpertFan", "async_sync_device_clock")

        self.assertTrue(
            any(
                isinstance(node, ast.Name) and node.id == "SERVICE_SYNC_DEVICE_CLOCK"
                for node in ast.walk(setup)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "async_sync_device_clock"
                for node in ast.walk(sync_method)
            )
        )


if __name__ == "__main__":
    unittest.main()

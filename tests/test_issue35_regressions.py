"""Static regressions for issue #35 follow-ups."""

from pathlib import Path
import ast
import unittest


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
FAN_PATH = COMPONENT_PATH / "fan.py"
FRONTEND_PATH = COMPONENT_PATH / "frontend.py"
INIT_PATH = COMPONENT_PATH / "__init__.py"
SWITCH_PATH = COMPONENT_PATH / "switch.py"
BINARY_SENSOR_PATH = COMPONENT_PATH / "binary_sensor.py"


def _tree(path):
    return ast.parse(path.read_text())


def _module_function(tree, method_name):
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            if node.name == method_name:
                return node
    raise AssertionError(f"{method_name} not found")


def _class_method(tree, class_name, method_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    if item.name == method_name:
                        return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _executor_calls(node, target_attr):
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if not isinstance(func, ast.Attribute) or func.attr != "async_add_executor_job":
            continue
        if not call.args:
            continue
        callback = call.args[0]
        if isinstance(callback, ast.Attribute) and callback.attr == target_attr:
            yield call


class Issue35RegressionTest(unittest.TestCase):
    def test_frontend_digest_file_io_runs_in_executor(self):
        tree = _tree(FRONTEND_PATH)
        register = _module_function(tree, "async_register_frontend")

        read_bytes_calls = [
            node
            for node in ast.walk(register)
            if isinstance(node, ast.Attribute) and node.attr == "read_bytes"
        ]
        executor_calls = [
            node
            for node in ast.walk(register)
            if isinstance(node, ast.Attribute) and node.attr == "async_add_executor_job"
        ]

        self.assertEqual(read_bytes_calls, [])
        self.assertTrue(executor_calls)

    def test_direct_speed_change_is_live_fan_control(self):
        tree = _tree(FAN_PATH)
        turn_on = _class_method(tree, "VentoExpertFan", "async_turn_on")
        set_percentage = _class_method(tree, "VentoExpertFan", "async_set_percentage")
        set_preset = _class_method(tree, "VentoExpertFan", "async_set_preset_mode")

        self.assertTrue(
            any(
                len(call.args) >= 3 and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(turn_on, "set_percentage")
            )
        )
        self.assertTrue(
            any(
                len(call.args) >= 3 and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(set_percentage, "set_percentage")
            )
        )
        self.assertTrue(
            any(
                len(call.args) >= 3 and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(set_preset, "set_preset_mode")
            )
        )

    def test_weekly_schedule_switch_stays_visible(self):
        switch_source = SWITCH_PATH.read_text()
        init_source = INIT_PATH.read_text()
        tree = _tree(SWITCH_PATH)

        self.assertIn('"_weekly_schedule_state"', switch_source)
        self.assertIn('"weekly_schedule_state"', switch_source)
        self.assertIsNotNone(
            _class_method(tree, "VentoSwitch", "weekly_schedule_state")
        )
        self.assertNotIn('f"switch.{device_slug}_weekly_schedule"', init_source)

    def test_reported_legacy_entity_migrations_are_listed(self):
        init_source = INIT_PATH.read_text()

        self.assertIn('fan.id + "_speed1"', init_source)
        self.assertIn('f"sensor.{device_slug}_fan_1_speed"', init_source)

    def test_alarm_status_keeps_problem_binary_sensor(self):
        binary_sensor_source = BINARY_SENSOR_PATH.read_text()
        init_source = INIT_PATH.read_text()

        self.assertIn('"_alarm_status"', binary_sensor_source)
        self.assertIn('"alarm_status"', binary_sensor_source)
        self.assertIn("BinarySensorDeviceClass.PROBLEM", binary_sensor_source)
        self.assertIn('on_values=("alarm", "warning")', binary_sensor_source)
        self.assertNotIn('fan.id + "_alarm_status"', init_source)


if __name__ == "__main__":
    unittest.main()

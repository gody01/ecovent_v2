"""Static regressions for Home Assistant fan direction mapping."""

from pathlib import Path
import ast
import unittest


FAN_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2" / "fan.py"
)


def _fan_tree():
    return ast.parse(FAN_PATH.read_text())


def _constant_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found")


def _class_method(tree, class_name, method_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    if item.name == method_name:
                        return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _string_constants(node):
    return {
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


class FanDirectionTest(unittest.TestCase):
    def test_turn_on_accepts_legacy_speed_argument(self):
        tree = _fan_tree()
        turn_on = _class_method(tree, "VentoExpertFan", "async_turn_on")

        self.assertIn("speed", _string_constants(turn_on))

    def test_advertised_directions_match_home_assistant_service_values(self):
        tree = _fan_tree()
        directions = _constant_assignment(tree, "DIRECTIONS")
        set_direction = _class_method(tree, "VentoExpertFan", "set_direction")

        self.assertEqual(directions, ["forward", "reverse"])
        self.assertTrue(set(directions).issubset(_string_constants(set_direction)))

    def test_protocol_airflow_values_stay_internal_to_direction_mapping(self):
        tree = _fan_tree()
        current_direction = _class_method(tree, "VentoExpertFan", "current_direction")
        set_direction = _class_method(tree, "VentoExpertFan", "set_direction")
        set_airflow_mode = _class_method(tree, "VentoExpertFan", "set_airflow_mode")

        current_constants = _string_constants(current_direction)
        set_constants = _string_constants(set_direction)
        set_airflow_constants = _string_constants(set_airflow_mode)

        self.assertIn("air_supply", current_constants)
        self.assertIn("reverse", current_constants)
        self.assertIn("ventilation", set_constants)
        self.assertIn("air_supply", set_constants)
        self.assertIn("state", set_airflow_constants)
        self.assertIn("on", set_airflow_constants)
        self.assertIn("airflow", set_airflow_constants)

    def test_direction_and_oscillation_turn_on_before_airflow_change(self):
        tree = _fan_tree()
        set_direction = _class_method(tree, "VentoExpertFan", "set_direction")
        oscillate = _class_method(tree, "VentoExpertFan", "set_oscillating")

        for method in (set_direction, oscillate):
            with self.subTest(method=method.name):
                calls = [
                    call
                    for call in ast.walk(method)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "set_airflow_mode"
                    and len(call.args) >= 2
                    and isinstance(call.args[-1], ast.Constant)
                    and call.args[-1].value is True
                ]
                self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()

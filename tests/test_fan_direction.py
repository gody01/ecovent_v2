"""Static regressions for Home Assistant fan direction mapping."""

from pathlib import Path
import ast
import unittest


FAN_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "ecovent_v2"
    / "fan.py"
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

        current_constants = _string_constants(current_direction)
        set_constants = _string_constants(set_direction)

        self.assertIn("air_supply", current_constants)
        self.assertIn("reverse", current_constants)
        self.assertIn("ventilation", set_constants)
        self.assertIn("air_supply", set_constants)


if __name__ == "__main__":
    unittest.main()

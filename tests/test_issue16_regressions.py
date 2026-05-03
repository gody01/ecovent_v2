"""Regression tests for issue #16 schedule polling behavior."""

from pathlib import Path
import ast
import unittest


COORDINATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "ecovent_v2"
    / "coordinator.py"
)


def _class_method(tree, class_name, method_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    if item.name == method_name:
                        return item
    raise AssertionError(f"{class_name}.{method_name} not found")


class Issue16RegressionTest(unittest.TestCase):
    def test_weekly_schedule_polling_is_gated_by_enabled_state(self):
        source = COORDINATOR_PATH.read_text()
        tree = ast.parse(source)
        should_refresh = _class_method(
            tree, "EcoVentCoordinator", "_should_refresh_schedule_week"
        )
        post_init = _class_method(tree, "EcoVentCoordinator", "_async_post_init_setup")

        self.assertIn("weekly_schedule_state == \"on\"", source)
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "_should_refresh_schedule_week"
                for node in ast.walk(post_init)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Constant)
                and node.value == "weekly_schedule_setup"
                for node in ast.walk(should_refresh)
            )
        )


if __name__ == "__main__":
    unittest.main()

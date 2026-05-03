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

    def test_schedule_save_refreshes_edited_days_before_diffing(self):
        tree = ast.parse(COORDINATOR_PATH.read_text())
        write_schedule = _class_method(
            tree, "EcoVentCoordinator", "async_write_schedule"
        )
        load_schedule_days = _class_method(
            tree, "EcoVentCoordinator", "_load_schedule_days"
        )

        calls = [
            node
            for node in ast.walk(write_schedule)
            if isinstance(node, ast.Call)
        ]
        load_call_lineno = next(
            node.lineno
            for node in calls
            if isinstance(node.func, ast.Attribute)
            and node.func.attr == "async_add_executor_job"
            and any(
                isinstance(arg, ast.Attribute) and arg.attr == "_load_schedule_days"
                for arg in node.args
            )
        )
        diff_call_lineno = next(
            node.lineno
            for node in calls
            if isinstance(node.func, ast.Name)
            and node.func.id == "changed_schedule_records"
        )

        self.assertLess(load_call_lineno, diff_call_lineno)
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "read_weekly_schedule_day"
                for node in ast.walk(load_schedule_days)
            )
        )


if __name__ == "__main__":
    unittest.main()

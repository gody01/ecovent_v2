"""Regression tests for issue #16 schedule polling behavior."""

from pathlib import Path
import ast
import logging
import types
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
    def test_weekly_schedule_polling_keeps_editor_cache_warm_when_disabled(self):
        source = COORDINATOR_PATH.read_text()
        tree = ast.parse(source)
        should_refresh = _class_method(
            tree, "EcoVentCoordinator", "_should_refresh_schedule_week"
        )
        post_init = _class_method(tree, "EcoVentCoordinator", "_async_post_init_setup")
        should_refresh_source = ast.get_source_segment(source, should_refresh)

        self.assertIn("not self._weekly_schedule", should_refresh_source)
        self.assertIn("state = self._fan.weekly_schedule_state", should_refresh_source)
        self.assertIn('state not in ("on", "off")', should_refresh_source)
        self.assertIn('state == "on"', should_refresh_source)
        self.assertIn("self.updateCounter % 10 == 0", should_refresh_source)
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "_should_refresh_schedule_week"
                for node in ast.walk(post_init)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Constant) and node.value == "weekly_schedule_setup"
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
            node for node in ast.walk(write_schedule) if isinstance(node, ast.Call)
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

    def test_schedule_state_write_reports_transport_failure(self):
        source = COORDINATOR_PATH.read_text()
        write_schedule = _class_method(
            ast.parse(source), "EcoVentCoordinator", "async_write_schedule"
        )
        method_source = ast.get_source_segment(source, write_schedule)

        self.assertIn("written = await self.hass.async_add_executor_job", method_source)
        self.assertIn('"weekly_schedule_state"', method_source)
        self.assertIn("if not written", method_source)
        self.assertIn("Failed to write weekly schedule state", method_source)

    def test_incomplete_schedule_read_preserves_last_complete_day(self):
        source = COORDINATOR_PATH.read_text()
        load_schedule_days = _class_method(
            ast.parse(source), "EcoVentCoordinator", "_load_schedule_days"
        )
        namespace = {"_LOGGER": logging.getLogger(__name__)}
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(body=[load_schedule_days], type_ignores=[])
                ),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        complete = {period: f"old-{period}" for period in range(1, 5)}
        partial = {period: f"partial-{period}" for period in range(1, 4)}
        fresh = {period: f"fresh-{period}" for period in range(1, 5)}
        reads = iter((partial, fresh))
        coordinator = types.SimpleNamespace(
            _fan=types.SimpleNamespace(
                name="Test fan",
                read_weekly_schedule_day=lambda _day: next(reads),
            ),
            _weekly_schedule={1: complete},
        )

        namespace["_load_schedule_days"](coordinator, [1])
        self.assertEqual(coordinator._weekly_schedule[1], complete)

        namespace["_load_schedule_days"](coordinator, [1])
        self.assertEqual(coordinator._weekly_schedule[1], fresh)


if __name__ == "__main__":
    unittest.main()

"""Structural regression checks for complete protocol refreshes."""

import ast
from pathlib import Path
import unittest


COORDINATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "ecovent_v2"
    / "coordinator.py"
)


class Issue63RegressionTest(unittest.TestCase):
    def test_coordinator_rejects_incomplete_protocol_refresh(self):
        tree = ast.parse(COORDINATOR_PATH.read_text())
        coordinator = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "EcoVentCoordinator"
        )
        update = next(
            node
            for node in coordinator.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_async_update_data"
        )

        assigned_names = {
            target.id
            for node in ast.walk(update)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        raised_names = {
            node.exc.func.id
            for node in ast.walk(update)
            if isinstance(node, ast.Raise)
            and isinstance(node.exc, ast.Call)
            and isinstance(node.exc.func, ast.Name)
        }

        self.assertIn("update_complete", assigned_names)
        self.assertIn("UpdateFailed", raised_names)


if __name__ == "__main__":
    unittest.main()

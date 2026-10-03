"""Persistence and public issue-link tests for rejected device values."""

import ast
import sys
import types
import unittest
from unittest.mock import patch

from ecovent_test_helpers import COMPONENT_PATH, Fan, packet_with_payload
from protocol_diagnostics import (
    rejected_device_value_details,
    rejected_device_value_issue_body,
)


COORDINATOR_PATH = COMPONENT_PATH / "coordinator.py"


def _coordinator_method():
    tree = ast.parse(COORDINATOR_PATH.read_text())
    coordinator = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "EcoVentCoordinator"
    )
    return next(
        node for node in coordinator.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_update_rejected_device_value_repair_issue"
    )


def _report(param_id=0x004A, *, count=1, episodes=None):
    return {
        "id": f"0x{param_id:04X}",
        "name": "fan1_speed",
        "reason_class": "out_of_range",
        "reason": "Invalid fan1_speed: 5100 is outside 0..5000",
        "count": count,
        "first_seen": "2026-10-03T12:00:00+00:00",
        "last_seen": "2026-10-03T12:00:01+00:00",
        "min_raw_hex": "ec13",
        "max_raw_hex": "ec13",
        "min_raw_int": 5100,
        "max_raw_int": 5100,
        "raw_samples": ["ec13"],
        "episodes": episodes or [],
        "integration_version": "1.2.19",
    }


class RejectedValueRepairTest(unittest.TestCase):
    def setUp(self):
        self.issues = {}
        self.creates = []
        registry = types.ModuleType("homeassistant.helpers.issue_registry")
        registry.IssueSeverity = types.SimpleNamespace(WARNING="warning")
        registry.async_get = lambda _hass: types.SimpleNamespace(issues=self.issues)

        def create(_hass, domain, issue_id, **kwargs):
            self.creates.append((domain, issue_id, kwargs))
            self.issues[(domain, issue_id)] = types.SimpleNamespace(data=kwargs["data"])

        def delete(_hass, domain, issue_id):
            self.issues.pop((domain, issue_id), None)

        registry.async_create_issue = create
        registry.async_delete_issue = delete
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.__path__ = []
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.__path__ = []
        helpers.issue_registry = registry
        self.modules = {
            "homeassistant": homeassistant,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.issue_registry": registry,
        }
        namespace = {
            "_LOGGER": types.SimpleNamespace(debug=lambda *_a, **_k: None, warning=lambda *_a, **_k: None),
            "DOMAIN": "ecovent_v2",
            "_report_version": lambda: self.version,
            "rejected_device_value_details": rejected_device_value_details,
            "rejected_device_value_issue_url": lambda _fan, details: "https://example.invalid/?body=" + str(details),
            "rejected_device_value_issue_id": lambda entry_id: f"rejected_device_values_{entry_id}",
            "async_delete_rejected_device_value_issue": lambda hass, entry_id: delete(
                hass, "ecovent_v2", f"rejected_device_values_{entry_id}"
            ),
        }
        self.version = "1.2.19"
        exec(compile(ast.Module(body=[_coordinator_method()], type_ignores=[]), str(COORDINATOR_PATH), "exec"), namespace)
        self.update = namespace["_update_rejected_device_value_repair_issue"]

    def _coordinator(self, fan):
        return types.SimpleNamespace(
            _fan=fan,
            hass=object(),
            config_entry=types.SimpleNamespace(entry_id="entry-1"),
        )

    def test_repair_and_diagnostics_persist_through_valid_value_and_re_setup(self):
        with patch.dict(sys.modules, self.modules):
            fan = Fan("192.0.2.1")
            fan.unit_type = "1100"
            fan.send_command = lambda *a, **k: fan.parse_response(
                packet_with_payload(bytes((0xFE, 3, 0x4A, 0xEC, 0x13, 0x00)))
            )
            fan._read_params("004a", required_params=frozenset())
            first = self._coordinator(fan)
            self.update(first)
            self.assertIn(("ecovent_v2", "rejected_device_values_entry-1"), self.issues)

            fan.send_command = lambda *a, **k: fan.parse_response(
                packet_with_payload(bytes((0xFE, 2, 0x4A, 0xA0, 0x0F)))
            )
            self.assertTrue(fan._read_params("004a", required_params=frozenset()))
            self.update(first)
            self.assertEqual(len(self.creates), 1)
            self.assertTrue(rejected_device_value_details(fan))

            reloaded = Fan("192.0.2.1")
            second = self._coordinator(reloaded)
            self.update(second)
            self.assertTrue(rejected_device_value_details(reloaded))
            self.assertEqual(len(self.creates), 1)
            self.assertIn(("ecovent_v2", "rejected_device_values_entry-1"), self.issues)

    def test_version_change_clears_old_report_and_allows_fresh_report(self):
        with patch.dict(sys.modules, self.modules):
            fan = Fan("192.0.2.1")
            fan._rejected_value_reports[(0x004A, "out_of_range")] = _report()
            self.update(self._coordinator(fan))
            self.assertEqual(len(self.creates), 1)

            self.version = "1.2.20"
            reloaded = Fan("192.0.2.1")
            self.update(self._coordinator(reloaded))
            self.assertFalse(reloaded._rejected_value_reports)
            self.assertNotIn(("ecovent_v2", "rejected_device_values_entry-1"), self.issues)

            reloaded._rejected_value_reports[(0x0027, "out_of_range")] = _report(0x0027)
            self.update(self._coordinator(reloaded))
            self.assertEqual(len(self.creates), 2)
            stored = self.issues[("ecovent_v2", "rejected_device_values_entry-1")].data["rejected_values"]
            self.assertEqual([item["id"] for item in stored], ["0x0027"])

    def test_issue_body_has_contextual_episode_and_no_secrets(self):
        fan = Fan("192.0.2.1", password="secret", fan_id="private-device-id")
        fan._rejected_value_reports[(0x004A, "out_of_range")] = _report(
            episodes=[{"prev_valid": "1450", "bad_samples": ["ec13"], "next_valid": "1480"}]
        )
        body = rejected_device_value_issue_body(fan)
        self.assertIn("`fan1_speed` `0x004A`", body)
        self.assertIn("1450 -> ec13 -> 1480", body)
        self.assertIn("count 1", body)
        for secret in ("192.0.2.1", "private-device-id", "secret"):
            self.assertNotIn(secret, body)


if __name__ == "__main__":
    unittest.main()

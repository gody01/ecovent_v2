"""Ignore-persistence tests for the hardware profile mismatch Repair.

Issue #130 reports that the mismatch Repair reappears after the user ignores
it in Home Assistant. Root cause: Home Assistant drops the dismissal when the
issue is deleted, and the coordinator deleted the issue whenever the rejected
set was transiently empty (early polls after restart/reload, firmware
re-reads) or on entry unload, then recreated it once the rows were re-learned.
The fix leaves dismissed issues in place for the same rejected set and only
resurfaces (delete + create) when the set positively changed.
"""

import ast
import sys
import types
import unittest
from unittest.mock import patch

from ecovent_test_helpers import COMPONENT_PATH, Fan
from protocol_diagnostics import (
    hardware_profile_mismatch_issue_url,
    hardware_profile_mismatch_state,
    unsupported_optional_poll_parameter_summary,
)


COORDINATOR_PATH = COMPONENT_PATH / "coordinator.py"

ISSUE125_130_ROWS = [
    0x0011,
    0x001A,
    0x0025,
    0x0027,
    0x0129,
    0x0315,
    0x031F,
    0x0320,
    0x0403,
    0x0404,
    0x0405,
]


def _coordinator_nodes():
    tree = ast.parse(COORDINATOR_PATH.read_text())
    module_fns = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    coordinator = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "EcoVentCoordinator"
    )
    method = next(
        node for node in coordinator.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_update_hardware_profile_mismatch_repair_issue"
    )
    return [
        module_fns["hardware_profile_mismatch_issue_id"],
        module_fns["async_delete_hardware_profile_mismatch_issue"],
        method,
    ]


def _mismatch_fan(rejected):
    fan = Fan("192.0.2.1")
    fan.unit_type = "1600"
    fan.firmware = "000c0109e907"
    fan._unsupported_optional_poll_params = set(rejected)
    return fan


class MismatchRepairIgnoreTest(unittest.TestCase):
    def setUp(self):
        self.issues = {}
        self.creates = []
        self.deletes = []
        registry = types.ModuleType("homeassistant.helpers.issue_registry")
        registry.IssueSeverity = types.SimpleNamespace(WARNING="warning")
        registry.async_get = lambda _hass: types.SimpleNamespace(issues=self.issues)

        def create(_hass, domain, issue_id, **kwargs):
            # Model Home Assistant core: updating an existing issue keeps its
            # dismissal; only delete + create resurfaces an ignored issue.
            self.creates.append((domain, issue_id, kwargs))
            previous = self.issues.get((domain, issue_id))
            dismissed = (
                getattr(previous, "dismissed_version", None) if previous else None
            )
            self.issues[(domain, issue_id)] = types.SimpleNamespace(
                data=kwargs.get("data", {}),
                dismissed_version=dismissed,
            )

        def delete(_hass, domain, issue_id):
            self.deletes.append((domain, issue_id))
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
            "_LOGGER": types.SimpleNamespace(
                debug=lambda *_a, **_k: None, warning=lambda *_a, **_k: None
            ),
            "DOMAIN": "ecovent_v2",
            "hardware_profile_mismatch_state": hardware_profile_mismatch_state,
            "hardware_profile_mismatch_issue_url": hardware_profile_mismatch_issue_url,
            "unsupported_optional_poll_parameter_summary": (
                unsupported_optional_poll_parameter_summary
            ),
        }
        exec(
            compile(
                ast.Module(body=_coordinator_nodes(), type_ignores=[]),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )
        self.update = namespace["_update_hardware_profile_mismatch_repair_issue"]
        self.issue_id = namespace["hardware_profile_mismatch_issue_id"]

    def _coordinator(self, fan, reported=None):
        return types.SimpleNamespace(
            _fan=fan,
            hass=object(),
            config_entry=types.SimpleNamespace(entry_id="entry-1"),
            _reported_hardware_profile_mismatch_state=reported,
            _hardware_profile_mismatch_issue_id=lambda: self.issue_id("entry-1"),
        )

    def _seed_issue(self, *, dismissed_version=None, param_ids=None):
        data = {"unsupported_optional_params": "seeded"}
        if param_ids is not None:
            data["unsupported_optional_param_ids"] = list(param_ids)
        self.issues[("ecovent_v2", self.issue_id("entry-1"))] = (
            types.SimpleNamespace(data=data, dismissed_version=dismissed_version)
        )

    def test_active_issue_resolves_when_set_clears(self):
        with patch.dict(sys.modules, self.modules):
            fan = _mismatch_fan({0x00B7})
            first = self._coordinator(fan)
            self.update(first)
            key = ("ecovent_v2", self.issue_id("entry-1"))
            self.assertIn(key, self.issues)

            cleared = self._coordinator(_mismatch_fan(set()))
            self.update(cleared)
            self.assertNotIn(key, self.issues)
            self.assertEqual(len(self.deletes), 1)

    def test_dismissed_issue_survives_transient_empty_set(self):
        with patch.dict(sys.modules, self.modules):
            self._seed_issue(
                dismissed_version="1.2.34", param_ids=ISSUE125_130_ROWS
            )
            reloaded = self._coordinator(_mismatch_fan(set()))
            self.update(reloaded)
            key = ("ecovent_v2", self.issue_id("entry-1"))
            self.assertEqual(self.deletes, [])
            self.assertIn(key, self.issues)
            self.assertEqual(
                self.issues[key].dismissed_version, "1.2.34"
            )

    def test_dismissed_issue_same_set_stays_dismissed(self):
        with patch.dict(sys.modules, self.modules):
            self._seed_issue(
                dismissed_version="1.2.34", param_ids=[0x00B7]
            )
            relearned = self._coordinator(_mismatch_fan({0x00B7}))
            self.update(relearned)
            key = ("ecovent_v2", self.issue_id("entry-1"))
            self.assertEqual(len(self.creates), 1)
            self.assertEqual(self.deletes, [])
            self.assertEqual(
                self.issues[key].dismissed_version, "1.2.34"
            )

    def test_dismissed_issue_changed_set_resurfaces(self):
        with patch.dict(sys.modules, self.modules):
            self._seed_issue(
                dismissed_version="1.2.34", param_ids=[0x00B7]
            )
            changed = self._coordinator(_mismatch_fan({0x00B7, 0x0083}))
            self.update(changed)
            key = ("ecovent_v2", self.issue_id("entry-1"))
            self.assertEqual(len(self.deletes), 1)
            self.assertEqual(len(self.creates), 1)
            self.assertIn(key, self.issues)
            self.assertIsNone(self.issues[key].dismissed_version)

    def test_dismissed_issue_without_stored_ids_stays_dismissed(self):
        with patch.dict(sys.modules, self.modules):
            self._seed_issue(dismissed_version="1.2.34", param_ids=None)
            relearned = self._coordinator(_mismatch_fan({0x00B7}))
            self.update(relearned)
            key = ("ecovent_v2", self.issue_id("entry-1"))
            self.assertEqual(self.deletes, [])
            self.assertEqual(
                self.issues[key].dismissed_version, "1.2.34"
            )


if __name__ == "__main__":
    unittest.main()

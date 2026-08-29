"""Static regressions for issue #35 follow-ups."""

from pathlib import Path
import ast
import asyncio
import importlib.util
import json
import sys
import types
import unittest
from unittest.mock import patch


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
FAN_PATH = COMPONENT_PATH / "fan.py"
CONFIG_FLOW_PATH = COMPONENT_PATH / "config_flow.py"
FRONTEND_PATH = COMPONENT_PATH / "frontend.py"
INIT_PATH = COMPONENT_PATH / "__init__.py"
NUMBER_PATH = COMPONENT_PATH / "number.py"
SENSOR_PATH = COMPONENT_PATH / "sensor.py"
SWITCH_PATH = COMPONENT_PATH / "switch.py"
SELECT_PATH = COMPONENT_PATH / "select.py"
BINARY_SENSOR_PATH = COMPONENT_PATH / "binary_sensor.py"
SENSOR_SPECS_PATH = COMPONENT_PATH / "sensor_specs.py"
STRINGS_PATH = COMPONENT_PATH / "strings.json"
TRANSLATIONS_PATH = COMPONENT_PATH / "translations"
FRONTEND_TEST_PACKAGE = "ecovent_v2_frontend_test"


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


def _module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_frontend_stubs():
    class StaticPathConfig:
        def __init__(self, url_path, path, cache_headers=True):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    _module("homeassistant")
    _module("homeassistant.components")
    _module(
        "homeassistant.components.frontend",
        add_extra_js_url=lambda hass, url: None,
    )
    _module(
        "homeassistant.components.http",
        StaticPathConfig=StaticPathConfig,
    )
    _module("homeassistant.core", HomeAssistant=object)


def _load_frontend_module():
    _install_frontend_stubs()

    package = types.ModuleType(FRONTEND_TEST_PACKAGE)
    package.__path__ = [str(COMPONENT_PATH)]
    sys.modules[FRONTEND_TEST_PACKAGE] = package

    module_name = f"{FRONTEND_TEST_PACKAGE}.frontend"
    spec = importlib.util.spec_from_file_location(module_name, FRONTEND_PATH)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = FRONTEND_TEST_PACKAGE
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeFrontendHttp:
    def __init__(self, failures=0):
        self.calls = 0
        self.active_calls = 0
        self.max_active_calls = 0
        self.failures = failures

    async def async_register_static_paths(self, paths):
        self.calls += 1
        self.active_calls += 1
        self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            await asyncio.sleep(0)
            if self.failures:
                self.failures -= 1
                raise RuntimeError("static path registration failed")
            await asyncio.sleep(0)
        finally:
            self.active_calls -= 1


class _FakeFrontendHass:
    def __init__(self, failures=0):
        self.data = {}
        self.http = _FakeFrontendHttp(failures=failures)
        self.executor_calls = 0

    async def async_add_executor_job(self, func, *args):
        self.executor_calls += 1
        await asyncio.sleep(0)
        return func(*args)


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

    def test_frontend_registration_serializes_concurrent_callers(self):
        async def run_test():
            frontend = _load_frontend_module()
            hass = _FakeFrontendHass()
            with patch.object(frontend, "add_extra_js_url") as add_extra_js_url:
                await asyncio.gather(
                    frontend.async_register_frontend(hass),
                    frontend.async_register_frontend(hass),
                )

            self.assertEqual(hass.http.calls, 1)
            self.assertEqual(hass.http.max_active_calls, 1)
            self.assertEqual(hass.executor_calls, 1)
            add_extra_js_url.assert_called_once()
            self.assertTrue(hass.data[frontend._REGISTERED_KEY])

        asyncio.run(run_test())

    def test_frontend_registration_retries_after_failure(self):
        async def run_test():
            frontend = _load_frontend_module()
            hass = _FakeFrontendHass(failures=1)
            with patch.object(frontend, "add_extra_js_url") as add_extra_js_url:
                with self.assertRaises(RuntimeError):
                    await frontend.async_register_frontend(hass)

                self.assertIsNot(hass.data.get(frontend._REGISTERED_KEY), True)

                await frontend.async_register_frontend(hass)

            self.assertEqual(hass.http.calls, 2)
            self.assertEqual(hass.executor_calls, 1)
            add_extra_js_url.assert_called_once()
            self.assertTrue(hass.data[frontend._REGISTERED_KEY])

        asyncio.run(run_test())

    def test_direct_speed_change_is_live_fan_control(self):
        tree = _tree(FAN_PATH)
        turn_on = _class_method(tree, "VentoExpertFan", "async_turn_on")
        set_percentage = _class_method(tree, "VentoExpertFan", "async_set_percentage")
        set_preset = _class_method(tree, "VentoExpertFan", "async_set_preset_mode")

        self.assertTrue(
            any(
                len(call.args) >= 3
                and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(turn_on, "set_percentage")
            )
        )
        self.assertTrue(
            any(
                len(call.args) >= 3
                and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(set_percentage, "set_percentage")
            )
        )
        self.assertTrue(
            any(
                len(call.args) >= 3
                and isinstance(call.args[2], ast.Constant)
                and call.args[2].value is True
                for call in _executor_calls(set_preset, "set_preset_mode")
            )
        )

    def test_executor_jobs_do_not_use_keyword_arguments(self):
        tree = _tree(FAN_PATH)

        executor_calls_with_keywords = [
            call.lineno
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "async_add_executor_job"
            and call.keywords
        ]

        self.assertEqual(executor_calls_with_keywords, [])

    def test_unchanged_fan_services_return_before_executor_job(self):
        tree = _tree(FAN_PATH)
        source = FAN_PATH.read_text()

        methods = [
            ("async_turn_off", "self._fan.state == \"off\"", "async_add_executor_job"),
            (
                "async_set_preset_mode",
                "self._is_preset_mode_unchanged(preset_mode)",
                "async_add_executor_job",
            ),
            (
                "async_set_percentage",
                "percentage <= 0",
                "async_add_executor_job",
            ),
        ]

        for method_name, guard, executor in methods:
            with self.subTest(method=method_name):
                method = _class_method(tree, "VentoExpertFan", method_name)
                method_source = ast.get_source_segment(source, method)

                self.assertIn(guard, method_source)
                self.assertLess(
                    method_source.index(guard),
                    method_source.index(executor),
                )

        set_preset = ast.get_source_segment(
            source, _class_method(tree, "VentoExpertFan", "async_set_preset_mode")
        )
        set_percentage = ast.get_source_segment(
            source, _class_method(tree, "VentoExpertFan", "async_set_percentage")
        )

        self.assertLess(
            set_preset.index("set_silent_preset_mode(None)"),
            set_preset.index("return"),
        )
        preset_guard = ast.get_source_segment(
            source, _class_method(tree, "VentoExpertFan", "_is_preset_mode_unchanged")
        )
        self.assertIn("target_percentage = self._silent_preset_percentage(preset_mode)", preset_guard)
        self.assertIn(
            "self._fan.man_speed == max(0, min(100, target_percentage))",
            preset_guard,
        )
        self.assertNotIn("self.coordinator.silent_preset_mode == preset_mode", preset_guard)
        self.assertIn("set_silent_preset_mode(preset_mode)", set_preset)
        self.assertLess(
            set_preset.index("set_silent_preset_mode(preset_mode)"),
            set_preset.index("return"),
        )
        self.assertIn("not self._fan.uses_operating_mode_presets", set_percentage)
        self.assertIn(
            "percentage > 0 or self._silent_mode_controls_manual_speed",
            set_percentage,
        )
        self.assertLess(
            set_percentage.index("percentage <= 0"),
            set_percentage.index("return"),
        )
        self.assertLess(
            set_percentage.index("percentage <= 0"),
            set_percentage.index('set_silent_preset_mode("manual")'),
        )
        self.assertLess(
            set_percentage.index('set_silent_preset_mode("manual")'),
            set_percentage.index("async_write_ha_state()"),
        )
        self.assertLess(
            set_percentage.index("async_write_ha_state()"),
            set_percentage.rindex("return"),
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
        self.assertIn('fan.id + "_weekly_schedule_state"', init_source)
        self.assertIn("hidden_by=None", init_source)
        self.assertIn("hidden_by == er.RegistryEntryHider.INTEGRATION", init_source)
        self.assertNotIn('f"switch.{device_slug}_weekly_schedule"', init_source)

    def test_unsupported_optional_entities_are_hidden_not_removed(self):
        init_source = INIT_PATH.read_text()
        tree = _tree(INIT_PATH)
        helper = ast.get_source_segment(
            init_source,
            _module_function(tree, "_async_update_unsupported_optional_poll_entities"),
        )

        self.assertIn("hidden_by=er.RegistryEntryHider.INTEGRATION", helper)
        self.assertIn("hidden_by=None", helper)
        self.assertIn('fan.id + "_schedule"', helper)
        self.assertNotIn("async_remove", helper)

    def test_unsupported_optional_entities_remain_live_and_resync(self):
        init_source = INIT_PATH.read_text()
        init_tree = _tree(INIT_PATH)
        setup = ast.get_source_segment(
            init_source,
            _module_function(init_tree, "async_setup_entry"),
        )
        register = ast.get_source_segment(
            init_source,
            _module_function(init_tree, "_async_register_optional_poll_entity_sync"),
        )

        for path in (
            SENSOR_PATH,
            BINARY_SENSOR_PATH,
            SWITCH_PATH,
            NUMBER_PATH,
            SELECT_PATH,
        ):
            self.assertIn("profile_has_entity_requirements", path.read_text())

        self.assertIn("coordinator.async_add_listener", register)
        self.assertIn("entry.async_on_unload", register)
        self.assertIn("_async_sync_entity_registry()", register)
        self.assertIn("if not coordinator.last_update_success", register)
        self.assertIn("async_schedule_reload(entry.entry_id)", register)
        self.assertIn("current_identity != loaded_identity", register)
        self.assertIn("reload_requested", register)
        self.assertLess(
            register.index("if not coordinator.last_update_success"),
            register.index("_async_update_unsupported_optional_poll_entities"),
        )
        self.assertGreater(
            setup.index("_async_register_optional_poll_entity_sync"),
            setup.index("async_forward_entry_setups"),
        )

    def test_optional_entity_sync_waits_for_success_and_reloads_identity(self):
        function = _module_function(
            _tree(INIT_PATH), "_async_register_optional_poll_entity_sync"
        )
        namespace = {
            "HomeAssistant": object,
            "ConfigEntry": object,
            "EcoVentCoordinator": object,
        }
        registry = object()
        namespace["er"] = types.SimpleNamespace(async_get=lambda _hass: registry)
        namespace["_LOGGER"] = types.SimpleNamespace(info=lambda *_args: None)
        sync_calls = []
        namespace["_async_update_unsupported_optional_poll_entities"] = (
            lambda actual_registry, fan: sync_calls.append(
                (actual_registry, fan.unsupported_optional_poll_parameter_ids())
            )
        )
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                str(INIT_PATH),
                "exec",
            ),
            namespace,
        )
        register = namespace["_async_register_optional_poll_entity_sync"]

        class Fan:
            profile_key = "vento"
            _unit_type_id = 0x0500
            firmware = "0.5 2021-10-04"
            unsupported = frozenset()

            def unsupported_optional_poll_parameter_ids(self):
                return self.unsupported

        class Coordinator:
            def __init__(self):
                self._fan = Fan()
                self.last_update_success = True
                self.listener = None

            def async_add_listener(self, listener):
                self.listener = listener
                return lambda: None

        class Entry:
            entry_id = "entry-1"

            def async_on_unload(self, _unload):
                return None

        reloads = []
        hass = types.SimpleNamespace(
            config_entries=types.SimpleNamespace(
                async_schedule_reload=lambda entry_id: reloads.append(entry_id)
            )
        )
        coordinator = Coordinator()
        register(hass, Entry(), coordinator)

        self.assertEqual(sync_calls, [(registry, frozenset())])
        coordinator._fan.unsupported = frozenset({0x003A})
        coordinator.listener()
        self.assertEqual(sync_calls[-1], (registry, frozenset({0x003A})))

        coordinator.last_update_success = False
        coordinator._fan.firmware = "0.6 2021-05-17"
        coordinator.listener()
        self.assertEqual(reloads, [])

        coordinator.last_update_success = True
        coordinator.listener()
        coordinator.listener()
        self.assertEqual(reloads, ["entry-1"])

    def test_hardware_profile_repairs_issue_is_unloaded_cleanly(self):
        init_source = INIT_PATH.read_text()
        coordinator_source = (COMPONENT_PATH / "coordinator.py").read_text()
        init_tree = _tree(INIT_PATH)
        unload = ast.get_source_segment(
            init_source,
            _module_function(init_tree, "async_unload_entry"),
        )

        self.assertIn("async_delete_hardware_profile_mismatch_issue", unload)
        self.assertIn("except Exception as err", unload)
        self.assertLess(
            unload.index("except Exception as err"),
            unload.index("coordinator = hass.data"),
        )
        self.assertIn("hardware_profile_mismatch_issue_id", coordinator_source)
        self.assertIn(
            '"unsupported_optional_params": unsupported_params', coordinator_source
        )
        self.assertNotIn('"unsupported_optional_params": list(', coordinator_source)
        repair_method = ast.get_source_segment(
            coordinator_source,
            _class_method(
                _tree(COMPONENT_PATH / "coordinator.py"),
                "EcoVentCoordinator",
                "_update_hardware_profile_mismatch_repair_issue",
            ),
        )
        self.assertIn("except Exception as err", repair_method)
        self.assertGreater(
            repair_method.rindex(
                "self._reported_hardware_profile_mismatch_state = mismatch_state"
            ),
            repair_method.index("ir.async_create_issue"),
        )

    def test_hardware_profile_repair_failure_does_not_poison_dedupe(self):
        coordinator_path = COMPONENT_PATH / "coordinator.py"
        method = _class_method(
            _tree(coordinator_path),
            "EcoVentCoordinator",
            "_update_hardware_profile_mismatch_repair_issue",
        )
        namespace = {
            "hardware_profile_mismatch_state": lambda _fan: (
                "vento",
                0x0500,
                "0.5 2021-10-04",
                frozenset({0x0083}),
            ),
            "unsupported_optional_poll_parameter_summary": (
                lambda _fan, _unsupported: "0x0083 (unknown)"
            ),
            "hardware_profile_mismatch_issue_url": (
                lambda _fan, _unsupported: "https://example.invalid/issue"
            ),
            "async_delete_hardware_profile_mismatch_issue": lambda *_args: None,
            "DOMAIN": "ecovent_v2",
            "_LOGGER": types.SimpleNamespace(
                debug=lambda *_args, **_kwargs: None,
                warning=lambda *_args, **_kwargs: None,
            ),
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(coordinator_path),
                "exec",
            ),
            namespace,
        )
        update_repair = namespace["_update_hardware_profile_mismatch_repair_issue"]

        attempts = []
        issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")
        issue_registry.IssueSeverity = types.SimpleNamespace(WARNING="warning")

        def async_create_issue(*_args, **_kwargs):
            attempts.append("create")
            if len(attempts) == 1:
                raise RuntimeError("transient registry failure")

        issue_registry.async_create_issue = async_create_issue
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.__path__ = []
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.__path__ = []
        helpers.issue_registry = issue_registry
        fan = types.SimpleNamespace(
            name="Test fan",
            unit_type="Vento",
            profile_key="vento",
            _unit_type_id=0x0500,
        )
        coordinator = types.SimpleNamespace(
            _fan=fan,
            _reported_hardware_profile_mismatch_state=None,
            hass=object(),
            config_entry=types.SimpleNamespace(entry_id="entry-1"),
            _hardware_profile_mismatch_issue_id=lambda: "repair-1",
        )
        modules = {
            "homeassistant": homeassistant,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.issue_registry": issue_registry,
        }
        with patch.dict(sys.modules, modules):
            update_repair(coordinator)
            self.assertIsNone(
                coordinator._reported_hardware_profile_mismatch_state
            )
            update_repair(coordinator)

        self.assertEqual(attempts, ["create", "create"])
        self.assertEqual(
            coordinator._reported_hardware_profile_mismatch_state,
            ("vento", 0x0500, "0.5 2021-10-04", frozenset({0x0083})),
        )

    def test_setup_failure_closes_and_removes_coordinator(self):
        init_tree = _tree(INIT_PATH)
        close_coordinator = _module_function(init_tree, "_async_close_coordinator")
        setup_entry = _module_function(init_tree, "async_setup_entry")
        namespace = {
            "HomeAssistant": object,
            "ConfigEntry": object,
            "EcoVentCoordinator": object,
            "CONF_IP_ADDRESS": "ip_address",
            "CONF_PORT": "port",
            "CONF_PASSWORD": "password",
            "CONF_NAME": "name",
            "UPDATE_INTERVAL": "update_interval",
            "CONF_AUTO_CLOCK_SYNC": "auto_clock_sync",
            "CONF_TRANSPORT": "transport",
            "TRANSPORT_BGCP_UDP": "bgcp_udp",
            "DOMAIN": "ecovent_v2",
            "_LOGGER": types.SimpleNamespace(warning=lambda *_args, **_kwargs: None),
        }
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(
                        body=[close_coordinator, setup_entry],
                        type_ignores=[],
                    )
                ),
                str(INIT_PATH),
                "exec",
            ),
            namespace,
        )

        closed = []

        class Coordinator:
            def __init__(self, _hass, _entry, update_seconds):
                self.update_seconds = update_seconds
                self._fan = types.SimpleNamespace(close=lambda: closed.append("close"))

            async def async_config_entry_first_refresh(self):
                return None

        async def fail_frontend(_hass):
            raise RuntimeError("frontend setup failed")

        namespace["EcoVentCoordinator"] = Coordinator
        namespace["async_register_frontend"] = fail_frontend
        hass = types.SimpleNamespace(
            data={},
            async_add_executor_job=lambda callback: asyncio.to_thread(callback),
        )
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"update_interval": 30},
            runtime_data=None,
        )

        with self.assertRaisesRegex(RuntimeError, "frontend setup failed"):
            asyncio.run(namespace["async_setup_entry"](hass, entry))

        self.assertEqual(closed, ["close"])
        self.assertNotIn("entry-1", hass.data.get("ecovent_v2", {}))

    def test_switch_none_state_remains_unknown(self):
        switch_source = SWITCH_PATH.read_text()
        tree = _tree(SWITCH_PATH)
        is_on = ast.get_source_segment(
            switch_source, _class_method(tree, "VentoSwitch", "is_on")
        )

        self.assertIn("value = self._method()", is_on)
        self.assertIn("None if value is None else value == \"on\"", is_on)

    def test_weekly_schedule_summary_none_state_remains_unknown(self):
        sensor_source = SENSOR_PATH.read_text()
        tree = _tree(SENSOR_PATH)
        native_value = ast.get_source_segment(
            sensor_source,
            _class_method(tree, "WeeklyScheduleSummarySensor", "native_value"),
        )
        attrs = ast.get_source_segment(
            sensor_source,
            _class_method(
                tree, "WeeklyScheduleSummarySensor", "extra_state_attributes"
            ),
        )

        self.assertIn("state = self._fan.weekly_schedule_state", native_value)
        self.assertIn('if state == "on"', native_value)
        self.assertIn('if state == "off"', native_value)
        self.assertIn("return None", native_value)
        self.assertIn("enabled = state == \"on\" if state in", attrs)
        self.assertIn('"weekly_schedule_enabled": enabled', attrs)

    def test_reported_legacy_entity_migrations_are_listed(self):
        init_source = INIT_PATH.read_text()

        self.assertIn('fan.id + "_speed1"', init_source)
        self.assertIn("stable_entity_id(", init_source)
        self.assertIn('"fan1_speed"', init_source)

    def test_entity_id_migration_preserves_user_custom_ids(self):
        init_source = INIT_PATH.read_text()

        self.assertIn("_entity_id_matches_generated_suffix(", init_source)
        self.assertIn("user-customized", init_source)
        self.assertIn('object_tokens = object_id.split("_")', init_source)
        self.assertIn("prefix == device_slug or legacy_device_match", init_source)
        self.assertIn("_known_generated_unique_ids(", init_source)
        self.assertIn('"new_unique_id"', init_source)
        self.assertIn("has_legacy_unique_id", init_source)

    def test_entity_id_migration_and_new_entities_share_suffixes(self):
        init_source = INIT_PATH.read_text()

        self.assertIn('"analogV_treshold"', init_source)
        self.assertIn('"analogV_sensor_state"', init_source)
        self.assertGreaterEqual(init_source.count("stable_entity_id("), 8)
        self.assertIn('"analogv_treshold"', init_source)
        self.assertIn('"analogv"', init_source)
        self.assertIn('"analogV_status"', init_source)
        self.assertIn('"analogV_treshold_set"', init_source)
        self.assertIn('"analog_v_threshold"', init_source)
        self.assertIn('"analog_voltage_status"', init_source)
        self.assertIn('"analog_voltage_threshold"', init_source)
        self.assertIn('"analogv_sensor_state"', init_source)
        self.assertIn('"analog_voltage_sensor"', init_source)
        self.assertIn('"humidity_threshold_set"', init_source)
        self.assertIn('"fan_1_speed"', init_source)
        self.assertIn('f"{fan_name} {fan_id}"', init_source)

        for path in (
            NUMBER_PATH,
            SWITCH_PATH,
            SENSOR_PATH,
            SELECT_PATH,
            BINARY_SENSOR_PATH,
        ):
            source = path.read_text()

            self.assertIn("StableObjectIdMixin", source, path.name)
            self.assertIn("clean_object_id_suffix", source, path.name)

        naming_source = (COMPONENT_PATH / "entity_naming.py").read_text()
        self.assertIn('f"{slugify(device_name)}_', naming_source)

    def test_alarm_status_keeps_problem_binary_sensor(self):
        binary_sensor_source = BINARY_SENSOR_PATH.read_text()
        init_source = INIT_PATH.read_text()

        self.assertIn('"_alarm_status"', binary_sensor_source)
        self.assertIn('"Device problem"', binary_sensor_source)
        self.assertIn('"alarm_status"', binary_sensor_source)
        self.assertIn("BinarySensorDeviceClass.PROBLEM", binary_sensor_source)
        self.assertIn('on_values=("alarm", "warning")', binary_sensor_source)
        self.assertNotIn('fan.id + "_alarm_status"', init_source)

    def test_silent_mode_keeps_manual_speed_facade(self):
        config_source = CONFIG_FLOW_PATH.read_text()
        fan_source = FAN_PATH.read_text()
        tree = _tree(FAN_PATH)

        self.assertIn("CONF_SILENT_MODE", config_source)
        self.assertIn("default=False", config_source)
        self.assertIn("silent_preset_mode", fan_source)
        self.assertIn("_set_silent_manual_percentage", fan_source)
        self.assertIn("_set_parameters_if_changed", fan_source)
        self.assertIn("entering_manual_mode = self._fan.speed != \"manual\"", fan_source)
        self.assertIn("include_extra_write_parameters=entering_manual_mode", fan_source)
        self.assertIn("audible_write_command_count", fan_source)
        self.assertIn("steady-state silent manual speed update", fan_source)
        self.assertIn("This protocol ignores an off -> on transition", fan_source)

        silent_targets = _class_method(tree, "VentoExpertFan", "_silent_manual_targets")
        set_airflow_mode = _class_method(tree, "VentoExpertFan", "set_airflow_mode")
        silent_target_constants = {
            item.value
            for item in ast.walk(silent_targets)
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }
        self.assertNotIn("humidity_sensor_state", silent_target_constants)
        self.assertNotIn("relay_sensor_state", silent_target_constants)
        self.assertNotIn("analogV_sensor_state", silent_target_constants)
        self.assertIn("speed", silent_target_constants)
        self.assertIn("man_speed", silent_target_constants)
        self.assertTrue(
            any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "_set_silent_manual_percentage"
                for call in ast.walk(set_airflow_mode)
            )
        )

    def test_entity_writes_fail_closed_on_transport_failure(self):
        cases = (
            (SWITCH_PATH, "VentoSwitch", ("async_turn_on", "async_turn_off")),
            (NUMBER_PATH, "VentoNumber", ("async_set_native_value",)),
            (SELECT_PATH, "VentoSelect", ("async_select_option",)),
        )

        for path, class_name, method_names in cases:
            tree = _tree(path)
            source = path.read_text()
            for method_name in method_names:
                with self.subTest(path=path.name, method=method_name):
                    method = _class_method(tree, class_name, method_name)
                    method_source = ast.get_source_segment(source, method)
                    self.assertIn("success = await", method_source)
                    self.assertIn("if not success", method_source)
                    self.assertIn("raise RuntimeError", method_source)

        switch_source = SWITCH_PATH.read_text()
        for method_name in ("async_turn_on", "async_turn_off"):
            method_source = ast.get_source_segment(
                switch_source,
                _class_method(_tree(SWITCH_PATH), "VentoSwitch", method_name),
            )
            self.assertIn("await self.coordinator.async_refresh()", method_source)
            self.assertNotIn("self.async_write_ha_state()", method_source)

    def test_auto_boost_trigger_switch_names_are_explicit(self):
        switch_source = SWITCH_PATH.read_text()
        select_source = SELECT_PATH.read_text()
        binary_sensor_source = BINARY_SENSOR_PATH.read_text()
        number_source = NUMBER_PATH.read_text()

        self.assertIn('"Boost humidity"', switch_source)
        self.assertIn('"Boost relay sensor"', switch_source)
        self.assertIn('"Boost analog voltage"', switch_source)
        self.assertIn('"Boost mode on humidity"', select_source)
        self.assertIn('"Boost airflow on humidity"', select_source)
        self.assertIn('"Airflow (raw)"', select_source)
        self.assertIn('"Boost humidity active"', binary_sensor_source)
        self.assertIn('"Boost relay sensor active"', binary_sensor_source)
        self.assertIn('"Boost analog voltage active"', binary_sensor_source)
        self.assertIn('"Boost humidity threshold"', number_source)
        self.assertIn('"Boost analog voltage threshold"', number_source)
        self.assertNotIn('"Humidity sensor"', switch_source)
        self.assertNotIn('"Relay sensor"', switch_source)
        self.assertNotIn('"Analog voltage sensor"', switch_source)
        self.assertNotIn('"Humidity status"', binary_sensor_source)
        self.assertNotIn('"Relay status"', binary_sensor_source)
        self.assertNotIn('"Analog voltage status"', binary_sensor_source)
        self.assertNotIn('"Boost active on humidity"', binary_sensor_source)
        self.assertNotIn('"Boost active on relay sensor"', binary_sensor_source)
        self.assertNotIn('"Boost active on analog voltage"', binary_sensor_source)
        self.assertNotIn('"Humidity sensor mode"', select_source)
        self.assertNotIn('"Humidity airflow"', select_source)

    def test_sort_friendly_labels_start_with_their_group(self):
        number_source = NUMBER_PATH.read_text()
        sensor_source = SENSOR_SPECS_PATH.read_text()
        switch_source = SWITCH_PATH.read_text()
        select_source = SELECT_PATH.read_text()

        self.assertIn('"Speed manual"', number_source)
        self.assertIn('"Speed 1 supply low"', number_source)
        self.assertIn('"Speed 1 exhaust low"', number_source)
        self.assertIn('"Speed 2 supply medium"', number_source)
        self.assertIn('"Speed 2 exhaust medium"', number_source)
        self.assertIn('"Speed 3 supply high"', number_source)
        self.assertIn('"Speed 3 exhaust high"', number_source)
        self.assertIn('"Speed setpoint interval ventilation"', number_source)
        self.assertIn('"Speed fan"', sensor_source)
        self.assertIn('"RTC timestamp"', sensor_source)
        self.assertIn('"rtc_timestamp"', sensor_source)
        self.assertNotIn('"RTC time"', sensor_source)
        self.assertNotIn('"RTC date"', sensor_source)
        self.assertIn('"Timer night mode"', sensor_source)
        self.assertIn('"Timer party mode"', sensor_source)
        self.assertIn('"Boost analog voltage level"', sensor_source)
        self.assertIn('"Runtime machine hours"', sensor_source)
        self.assertIn('"Weekly schedule speed"', sensor_source)
        self.assertIn('"Mode interval ventilation"', switch_source)
        self.assertIn('"Trigger on motion"', switch_source)
        self.assertIn('"Airflow on motion/light"', select_source)
        self.assertIn('"Trigger mode on air quality"', select_source)
        self.assertIn('"Timer mode"', select_source)

    def test_preset_translations_group_boost_modes(self):
        translation_paths = [STRINGS_PATH, *TRANSLATIONS_PATH.glob("*.json")]

        for path in translation_paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text())
                states = data["entity"]["fan"]["vent"]["state_attributes"][
                    "preset_mode"
                ]["state"]
                self.assertNotIn("Humidity auto", states.values())
                self.assertNotIn("Humidity manual", states.values())
                self.assertNotIn("Авто по влажности", states.values())
                self.assertNotIn("Влажность вручную", states.values())
                self.assertTrue(states["humidity_trigger"].startswith(("Boost", "Ф")))

    def test_config_flow_translations_cover_reconfigure_form(self):
        translation_paths = [STRINGS_PATH, *TRANSLATIONS_PATH.glob("*.json")]
        expected_fields = {
            "ip_address",
            "port",
            "password",
            "name",
            "update_interval",
            "auto_clock_sync",
            "silent_mode",
        }

        for path in translation_paths:
            with self.subTest(path=path.name):
                steps = json.loads(path.read_text())["config"]["step"]

                for step in ("user", "reconfigure"):
                    labels = steps[step]["data"]
                    self.assertTrue(expected_fields <= labels.keys())
                    for key in expected_fields:
                        self.assertNotEqual(labels[key], key)


if __name__ == "__main__":
    unittest.main()

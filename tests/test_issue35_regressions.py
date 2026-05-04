"""Static regressions for issue #35 follow-ups."""

from pathlib import Path
import ast
import json
import unittest


COMPONENT_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"
)
FAN_PATH = COMPONENT_PATH / "fan.py"
CONFIG_FLOW_PATH = COMPONENT_PATH / "config_flow.py"
FRONTEND_PATH = COMPONENT_PATH / "frontend.py"
INIT_PATH = COMPONENT_PATH / "__init__.py"
SWITCH_PATH = COMPONENT_PATH / "switch.py"
SELECT_PATH = COMPONENT_PATH / "select.py"
BINARY_SENSOR_PATH = COMPONENT_PATH / "binary_sensor.py"
NUMBER_PATH = COMPONENT_PATH / "number.py"
SENSOR_SPECS_PATH = COMPONENT_PATH / "sensor_specs.py"
STRINGS_PATH = COMPONENT_PATH / "strings.json"
TRANSLATIONS_PATH = COMPONENT_PATH / "translations"


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
        self.assertNotIn('f"switch.{device_slug}_weekly_schedule"', init_source)

    def test_reported_legacy_entity_migrations_are_listed(self):
        init_source = INIT_PATH.read_text()

        self.assertIn('fan.id + "_speed1"', init_source)
        self.assertIn('f"sensor.{device_slug}_fan_1_speed"', init_source)

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
        self.assertTrue(
            any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "_set_silent_manual_percentage"
                for call in ast.walk(set_airflow_mode)
            )
        )

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


if __name__ == "__main__":
    unittest.main()

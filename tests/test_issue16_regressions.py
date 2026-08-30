"""Regression tests for issue #16 schedule polling behavior."""

from pathlib import Path
import ast
import asyncio
import logging
import types
import unittest

from ecovent_test_helpers import Fan


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
        self.assertIn("profile_supports_parameter", should_refresh_source)
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

    def test_schedule_poll_reprobes_a_profile_row_learned_unsupported(self):
        should_refresh = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "_should_refresh_schedule_week",
        )
        namespace = {"_LOGGER": logging.getLogger(__name__)}
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(body=[should_refresh], type_ignores=[])
                ),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )
        fan = Fan("192.0.2.1")
        fan.unit_type = "1100"
        fan.weekly_schedule_state = "00"
        fan._unsupported_optional_poll_params.add(0x0077)
        coordinator = types.SimpleNamespace(
            _fan=fan,
            _weekly_schedule={},
            updateCounter=1,
        )

        self.assertFalse(fan.supports_parameter("weekly_schedule_setup"))
        self.assertTrue(fan.profile_supports_parameter("weekly_schedule_setup"))
        self.assertTrue(namespace["_should_refresh_schedule_week"](coordinator))

    def test_bgcp_fan_declares_transport_used_by_schedule_preflight(self):
        self.assertEqual(Fan("192.0.2.1").transport, "bgcp_udp")

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
        load_call_lineno = min(
            node.lineno
            for node in calls
            if isinstance(node.func, ast.Attribute)
            and node.func.attr == "async_add_executor_job"
            and any(
                isinstance(arg, ast.Attribute) and arg.attr == "_load_schedule_days"
                for arg in node.args
            )
        )
        prepare_call_lineno = min(
            node.lineno
            for node in calls
            if isinstance(node.func, ast.Name)
            and node.func.id == "prepare_day_writes"
        )

        self.assertLess(load_call_lineno, prepare_call_lineno)
        self.assertTrue(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "read_weekly_schedule_day"
                for node in ast.walk(load_schedule_days)
            )
        )

    def test_optional_schedule_read_error_preserves_cache_and_core_update(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "_load_schedule_days",
        )
        namespace = {
            "_LOGGER": types.SimpleNamespace(warning=lambda *_args: None),
            "validate_schedule_day": lambda _records: None,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )
        cached_day = {period: f"old-{period}" for period in range(1, 5)}
        fresh_day = {period: f"new-{period}" for period in range(1, 5)}

        class Fan:
            name = "Test fan"

            def read_weekly_schedule_day(self, day):
                if day == 1:
                    raise OSError("schedule timeout")
                return fresh_day

        coordinator = types.SimpleNamespace(
            _fan=Fan(),
            _weekly_schedule={1: cached_day},
        )
        loaded_days = namespace["_load_schedule_days"](coordinator, [1, 2])

        self.assertIs(coordinator._weekly_schedule[1], cached_day)
        self.assertIs(coordinator._weekly_schedule[2], fresh_day)
        self.assertEqual(loaded_days, {2})

    def test_schedule_write_aborts_when_prewrite_readback_is_stale(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        events = []

        def changed_records(*_args):
            events.append("diff")
            return []

        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1},
            "changed_schedule_records": changed_records,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            weekly_schedule_state = "off"
            name = "Test fan"

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def set_param(self, *_args):
                events.append("write")
                return True

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={1: {period: "stale" for period in range(1, 5)}},
            _load_schedule_days=lambda _days: set(),
            schedule_day_records=lambda _day: self.fail("stale cache was diffed"),
            async_update_listeners=lambda: events.append("listeners"),
        )

        with self.assertRaisesRegex(RuntimeError, "Failed to refresh"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    weekly_schedule_enabled=True,
                    days=[{"day": "Monday", "periods": []}],
                )
            )

        self.assertEqual(events, [])

        coordinator._load_schedule_days = lambda _days: {1}
        coordinator.schedule_day_records = lambda _day: {}
        asyncio.run(
            namespace["async_write_schedule"](
                coordinator,
                days=[{"day": "Monday", "periods": []}],
            )
        )
        self.assertEqual(events, ["diff", "listeners"])

    def test_schedule_payload_validation_precedes_state_write(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        events = []
        unsupported_record = types.SimpleNamespace(period=1, speed="speed_5")

        def changed_records(*_args):
            events.append("validate")
            return [unsupported_record]

        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1, "Tuesday": 2},
            "changed_schedule_records": changed_records,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            name = "Vento"
            weekly_schedule_state = "off"
            device_profile = types.SimpleNamespace(
                schedule_speed_modes=("standby", "low", "medium", "high")
            )

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def set_param(self, *_args):
                events.append("write-state")
                return True

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={1: {period: object() for period in range(1, 5)}},
            _load_schedule_days=lambda days: set(days),
            schedule_day_records=lambda day: coordinator._weekly_schedule[day],
            async_update_listeners=lambda: events.append("listeners"),
        )

        with self.assertRaisesRegex(ValueError, "not supported"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    selected_day="Tuesday",
                    weekly_schedule_enabled=True,
                    days=[
                        {
                            "day": "Monday",
                            "periods": [{"period": 1, "speed": "Speed 5"}],
                        }
                    ],
                )
            )

        self.assertEqual(events, ["validate"])
        self.assertEqual(coordinator._schedule_day, 1)

        asyncio.run(
            namespace["async_write_schedule"](
                coordinator,
                selected_day="Tuesday",
            )
        )
        self.assertEqual(coordinator._schedule_day, 2)
        self.assertEqual(events, ["validate", "listeners"])

    def test_bgcp_final_period_is_validated_before_any_schedule_write(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        events = []
        current = {
            period: types.SimpleNamespace(
                period=period,
                speed="low",
                end_hour=0 if period == 4 else period * 4,
                end_minute=0,
            )
            for period in range(1, 5)
        }
        changed = [
            types.SimpleNamespace(
                period=1, speed="low", end_hour=5, end_minute=0
            ),
            types.SimpleNamespace(
                period=4, speed="low", end_hour=1, end_minute=0
            ),
        ]
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1},
            "changed_schedule_records": lambda *_args: changed,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            name = "Vento"
            transport = "bgcp_udp"
            weekly_schedule_state = "off"
            device_profile = types.SimpleNamespace(schedule_speed_modes=("low",))

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def write_weekly_schedule_record(self, _record):
                events.append("write")
                return True

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={1: current},
            _load_schedule_days=lambda days: set(days),
            schedule_day_records=lambda _day: current,
            async_update_listeners=lambda: events.append("listeners"),
        )

        with self.assertRaisesRegex(ValueError, "must end at midnight"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    days=[
                        {
                            "day": "Monday",
                            "periods": [
                                {"period": 1, "end": "05:00"},
                                {"period": 4, "end": "01:00"},
                            ],
                        }
                    ],
                )
            )

        self.assertEqual(events, [])

    def test_schedule_write_stops_after_device_rejects_schedule_rows(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        events = []
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1, "Tuesday": 2},
            "changed_schedule_records": lambda *_args: events.append("diff"),
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Fan:
            name = "Test fan"
            weekly_schedule_state = "off"

            def supports_parameter(self, _name):
                return False

            profile_supports_parameter = supports_parameter

            def set_param(self, *_args):
                events.append("write-state")
                return True

            def write_weekly_schedule_record(self, _record):
                events.append("write-record")
                return True

        coordinator = types.SimpleNamespace(
            _fan=Fan(),
            _schedule_day=1,
            async_update_listeners=lambda: events.append("listeners"),
        )

        with self.assertRaisesRegex(RuntimeError, "not supported"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    selected_day="Tuesday",
                    weekly_schedule_enabled=True,
                    days=[{"day": "Monday", "periods": []}],
                )
            )

        self.assertEqual(events, [])
        self.assertEqual(coordinator._schedule_day, 1)

    def test_schedule_state_change_rebuilds_writes_from_fresh_readback(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        diffs = []
        writes = []
        prepared_records = []

        def changed_records(_day, current, _payload):
            diffs.append(current[1])
            record = types.SimpleNamespace(period=1, speed="low", base=current[1])
            prepared_records.append(record)
            return [record]

        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1},
            "changed_schedule_records": changed_records,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            name = "Vento"
            weekly_schedule_state = "off"
            device_profile = types.SimpleNamespace(schedule_speed_modes=("low",))

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def set_param(self, *_args):
                writes.append("state")
                return True

            def write_weekly_schedule_record(self, record):
                writes.append(record.base)
                return True

        load_count = 0

        def load_schedule_days(days):
            nonlocal load_count
            load_count += 1
            if load_count == 2:
                coordinator._weekly_schedule[1] = {
                    period: f"fresh-{period}" for period in range(1, 5)
                }
            return set(days)

        async def refresh():
            coordinator._fan.weekly_schedule_state = "on"
            coordinator.last_update_success = True

        async def reconcile(_day):
            confirmed = dict(coordinator._weekly_schedule[1])
            confirmed[1] = prepared_records[-1]
            return confirmed

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={1: {period: f"old-{period}" for period in range(1, 5)}},
            _load_schedule_days=load_schedule_days,
            schedule_day_records=lambda day: dict(coordinator._weekly_schedule[day]),
            last_update_success=False,
            async_refresh=refresh,
            _async_reconcile_schedule_day=reconcile,
            async_update_listeners=lambda: None,
        )

        asyncio.run(
            namespace["async_write_schedule"](
                coordinator,
                weekly_schedule_enabled=True,
                days=[{"day": "Monday", "periods": [{"period": 1}]}],
            )
        )

        self.assertEqual(diffs, ["old-1", "fresh-1"])
        self.assertEqual(writes, ["state", "fresh-1"])

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

    def test_schedule_state_write_refreshes_before_listener_notification(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {},
            "changed_schedule_records": lambda *_args: [],
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        events = []

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            weekly_schedule_state = "off"
            name = "Test fan"

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def set_param(self, name, value):
                events.append(("write", name, value))
                return True

        async def refresh():
            events.append("refresh")
            coordinator._fan.weekly_schedule_state = "on"
            coordinator.last_update_success = True

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={},
            last_update_success=False,
            async_refresh=refresh,
            async_update_listeners=lambda: events.append("listeners"),
        )

        asyncio.run(
            namespace["async_write_schedule"](
                coordinator, weekly_schedule_enabled=True
            )
        )
        self.assertEqual(
            events,
            [("write", "weekly_schedule_state", "on"), "refresh", "listeners"],
        )

    def test_schedule_state_write_rejects_swallowed_refresh_failure(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {},
            "changed_schedule_records": lambda *_args: [],
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )
        events = []

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            weekly_schedule_state = "off"
            name = "Test fan"

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def set_param(self, _name, _value):
                events.append("write")
                return True

        async def refresh():
            events.append("refresh-failed-but-swallowed")

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={},
            last_update_success=False,
            async_refresh=refresh,
            async_update_listeners=lambda: events.append("listeners"),
        )

        with self.assertRaisesRegex(RuntimeError, "did not confirm"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator, weekly_schedule_enabled=True
                )
            )
        self.assertEqual(events, ["write", "refresh-failed-but-swallowed"])

    def test_schedule_record_write_requires_complete_matching_readback(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        requested = types.SimpleNamespace(period=1, speed="low", value="requested")
        actual = {
            period: types.SimpleNamespace(period=period, value="actual")
            for period in range(1, 5)
        }
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1},
            "changed_schedule_records": lambda *_args: [requested],
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            weekly_schedule_state = "off"
            name = "Test fan"
            device_profile = types.SimpleNamespace(schedule_speed_modes=("low",))

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def write_weekly_schedule_record(self, _record):
                return True

            def read_weekly_schedule_day(self, _day):
                return actual

        events = []
        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={1: {}},
            _load_schedule_days=lambda days: set(days),
            schedule_day_records=lambda _day: {},
            _async_reconcile_schedule_day=None,
            async_update_listeners=lambda: events.append("listeners"),
        )

        async def reconcile(_day):
            coordinator._weekly_schedule[1] = actual
            return actual

        coordinator._async_reconcile_schedule_day = reconcile

        with self.assertRaisesRegex(RuntimeError, "did not confirm schedule write"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    days=[{"day": "Monday", "periods": []}],
                )
            )
        self.assertEqual(coordinator._weekly_schedule[1], actual)
        self.assertEqual(events, ["listeners"])

    def test_partial_schedule_write_failure_reconciles_device_state(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "async_write_schedule",
        )
        records = [
            types.SimpleNamespace(period=1, speed="low", value="new-1"),
            types.SimpleNamespace(period=2, speed="low", value="new-2"),
        ]
        namespace = {
            "SCHEDULE_DAY_TO_INDEX": {"Monday": 1},
            "changed_schedule_records": lambda *_args: records,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )
        actual = {
            period: types.SimpleNamespace(period=period, value=f"old-{period}")
            for period in range(1, 5)
        }
        events = []

        class Hass:
            async def async_add_executor_job(self, callback, *args):
                return callback(*args)

        class Fan:
            weekly_schedule_state = "off"
            name = "Test fan"
            device_profile = types.SimpleNamespace(schedule_speed_modes=("low",))

            def supports_parameter(self, _name):
                return True

            profile_supports_parameter = supports_parameter

            def write_weekly_schedule_record(self, record):
                events.append(("write", record.period))
                if record.period == 1:
                    actual[1] = record
                    return True
                return False

        coordinator = types.SimpleNamespace(
            hass=Hass(),
            _fan=Fan(),
            _schedule_day=1,
            _weekly_schedule={
                1: {
                    period: types.SimpleNamespace(
                        period=period, value=f"old-{period}"
                    )
                    for period in range(1, 5)
                }
            },
            _load_schedule_days=lambda days: set(days),
            schedule_day_records=lambda day: dict(actual),
            _async_reconcile_schedule_day=None,
            async_update_listeners=lambda: events.append("listeners"),
        )

        async def reconcile(day):
            coordinator._weekly_schedule[day] = dict(actual)
            events.append("readback")
            return actual

        coordinator._async_reconcile_schedule_day = reconcile

        with self.assertRaisesRegex(RuntimeError, "period 2"):
            asyncio.run(
                namespace["async_write_schedule"](
                    coordinator,
                    days=[{"day": "Monday", "periods": []}],
                )
            )
        self.assertEqual(
            events,
            [("write", 1), ("write", 2), "readback", "listeners"],
        )
        self.assertIs(coordinator._weekly_schedule[1][1], records[0])

    def test_incomplete_schedule_read_preserves_last_complete_day(self):
        source = COORDINATOR_PATH.read_text()
        load_schedule_days = _class_method(
            ast.parse(source), "EcoVentCoordinator", "_load_schedule_days"
        )
        namespace = {
            "_LOGGER": logging.getLogger(__name__),
            "validate_schedule_day": lambda _records: None,
        }
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

    def test_invalid_schedule_read_preserves_last_chronological_day(self):
        method = _class_method(
            ast.parse(COORDINATOR_PATH.read_text()),
            "EcoVentCoordinator",
            "_load_schedule_days",
        )

        def validate(records):
            previous = -1
            for record in records[:3]:
                current = record.end_hour * 60 + record.end_minute
                if current <= previous:
                    raise ValueError("not chronological")
                previous = current

        namespace = {
            "_LOGGER": logging.getLogger(__name__),
            "validate_schedule_day": validate,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                str(COORDINATOR_PATH),
                "exec",
            ),
            namespace,
        )

        def records(ends):
            return {
                period: types.SimpleNamespace(
                    period=period,
                    end_hour=end // 60,
                    end_minute=end % 60,
                )
                for period, end in enumerate(ends, 1)
            }

        cached = records((360, 720, 1080, 0))
        invalid = records((600, 540, 1080, 0))
        fresh = records((420, 780, 1140, 0))
        reads = iter((invalid, fresh))
        coordinator = types.SimpleNamespace(
            _fan=types.SimpleNamespace(
                name="Test fan",
                read_weekly_schedule_day=lambda _day: next(reads),
            ),
            _weekly_schedule={1: cached},
        )

        namespace["_load_schedule_days"](coordinator, [1])
        self.assertIs(coordinator._weekly_schedule[1], cached)

        namespace["_load_schedule_days"](coordinator, [1])
        self.assertIs(coordinator._weekly_schedule[1], fresh)


if __name__ == "__main__":
    unittest.main()

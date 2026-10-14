"""Regressions for the one-time startup statistics listener lifecycle."""

import ast
import asyncio
import inspect
import unittest

from ecovent_test_helpers import COMPONENT_PATH


def _callback(function):
    function._hass_callback = True
    return function


def _load_statistics_startup_listener():
    """Load the production listener function without importing Home Assistant."""
    path = COMPONENT_PATH / "__init__.py"
    tree = ast.parse(path.read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_async_migrate_statistics_metadata_on_start"
    )
    namespace = {
        "HomeAssistant": object,
        "ConfigEntry": object,
        "EcoVentCoordinator": object,
        "EVENT_HOMEASSISTANT_STARTED": "homeassistant_started",
        "callback": _callback,
    }
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"),
        namespace,
    )
    return namespace[function.name], namespace


class _OneTimeBus:
    """Model HA removal-before-dispatch semantics and a non-idempotent remover."""

    def __init__(self):
        self.event_type = None
        self.listener = None
        self.removal_calls = 0

    def async_listen_once(self, event_type, listener):
        if not getattr(listener, "_hass_callback", False):
            raise AssertionError("Home Assistant callbacks must run in the event loop")
        self.event_type = event_type
        self.listener = listener

        def remove_listener():
            self.removal_calls += 1
            if self.listener is not listener:
                raise ValueError("listener was already removed")
            self.listener = None

        self._remove_listener = remove_listener
        return remove_listener

    def fire(self, event_type):
        if event_type != self.event_type or self.listener is None:
            return
        listener = self.listener
        self._remove_listener()
        result = listener(None)
        if inspect.isawaitable(result):
            asyncio.create_task(result)


class _HomeAssistant:
    def __init__(self, bus):
        self.bus = bus
        self.tasks = []

    def async_create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


class _ConfigEntry:
    def __init__(self):
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)

    def unload(self):
        for callback in self.unload_callbacks:
            callback()


class StatisticsStartupListenerTest(unittest.IsolatedAsyncioTestCase):
    def _harness(self):
        calls = []

        async def migrate(_hass, coordinator):
            calls.append(coordinator)

        startup_listener, namespace = _load_statistics_startup_listener()
        namespace["_async_migrate_statistics_metadata"] = migrate
        bus = _OneTimeBus()
        hass = _HomeAssistant(bus)
        entry = _ConfigEntry()
        coordinator = object()
        return startup_listener, hass, entry, coordinator, calls

    async def test_unload_after_startup_does_not_remove_fired_listener(self):
        startup_listener, hass, entry, coordinator, calls = self._harness()
        await startup_listener(hass, entry, coordinator)
        bus = hass.bus

        bus.fire("homeassistant_started")
        await asyncio.gather(*hass.tasks)
        entry.unload()

        self.assertEqual(calls, [coordinator, coordinator])
        self.assertEqual(bus.removal_calls, 1)

    async def test_unload_before_startup_cancels_listener(self):
        startup_listener, hass, entry, coordinator, calls = self._harness()
        await startup_listener(hass, entry, coordinator)
        bus = hass.bus

        entry.unload()
        bus.fire("homeassistant_started")

        self.assertEqual(calls, [coordinator])
        self.assertEqual(bus.removal_calls, 1)

    async def test_unload_during_startup_task_scheduling_does_not_race_removal(self):
        startup_listener, hass, entry, coordinator, calls = self._harness()
        await startup_listener(hass, entry, coordinator)
        bus = hass.bus

        bus.fire("homeassistant_started")
        entry.unload()
        await asyncio.gather(*hass.tasks)

        self.assertEqual(calls, [coordinator, coordinator])
        self.assertEqual(bus.removal_calls, 1)

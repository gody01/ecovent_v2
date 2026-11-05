"""One lost UDP reply must not flip availability or reload the entry (#133)."""

import asyncio
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ecovent_test_helpers import COMPONENT_PATH, Fan

ROOT = str(COMPONENT_PATH.parents[1])


class _UpdateFailed(Exception):
    pass


class _Base:
    def __init__(self, *args, **kwargs):
        pass


@pytest.fixture
def integration(monkeypatch):
    """Import the integration with Home Assistant replaced by stubs."""
    saved = {
        name: mod
        for name, mod in sys.modules.items()
        if name.startswith(("custom_components", "homeassistant", "voluptuous"))
    }
    for name in saved:
        del sys.modules[name]

    class Finder:
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in ("homeassistant", "voluptuous"):
                import importlib.machinery

                return importlib.machinery.ModuleSpec(name, self, is_package=True)

        def create_module(self, spec):
            mod = MagicMock()
            mod.__path__ = []
            mod.__name__ = spec.name
            mod.__spec__ = spec
            if spec.name == "homeassistant.helpers.update_coordinator":
                mod.DataUpdateCoordinator = _Base
                mod.UpdateFailed = _UpdateFailed
            return mod

        def exec_module(self, module):
            pass

    finder = Finder()
    monkeypatch.setattr(sys, "meta_path", [finder] + sys.meta_path)
    monkeypatch.syspath_prepend(ROOT)
    pkg = importlib.import_module("custom_components.ecovent_v2")
    coordinator = importlib.import_module("custom_components.ecovent_v2.coordinator")
    yield pkg, coordinator
    for name in list(sys.modules):
        if name.startswith(("custom_components", "homeassistant", "voluptuous")):
            del sys.modules[name]
    sys.modules.update(saved)


class _Hass:
    async def async_add_executor_job(self, func, *args):
        return func(*args)


def _coordinator(coordinator_module, results):
    coordinator = object.__new__(coordinator_module.EcoVentCoordinator)
    coordinator.hass = _Hass()
    coordinator.fan_initialized = True
    coordinator.updateCounter = 10
    coordinator._failed_polls = 0
    coordinator._fan = SimpleNamespace(
        name="fan",
        update=lambda: next(results),
        quick_update=lambda: next(results),
    )
    coordinator._update_hardware_profile_mismatch_repair_issue = lambda: None
    coordinator._update_rejected_device_value_repair_issue = lambda: None
    coordinator._should_refresh_schedule_week = lambda: False
    coordinator._auto_clock_sync = False
    return coordinator


def _poll(coordinator):
    return asyncio.run(coordinator._async_update_data())


def test_single_incomplete_poll_keeps_device_available(integration):
    _pkg, module = integration
    coordinator = _coordinator(module, iter([False, True, False, False, True]))

    _poll(coordinator)  # tolerated
    assert coordinator._failed_polls == 1
    _poll(coordinator)  # complete poll resets the counter
    assert coordinator._failed_polls == 0
    _poll(coordinator)
    _poll(coordinator)
    assert coordinator._failed_polls == 2
    _poll(coordinator)
    assert coordinator._failed_polls == 0


def test_three_consecutive_incomplete_polls_fail(integration):
    _pkg, module = integration
    coordinator = _coordinator(module, iter([False] * 3))

    _poll(coordinator)
    _poll(coordinator)
    with pytest.raises(_UpdateFailed):
        _poll(coordinator)


def _registry_sync(pkg, monkeypatch, fan, coordinator_attrs):
    listeners = []
    coordinator = SimpleNamespace(
        _fan=fan,
        last_update_success=True,
        _failed_polls=0,
        async_add_listener=lambda cb: listeners.append(cb) or (lambda: None),
        **coordinator_attrs,
    )
    hass = MagicMock()
    entry = MagicMock()
    monkeypatch.setattr(
        pkg, "_async_update_unsupported_optional_poll_entities", lambda *a: None
    )
    pkg._async_register_optional_poll_entity_sync(hass, entry, coordinator)
    return hass, coordinator, listeners[0]


def _fan(device_search="DEV1"):
    return SimpleNamespace(
        profile_key="breezy",
        _unit_type_id=0x1100,
        firmware="0.8",
        device_search=device_search,
    )


def test_none_device_search_does_not_reload(integration, monkeypatch):
    pkg, _module = integration
    fan = _fan()
    hass, _coordinator_obj, sync = _registry_sync(pkg, monkeypatch, fan, {})

    fan.device_search = None
    fan.firmware = None
    sync()
    hass.config_entries.async_schedule_reload.assert_not_called()


def test_changed_device_search_still_reloads(integration, monkeypatch):
    pkg, _module = integration
    fan = _fan()
    hass, _coordinator_obj, sync = _registry_sync(pkg, monkeypatch, fan, {})

    fan.device_search = "DEV2"
    sync()
    hass.config_entries.async_schedule_reload.assert_called_once()


def test_identity_check_skipped_after_tolerated_incomplete_poll(
    integration, monkeypatch
):
    pkg, _module = integration
    fan = _fan()
    hass, coordinator, sync = _registry_sync(pkg, monkeypatch, fan, {})

    fan.device_search = "DEV2"
    coordinator._failed_polls = 1
    sync()
    hass.config_entries.async_schedule_reload.assert_not_called()


def test_required_params_get_extra_individual_retries():
    fan = Fan("192.0.2.1", fan_id="0123456789ABCDEF")
    calls = []

    def send_command(command, param, value="", retries=10, **_kwargs):
        calls.append((param, retries))
        return False

    fan.send_command = send_command
    fan._bulk_read_supported = False
    fan._read_params_locked("000100020006", required_params=(0x0001, 0x0002))

    retries = dict(calls)
    assert retries["0001"] == 3
    assert retries["0002"] == 3
    assert retries["0006"] == 1

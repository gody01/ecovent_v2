"""Exercise issue 100 through real HA coordinator, entity and state-machine code.

Run with a Python environment containing Home Assistant (tested with 2026.6.0.dev0):
    python tests/ha_issue100_smoke.py
    python tests/ha_issue100_smoke.py --baseline b72970a

The optional baseline replaces only the two historical polling handlers, keeping
HA and the wire fixture identical. Cycles are accelerated: 26 calls represent
13 minutes at the default 30-second interval; there is no wall-clock soak.
Replies use captured TwinFresh values with controlled omissions. This does not
reproduce the frequency of natural packet loss. Schedule/Repairs side effects
are excluded; all fan polling, parsing, HA availability, entity listeners and
state serialization use production code. No network or device writes are allowed.
"""

import argparse
import asyncio
import importlib
import json
import logging
from pathlib import Path
import sys
import tempfile
import subprocess
import types

from ecovent_test_helpers import Fan, packet_with_payload
from homeassistant.core import HomeAssistant
from homeassistant.const import __version__
from homeassistant.helpers.entity_component import EntityComponent

ROOT = Path(__file__).resolve().parents[1]

pkg = types.ModuleType("audit_ecovent")
pkg.__path__ = [str(ROOT / "custom_components/ecovent_v2")]
sys.modules[pkg.__name__] = pkg

Coordinator = importlib.import_module("audit_ecovent.coordinator").EcoVentCoordinator
Entity = importlib.import_module("audit_ecovent.fan").VentoExpertFan

capture = json.loads(
    (ROOT / "tests/fixtures/twinfresh_style_wifi_poll_capture.json").read_text()
)
values = {}
decoder = Fan("192.0.2.1")
for tx in capture["identity_transactions"] + capture["polls"][0]["transactions"]:
    for frame in tx["frames"]:
        if frame:
            assert decoder.parse_response(
                packet_with_payload(bytes.fromhex(frame["payload"])), store=False
            )
            values.update(decoder._last_response_param_values)


class Wire:
    def __init__(self, fan):
        self.fan = fan
        self.values = dict(values)
        self.omit = set()
        self.bulk_omit = set()
        self.reject = set()
        self.offline = False
        self.response_mode = "normal"
        self.calls = []
        self.pending = None

    def send(self, data):
        assert data[:2] == self.fan.func["read"], "unexpected control write"
        # Decode read IDs, including page switches, from the production encoder.
        raw = bytes.fromhex(data[2:])
        page = 0
        ids = []
        i = 0
        while i < len(raw):
            n = raw[i]
            i += 1
            if n == 255:
                page = raw[i]
                i += 1
            else:
                ids.append(page * 256 + n)
        self.calls.append(ids)
        payload = b""
        for pid in ids:
            if pid in self.omit or (len(ids) > 1 and pid in self.bulk_omit):
                continue
            payload += bytes([255, pid >> 8])
            if pid in self.reject:
                payload += bytes([253, pid & 255])
            elif pid in self.values:
                value = self.values[pid]
                payload += (
                    (bytes([254, len(value)]) if len(value) > 1 else b"")
                    + bytes([pid & 255])
                    + value
                )
            else:
                payload = payload[:-2]
        self.pending = (
            packet_with_payload(payload, device_id=self.fan.id.encode())
            if payload
            else False
        )
        return not self.offline

    def receive(self):
        if self.offline:
            return False
        if self.response_mode == "empty":
            return packet_with_payload(b"", device_id=self.fan.id.encode())
        if self.response_mode == "unrelated":
            return packet_with_payload(
                bytes([255, 127, 1, 1]), device_id=self.fan.id.encode()
            )
        if self.response_mode == "wrong_device":
            return packet_with_payload(bytes([1, 1]), device_id=b"OTHER_DEVICE_123")
        if self.response_mode == "checksum" and self.pending:
            return self.pending[:-1] + bytes([self.pending[-1] ^ 1])
        return self.pending


async def run_case(pid, baseline=None, recovery="individual"):
    rows = []
    with tempfile.TemporaryDirectory(prefix="ecovent-ha-audit-") as tmp:
        hass = HomeAssistant(tmp)
        entry = types.SimpleNamespace(
            data={
                "ip_address": "192.0.2.1",
                "password": "1111",
                "name": "Audit",
                "auto_clock_sync": False,
            },
            unique_id=None,
            entry_id="audit",
            async_on_unload=lambda _: None,
            pref_disable_polling=True,
        )
        from homeassistant.helpers import entity_registry, device_registry

        device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        co = Coordinator(hass, entry)
        fan = co._fan
        if baseline:
            namespace = {"__name__": "baseline_protocol"}
            exec(
                subprocess.check_output(
                    [
                        "git",
                        "show",
                        f"{baseline}:custom_components/ecovent_v2/fan_protocol.py",
                    ],
                    cwd=ROOT,
                    text=True,
                ),
                namespace,
            )
            for name in ("_read_params", "_mark_param_unavailable"):
                setattr(
                    fan,
                    name,
                    types.MethodType(getattr(namespace["FanProtocolMixin"], name), fan),
                )
        wire = Wire(fan)
        fan.send = wire.send
        fan.receive = wire.receive
        # No schedule editor involved in #100; keep its separate traffic out.
        co._should_refresh_schedule_week = lambda: False
        co._update_hardware_profile_mismatch_repair_issue = lambda: None
        await co.async_refresh()
        assert co.last_update_success, repr(co.last_exception)
        hass.data["ecovent_v2"] = {"audit": co}
        entity = Entity(hass, entry)
        component = EntityComponent(logging.getLogger("audit"), "fan", hass)
        await component.async_add_entities([entity])
        entity.async_write_ha_state()
        assert hass.states.get(entity.entity_id).state == "on"
        initial_percentage = entity.percentage
        wire.omit = {pid}
        if recovery == "individual":
            wire.bulk_omit = {pid}
        co.updateCounter = 3
        for cycle in range(26):
            if cycle == 2:
                wire.omit.clear()
                wire.values[pid] = {1: b"\x00", 2: b"\x02", 68: b"\x80"}[pid]
            wire.calls.clear()
            await co.async_refresh()
            current = hass.states.get(entity.entity_id)
            assert co.last_update_success, repr(co.last_exception)
            rows.append(
                {
                    "cycle": cycle,
                    "state": current.state,
                    "percentage": current.attributes.get("percentage"),
                    "targeted": [pid] in wire.calls,
                }
            )
            if not baseline:
                assert current.state not in ("unknown", "unavailable"), rows[-1]
                assert current.attributes["percentage"] is not None, rows[-1]
                if cycle == 0:
                    wire.calls.clear()
                    try:
                        if pid == 1:
                            await entity.async_turn_on()
                        else:
                            await entity.async_set_percentage(initial_percentage)
                    except RuntimeError as err:
                        assert "retained control" in str(err), str(err)
                        assert wire.calls and all(ids == [pid] for ids in wire.calls)
                    else:
                        raise AssertionError(
                            "retained control accepted as a successful command"
                        )
                if cycle == 2:
                    # A recovered value must also restore successful controls.
                    wire.calls.clear()
                    if pid == 1:
                        await entity.async_turn_off()
                    else:
                        await entity.async_set_preset_mode(entity.preset_mode)
                    assert not wire.calls, "confirmed unchanged command was not a no-op"
                if cycle < 2:
                    assert (
                        current.state == "on"
                        and current.attributes["percentage"] == initial_percentage
                    )
                else:
                    assert (
                        (current.state == "off")
                        if pid == 1
                        else (current.attributes["percentage"] != initial_percentage)
                    ), rows[-1]
        if baseline:
            assert any(
                row["state"] == "unknown" or row["percentage"] is None for row in rows
            )
        else:
            # Keep the actual HA failure/recovery path strict even with cached controls.
            wire.offline = True
            await co.async_refresh()
            assert not co.last_update_success
            assert hass.states.get(entity.entity_id).state == "unavailable"
            wire.offline = False
            await co.async_refresh()
            assert co.last_update_success
            assert hass.states.get(entity.entity_id).state not in (
                "unknown",
                "unavailable",
            )
        if not baseline:
            wire.bulk_omit.clear()
            for response_mode in ("empty", "unrelated", "wrong_device", "checksum"):
                wire.response_mode = response_mode
                await co.async_refresh()
                assert not co.last_update_success, response_mode
                assert hass.states.get(entity.entity_id).state == "unavailable", (
                    response_mode
                )
            wire.response_mode = "normal"
            await co.async_refresh()
            assert co.last_update_success
            # Valid frame with an invalid control width is not a soft omission.
            wire.values[pid] = b"\x01\x02"
            co.updateCounter = 3
            await co.async_refresh()
            current = hass.states.get(entity.entity_id)
            assert co.last_update_success
            assert (
                current.state == "unknown"
                if pid == 1
                else current.attributes["percentage"] is None
            )
            assert pid not in fan.retained_control_params
            wire.values[pid] = {1: b"\x00", 2: b"\x02", 68: b"\x80"}[pid]
            co.updateCounter = 3
            await co.async_refresh()
            assert co.last_update_success
            wire.reject = {pid}
            co.updateCounter = 3
            await co.async_refresh()
            current = hass.states.get(entity.entity_id)
            assert co.last_update_success
            assert (
                current.state == "unknown"
                if pid == 1
                else current.attributes["percentage"] is None
            )
            assert pid in fan.unsupported_optional_poll_parameter_ids()
            assert pid not in fan.retained_control_params
        print(
            json.dumps(
                {
                    "ha": __version__,
                    "baseline": baseline,
                    "row": pid,
                    "recovery": recovery,
                    "unknown_cycles": sum(
                        r["state"] == "unknown" or r["percentage"] is None for r in rows
                    ),
                    "first_recovered_cycle": next(
                        i
                        for i, r in enumerate(rows[2:], 2)
                        if r["state"] != "unknown" and r["percentage"] is not None
                    ),
                    "cycles": len(rows),
                }
            )
        )
        await co.async_shutdown()
        await hass.async_stop()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline", help="Compare old polling handlers from this git revision"
    )
    args = parser.parse_args()
    for baseline in [args.baseline, None] if args.baseline else [None]:
        for recovery in ("bulk", "individual"):
            for pid in (1, 2, 68):
                await run_case(pid, baseline, recovery)


if __name__ == "__main__":
    asyncio.run(main())

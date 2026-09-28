"""Run real Home Assistant separately from the suite's module stubs."""

from pathlib import Path
import subprocess
import sys

import pytest


HARNESS = Path(__file__).with_name("ha_issue109_smoke.py")


def _skip_without_homeassistant():
    result = subprocess.run(
        [sys.executable, "-c", "import homeassistant"], capture_output=True
    )
    if result.returncode:
        pytest.skip("requires an importable Home Assistant installation")


def test_recom_4_sr_dump_exposes_temperatures_and_no_known_variant_repair():
    _skip_without_homeassistant()
    subprocess.run([sys.executable, str(HARNESS)], check=True)



def test_recom_late_probes_reload_at_most_once_across_setups():
    _skip_without_homeassistant()
    subprocess.run([sys.executable, str(HARNESS), "reload-loop"], check=True)

def test_recom_probe_latch_does_not_cross_device_serials():
    _skip_without_homeassistant()
    subprocess.run([sys.executable, str(HARNESS), "serial-swap"], check=True)

def test_recom_probe_latch_is_cleared_when_config_entry_is_removed():
    _skip_without_homeassistant()
    subprocess.run([sys.executable, str(HARNESS), "remove-latch"], check=True)
def test_df270_shaped_0100_without_temperature_answers_keeps_existing_behavior():
    _skip_without_homeassistant()
    subprocess.run([sys.executable, str(HARNESS), "df270"], check=True)

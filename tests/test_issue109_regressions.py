"""Run real Home Assistant separately from the suite's module stubs."""

from pathlib import Path
import subprocess
import sys


HARNESS = Path(__file__).with_name("ha_issue109_smoke.py")


def test_recom_4_sr_dump_exposes_temperatures_and_no_known_variant_repair():
    subprocess.run([sys.executable, str(HARNESS)], check=True)


def test_df270_shaped_0100_without_temperature_answers_keeps_existing_behavior():
    subprocess.run([sys.executable, str(HARNESS), "df270"], check=True)

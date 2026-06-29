"""Deterministic generator for the Device KPI demo dataset.

Running this script regenerates the two CSV files the dashboard reads:

* ``data/devices.csv``   - one row per measurement device (current snapshot)
* ``data/test_runs.csv`` - historical test runs, ~8 weeks, for trend charts

The generator is fully seeded (``random.seed(SEED)``) so the output is
reproducible: the same SEED always yields byte-identical CSVs. This lets the
data be regenerated on demand while keeping the committed files stable, and it
gives a clean talking point ("the demo data is generated, not hand-faked").

The dataset is anchored to ``REFERENCE_DATE`` so the calibration story
(overdue / due-soon devices) is meaningful when the dashboard is demoed.

Usage:
    python scripts/generate_data.py
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42

# All relative dates (calibration, test timestamps) are anchored here so the
# demo tells a stable story regardless of when the generator last ran.
REFERENCE_DATE = date(2026, 6, 29)

BASE_DIR = Path(__file__).resolve().parent.parent
DEVICES_FILE = BASE_DIR / "data" / "devices.csv"
TEST_RUNS_FILE = BASE_DIR / "data" / "test_runs.csv"

LOCATIONS = ["Berlin", "Munich", "Hamburg", "Frankfurt"]

# Firmware versions ordered oldest -> newest. Older firmware fails more often,
# which creates a credible "failures concentrate on outdated firmware" story.
FIRMWARE_VERSIONS = ["1.0.4", "1.0.8", "1.0.9", "1.1.5", "1.1.9", "1.2.0", "1.2.1", "1.3.0"]

# Device model name prefixes -> a realistic measurement-device fleet.
DEVICE_TYPES = [
    "Pressure Sensor",
    "Voltage Meter",
    "Temperature Logger",
    "Oscilloscope",
    "Signal Analyzer",
    "Power Analyzer",
    "Frequency Counter",
    "Current Probe",
    "Logic Analyzer",
    "Multimeter",
    "Spectrum Analyzer",
    "Function Generator",
]

ERROR_CODES = ["E_CONN", "E_TEST", "E_TIMEOUT", "E_CALIB", "E_FIRMWARE"]

N_DEVICES = 42
HISTORY_WEEKS = 8


@dataclass
class Device:
    device_id: str
    device_name: str
    location: str
    status: str
    firmware_version: str
    last_test_result: str
    test_duration_sec: int
    calibration_due: str
    pipeline_status: str
    error_code: str
    last_test_time: str
    # Internal: probability this device fails a given run (drives history).
    fail_bias: float = field(default=0.0, repr=False)


def _firmware_fail_bias(firmware: str) -> float:
    """Older firmware -> higher chance of failure."""
    idx = FIRMWARE_VERSIONS.index(firmware)
    # idx 0 (oldest) -> ~0.6, newest -> ~0.05
    return round(0.6 - (idx / (len(FIRMWARE_VERSIONS) - 1)) * 0.55, 3)


def _duration_for(result: str, rng: random.Random) -> int:
    """Failing runs take noticeably longer than passing ones (timeouts/retries)."""
    if result == "Pass":
        return rng.randint(22, 52)
    return rng.randint(55, 95)


def _make_devices(rng: random.Random) -> list[Device]:
    devices: list[Device] = []
    for i in range(1, N_DEVICES + 1):
        device_id = f"M{i:03d}"
        device_type = DEVICE_TYPES[(i - 1) % len(DEVICE_TYPES)]
        suffix = chr(ord("A") + (i - 1) % 26)
        device_name = f"{device_type} {suffix}"
        location = rng.choice(LOCATIONS)
        firmware = rng.choice(FIRMWARE_VERSIONS)
        fail_bias = _firmware_fail_bias(firmware)

        # Status: mostly Online, a few Offline / Maintenance.
        status = rng.choices(
            ["Online", "Offline", "Maintenance"],
            weights=[0.74, 0.16, 0.10],
        )[0]

        # Offline devices fail; otherwise failure scales with firmware age.
        if status == "Offline":
            result = "Fail"
        else:
            result = "Fail" if rng.random() < fail_bias else "Pass"

        duration = _duration_for(result, rng)

        if result == "Pass":
            pipeline_status = "Success"
        elif status == "Maintenance":
            pipeline_status = "Warning"
        else:
            pipeline_status = "Failed"

        # Error code only when something is wrong.
        if result == "Fail" or status != "Online":
            if status == "Maintenance":
                error_code = "E_CALIB"
            else:
                error_code = rng.choice(ERROR_CODES)
        else:
            error_code = ""

        # Calibration due dates spread around the reference date: a handful are
        # already overdue, several are due within 30 days, the rest are healthy.
        offset_days = rng.choices(
            [rng.randint(-40, -1), rng.randint(0, 30), rng.randint(31, 240)],
            weights=[0.18, 0.22, 0.60],
        )[0]
        calibration_due = (REFERENCE_DATE + timedelta(days=offset_days)).isoformat()

        # Last test time: within the last 3 days.
        last_dt = datetime(
            REFERENCE_DATE.year, REFERENCE_DATE.month, REFERENCE_DATE.day, 8, 0
        ) - timedelta(days=rng.randint(0, 3), hours=rng.randint(0, 12), minutes=rng.randint(0, 59))
        last_test_time = last_dt.strftime("%Y-%m-%d %H:%M")

        devices.append(
            Device(
                device_id=device_id,
                device_name=device_name,
                location=location,
                status=status,
                firmware_version=firmware,
                last_test_result=result,
                test_duration_sec=duration,
                calibration_due=calibration_due,
                pipeline_status=pipeline_status,
                error_code=error_code,
                last_test_time=last_test_time,
                fail_bias=fail_bias,
            )
        )
    return devices


def _make_test_runs(devices: list[Device], rng: random.Random) -> list[dict]:
    """Generate ~8 weeks of test-run history (twice weekly per device)."""
    runs: list[dict] = []
    start = REFERENCE_DATE - timedelta(weeks=HISTORY_WEEKS)
    # Two runs per week per device.
    run_days = list(range(0, HISTORY_WEEKS * 7, 3))
    for device in devices:
        for day_offset in run_days:
            run_dt = datetime(start.year, start.month, start.day, 9, 0) + timedelta(
                days=day_offset, hours=rng.randint(0, 8), minutes=rng.randint(0, 59)
            )
            if run_dt.date() > REFERENCE_DATE:
                continue
            result = "Fail" if rng.random() < device.fail_bias else "Pass"
            duration = _duration_for(result, rng)
            pipeline_status = "Success" if result == "Pass" else "Failed"
            runs.append(
                {
                    "run_timestamp": run_dt.strftime("%Y-%m-%d %H:%M"),
                    "device_id": device.device_id,
                    "result": result,
                    "duration_sec": duration,
                    "pipeline_status": pipeline_status,
                }
            )
    runs.sort(key=lambda r: (r["run_timestamp"], r["device_id"]))
    return runs


def _write_devices(devices: list[Device]) -> None:
    fieldnames = [
        "device_id",
        "device_name",
        "location",
        "status",
        "firmware_version",
        "last_test_result",
        "test_duration_sec",
        "calibration_due",
        "pipeline_status",
        "error_code",
        "last_test_time",
    ]
    DEVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DEVICES_FILE.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for device in devices:
            row = {name: getattr(device, name) for name in fieldnames}
            writer.writerow(row)


def _write_test_runs(runs: list[dict]) -> None:
    fieldnames = ["run_timestamp", "device_id", "result", "duration_sec", "pipeline_status"]
    TEST_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TEST_RUNS_FILE.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(runs)


def main() -> None:
    rng = random.Random(SEED)
    devices = _make_devices(rng)
    runs = _make_test_runs(devices, rng)
    _write_devices(devices)
    _write_test_runs(runs)
    print(f"Wrote {len(devices)} devices -> {DEVICES_FILE.relative_to(BASE_DIR)}")
    print(f"Wrote {len(runs)} test runs -> {TEST_RUNS_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()

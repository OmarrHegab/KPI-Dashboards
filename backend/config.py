"""Runtime configuration for the backend, read from the environment.

Twelve-factor style: every operational knob has an environment-variable
override with a sensible default, so the same image runs unchanged in local,
Docker, and CI contexts. Tests point ``DEVICE_DATA_FILE`` at a fixture CSV.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Data sources (overridable so tests can inject fixture files).
DEVICE_DATA_FILE = Path(os.getenv("DEVICE_DATA_FILE", str(BASE_DIR / "data" / "devices.csv")))
TEST_RUNS_FILE = Path(os.getenv("TEST_RUNS_FILE", str(BASE_DIR / "data" / "test_runs.csv")))

# Test-duration SLA: runs slower than this many seconds breach the budget.
SLA_THRESHOLD_SEC = int(os.getenv("SLA_THRESHOLD_SEC", "60"))

# A device is "due soon" when its calibration date falls within this window.
CALIBRATION_SOON_DAYS = int(os.getenv("CALIBRATION_SOON_DAYS", "30"))

# CORS allow-list for browser clients (comma-separated). "*" allows any origin.
CORS_ALLOW_ORIGINS = [
    origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()
]

# Canonical category values. Used for validation and stable filter ordering.
DEVICE_STATUSES = ["Online", "Offline", "Maintenance"]
PIPELINE_STATUSES = ["Success", "Failed", "Warning"]

# Columns every devices CSV must contain. Used to fail fast on malformed data.
REQUIRED_DEVICE_COLUMNS = [
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

# Columns the test-run history CSV must contain for trend aggregation.
REQUIRED_TEST_RUN_COLUMNS = [
    "run_timestamp",
    "device_id",
    "result",
    "duration_sec",
    "pipeline_status",
]

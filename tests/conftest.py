"""Shared pytest fixtures.

The fixtures provide a small, known-value device set so tests assert exact KPI
numbers without depending on the (regenerable) production CSV. ``TODAY`` is a
fixed anchor so calibration KPIs are deterministic.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import api
from backend.data import clear_cache

# Fixed "today" used for all calibration assertions.
TODAY = date(2026, 6, 29)

# 10-row fixture with hand-computed expected KPIs (see tests/test_kpis.py).
_SAMPLE_ROWS = [
    # id,   name,        location, status,        fw,      result, dur, calib,        pipeline,  err
    ("M001", "Sensor A", "Berlin", "Online", "1.2.0", "Pass", 30, "2026-09-01", "Success", ""),
    ("M002", "Meter B", "Munich", "Online", "1.1.5", "Pass", 40, "2026-07-10", "Success", ""),
    ("M003", "Logger C", "Berlin", "Online", "1.0.9", "Fail", 70, "2026-06-01", "Failed", "E_TEST"),
    (
        "M004",
        "Scope D",
        "Hamburg",
        "Offline",
        "1.0.4",
        "Fail",
        80,
        "2026-05-15",
        "Failed",
        "E_CONN",
    ),
    (
        "M005",
        "Probe E",
        "Berlin",
        "Maintenance",
        "1.0.8",
        "Fail",
        65,
        "2026-07-20",
        "Warning",
        "E_CALIB",
    ),
    ("M006", "Analyzer F", "Munich", "Online", "1.3.0", "Pass", 35, "2026-12-01", "Success", ""),
    ("M007", "Counter G", "Hamburg", "Online", "1.2.1", "Pass", 28, "2027-01-01", "Success", ""),
    (
        "M008",
        "Probe H",
        "Berlin",
        "Online",
        "1.0.9",
        "Fail",
        90,
        "2026-07-05",
        "Failed",
        "E_TIMEOUT",
    ),
    ("M009", "Logic I", "Munich", "Offline", "1.0.4", "Fail", 75, "2026-06-20", "Failed", "E_CONN"),
    ("M010", "Multi J", "Hamburg", "Online", "1.2.0", "Pass", 45, "2026-08-15", "Success", ""),
]

_COLUMNS = [
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
]


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A 10-row device DataFrame with known, asserted KPI values."""
    df = pd.DataFrame(_SAMPLE_ROWS, columns=_COLUMNS)
    df["last_test_time"] = "2026-06-28 09:00"
    return df


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """An empty DataFrame with the right columns (the all-filtered-out case)."""
    df = pd.DataFrame(columns=[*_COLUMNS, "last_test_time"])
    return df.astype({"test_duration_sec": "int64"})


@pytest.fixture
def client(monkeypatch, sample_df) -> TestClient:
    """TestClient whose data layer is backed by the in-memory ``sample_df``."""
    clear_cache()
    monkeypatch.setattr(api, "load_devices", lambda *a, **k: sample_df)
    return TestClient(api.app)

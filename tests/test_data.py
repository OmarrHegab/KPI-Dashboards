"""Tests for the data-loading layer and its error handling."""

from __future__ import annotations

import os
import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import api, data
from backend.config import REQUIRED_DEVICE_COLUMNS, REQUIRED_TEST_RUN_COLUMNS
from backend.data import (
    DataSchemaError,
    DataUnavailableError,
    clear_cache,
    load_devices,
    load_test_runs,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_file_raises_data_unavailable(tmp_path):
    with pytest.raises(DataUnavailableError):
        load_devices(tmp_path / "does_not_exist.csv")


def test_missing_columns_raises_schema_error(tmp_path):
    csv = _write(tmp_path / "bad.csv", "device_id,status\nM001,Online\n")
    with pytest.raises(DataSchemaError):
        load_devices(csv)


def test_valid_csv_loads(tmp_path):
    header = ",".join(REQUIRED_DEVICE_COLUMNS)
    row = "M001,Sensor,Berlin,Online,1.2.0,Pass,30,2026-09-01,Success,,2026-06-28 09:00"
    csv = _write(tmp_path / "good.csv", f"{header}\n{row}\n")
    df = load_devices(csv)
    assert len(df) == 1
    assert df.iloc[0]["device_id"] == "M001"


def test_blank_numeric_cell_does_not_break_typed_response(tmp_path):
    """A blank test_duration_sec must coerce to 0 (int), not crash /devices."""
    header = ",".join(REQUIRED_DEVICE_COLUMNS)
    # Second row has an empty test_duration_sec and empty error_code.
    rows = (
        "M001,Sensor,Berlin,Online,1.2.0,Pass,30,2026-09-01,Success,,2026-06-28 09:00\n"
        "M002,Meter,Berlin,Offline,1.0.4,Fail,,2026-05-01,Failed,,2026-06-28 09:00\n"
    )
    csv = _write(tmp_path / "dirty.csv", f"{header}\n{rows}")
    df = load_devices(csv)
    assert df["test_duration_sec"].dtype.kind == "i"  # integer dtype
    assert int(df.iloc[1]["test_duration_sec"]) == 0
    assert df.iloc[1]["error_code"] == ""


def test_devices_endpoint_serializes_dirty_data(monkeypatch, tmp_path):
    header = ",".join(REQUIRED_DEVICE_COLUMNS)
    rows = "M002,Meter,Berlin,Offline,1.0.4,Fail,,2026-05-01,Failed,,2026-06-28 09:00\n"
    csv = _write(tmp_path / "dirty.csv", f"{header}\n{rows}")
    monkeypatch.setattr(api, "load_devices", lambda *a, **k: load_devices(csv))
    resp = TestClient(api.app).get("/devices")
    assert resp.status_code == 200
    assert resp.json()[0]["test_duration_sec"] == 0


def test_cache_refreshes_when_file_changes(tmp_path):
    header = ",".join(REQUIRED_DEVICE_COLUMNS)
    base = "Sensor,Berlin,Online,1.2.0,Pass,30,2026-09-01,Success,,2026-06-28 09:00"
    csv = _write(tmp_path / "d.csv", f"{header}\nM001,{base}\n")
    assert len(load_devices(csv)) == 1

    _write(csv, f"{header}\nM001,{base}\nM002,{base}\n")
    # mtime change must invalidate the cache.
    os.utime(csv, (time.time() + 1, time.time() + 1))
    assert len(load_devices(csv)) == 2


def test_two_files_coexist_in_cache(tmp_path, monkeypatch):
    """Loading devices then test_runs (and back) must not evict each other."""
    dev_header = ",".join(REQUIRED_DEVICE_COLUMNS)
    dev = _write(
        tmp_path / "dev.csv",
        f"{dev_header}\nM001,S,Berlin,Online,1.2.0,Pass,30,2026-09-01,Success,,2026-06-28 09:00\n",
    )
    runs_header = ",".join(REQUIRED_TEST_RUN_COLUMNS)
    runs = _write(tmp_path / "runs.csv", f"{runs_header}\n2026-06-01 09:00,M001,Pass,30,Success\n")

    calls = {"n": 0}
    real_read = pd.read_csv

    def counting_read(*args, **kwargs):
        calls["n"] += 1
        return real_read(*args, **kwargs)

    monkeypatch.setattr(data.pd, "read_csv", counting_read)

    load_devices(dev)
    load_test_runs(runs)
    load_devices(dev)  # must be a cache HIT, not a re-parse
    load_test_runs(runs)  # cache HIT

    assert calls["n"] == 2  # each file parsed exactly once


def test_test_runs_missing_columns_degrades_to_empty(tmp_path):
    csv = _write(tmp_path / "runs.csv", "run_timestamp,foo\n2026-06-01 09:00,bar\n")
    df = load_test_runs(csv)
    assert df.empty
    assert list(df.columns) == REQUIRED_TEST_RUN_COLUMNS


def test_trends_endpoint_ok_with_malformed_runs(monkeypatch, tmp_path):
    csv = _write(tmp_path / "runs.csv", "run_timestamp,foo\n2026-06-01 09:00,bar\n")
    monkeypatch.setattr(api, "load_test_runs", lambda *a, **k: load_test_runs(csv))
    resp = TestClient(api.app).get("/trends")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_returns_503_when_data_unavailable(monkeypatch):
    def _boom(*_a, **_k):
        raise DataUnavailableError("Data file not found: devices.csv")

    monkeypatch.setattr(api, "load_devices", _boom)
    resp = TestClient(api.app, raise_server_exceptions=False).get("/devices")
    assert resp.status_code == 503
    assert "detail" in resp.json()


def test_ready_reports_unavailable(monkeypatch):
    def _boom(*_a, **_k):
        raise DataUnavailableError("gone")

    monkeypatch.setattr(api, "load_devices", _boom)
    resp = TestClient(api.app).get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unavailable"


class TestProductionData:
    """Smoke tests against the real committed CSV (regenerable, but present)."""

    def test_production_devices_load(self):
        df = load_devices()
        assert len(df) >= 10
        assert set(REQUIRED_DEVICE_COLUMNS) <= set(df.columns)

    def test_production_statuses_are_known(self):
        df = load_devices()
        assert set(df["status"].unique()) <= {"Online", "Offline", "Maintenance"}

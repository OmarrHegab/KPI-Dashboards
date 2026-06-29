"""Endpoint tests using FastAPI's TestClient against the in-memory fixture data.

Calibration KPIs depend on the real "today", so this module asserts their type
and bounds only; their exact values are pinned in tests/test_kpis.py where
``today`` is injected.
"""

from __future__ import annotations


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Device KPI API is running"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_reports_device_count(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["devices_loaded"] == 10


def test_devices_returns_all_rows(client):
    resp = client.get("/devices")
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) == 10
    expected_keys = {
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
    }
    assert expected_keys <= set(devices[0].keys())


def test_devices_status_filter(client):
    resp = client.get("/devices", params={"status": ["Online"]})
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) == 7
    assert {d["status"] for d in devices} == {"Online"}


def test_devices_combined_filter(client):
    resp = client.get("/devices", params={"status": ["Online"], "pipeline_status": ["Failed"]})
    assert {d["device_id"] for d in resp.json()} == {"M003", "M008"}


def test_kpis_shape_and_values(client):
    resp = client.get("/kpis")
    assert resp.status_code == 200
    kpis = resp.json()

    expected_keys = {
        "total_devices",
        "online_devices",
        "offline_devices",
        "maintenance_devices",
        "test_pass_rate",
        "pipeline_success_rate",
        "avg_test_duration",
        "p95_test_duration",
        "sla_threshold_sec",
        "tests_over_sla",
        "calibration_overdue",
        "calibration_due_soon",
        "error_code_breakdown",
    }
    # Exact key set: adding/removing a KPI must break this test on purpose.
    assert set(kpis.keys()) == expected_keys

    assert kpis["total_devices"] == 10
    assert kpis["online_devices"] == 7
    assert kpis["test_pass_rate"] == 50.0
    assert kpis["tests_over_sla"] == 5
    assert isinstance(kpis["calibration_overdue"], int)
    assert kpis["calibration_overdue"] >= 0


def test_kpis_types(client):
    kpis = client.get("/kpis").json()
    for int_key in ("total_devices", "online_devices", "tests_over_sla"):
        assert isinstance(kpis[int_key], int)
    for float_key in ("test_pass_rate", "avg_test_duration", "p95_test_duration"):
        assert isinstance(kpis[float_key], float)


def test_kpis_filtered(client):
    kpis = client.get("/kpis", params={"status": ["Online"]}).json()
    assert kpis["total_devices"] == 7
    assert kpis["offline_devices"] == 0


def test_kpis_empty_filter_is_json_safe(client):
    """All-filtered-out must return a clean 200 with finite zeros, not a 500."""
    resp = client.get("/kpis", params={"status": ["Nonexistent"]})
    assert resp.status_code == 200
    kpis = resp.json()
    assert kpis["total_devices"] == 0
    assert kpis["test_pass_rate"] == 0.0
    assert kpis["avg_test_duration"] == 0.0


def test_devices_and_kpis_are_consistent(client):
    """Cross-endpoint invariant: aggregates must match the raw device list."""
    devices = client.get("/devices").json()
    kpis = client.get("/kpis").json()

    assert kpis["total_devices"] == len(devices)
    online = sum(1 for d in devices if d["status"] == "Online")
    assert kpis["online_devices"] == online
    passes = sum(1 for d in devices if d["last_test_result"] == "Pass")
    assert kpis["test_pass_rate"] == round(passes / len(devices) * 100, 1)


def test_openapi_documents_models(client):
    """Pydantic models should surface in the OpenAPI schema."""
    schema = client.get("/openapi.json").json()
    assert "KpiSummary" in schema["components"]["schemas"]
    assert "Device" in schema["components"]["schemas"]

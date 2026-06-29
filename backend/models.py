"""Pydantic response models.

These give every endpoint a typed, self-documenting contract: FastAPI renders
them in the OpenAPI schema (/docs), validates responses against them, and makes
the API shape explicit to consumers and tests.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Device(BaseModel):
    """A single measurement device (one row of devices.csv)."""

    device_id: str
    device_name: str
    location: str
    status: str
    firmware_version: str
    last_test_result: str
    test_duration_sec: int
    calibration_due: str
    pipeline_status: str
    error_code: str = ""
    last_test_time: str = ""


class ErrorCodeCount(BaseModel):
    """How often a given failure error code occurs across the fleet."""

    code: str
    count: int


class KpiSummary(BaseModel):
    """Aggregated KPIs over a (possibly filtered) set of devices."""

    total_devices: int
    online_devices: int
    offline_devices: int
    maintenance_devices: int

    test_pass_rate: float = Field(ge=0, le=100)
    pipeline_success_rate: float = Field(ge=0, le=100)

    avg_test_duration: float = Field(ge=0)
    p95_test_duration: float = Field(ge=0)
    sla_threshold_sec: int
    tests_over_sla: int

    calibration_overdue: int
    calibration_due_soon: int

    error_code_breakdown: list[ErrorCodeCount] = Field(default_factory=list)


class TrendPoint(BaseModel):
    """One day of aggregated test-run history (for trend charts)."""

    date: str
    total_runs: int
    pass_rate: float = Field(ge=0, le=100)
    pipeline_success_rate: float = Field(ge=0, le=100)
    avg_duration: float = Field(ge=0)


class HealthStatus(BaseModel):
    """Liveness/readiness probe response."""

    status: str
    devices_loaded: int | None = None
    detail: str | None = None

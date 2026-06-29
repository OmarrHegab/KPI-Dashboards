"""FastAPI service exposing device data, KPIs and trends.

This is a thin HTTP layer: it loads data via :mod:`backend.data` and delegates
all aggregation to the pure functions in :mod:`backend.kpis`. Domain errors are
translated into clean JSON HTTP responses by an exception handler.

Run locally:
    python -m uvicorn backend.api:app --reload
or simply:
    python backend/api.py
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import CORS_ALLOW_ORIGINS
from backend.data import (
    DataSchemaError,
    DataUnavailableError,
    load_devices,
    load_test_runs,
)
from backend.kpis import compute_kpis, compute_trends, filter_devices
from backend.models import Device, HealthStatus, KpiSummary, TrendPoint

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Device KPI API",
    description="KPIs and health metrics for a fleet of electronic measurement devices.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(DataUnavailableError)
async def _data_unavailable_handler(_: Request, exc: DataUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(DataSchemaError)
async def _data_schema_handler(_: Request, exc: DataSchemaError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
def root() -> dict[str, str]:
    """Service banner."""
    return {"message": "Device KPI API is running"}


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """Liveness probe: the process is up and serving."""
    return HealthStatus(status="ok")


@app.get("/ready", response_model=HealthStatus)
def ready() -> HealthStatus:
    """Readiness probe: the data source is actually loadable."""
    try:
        df = load_devices()
    except (DataUnavailableError, DataSchemaError) as exc:
        return HealthStatus(status="unavailable", detail=str(exc))
    return HealthStatus(status="ok", devices_loaded=len(df))


@app.get("/devices", response_model=list[Device])
def get_devices(
    status: list[str] | None = Query(default=None),
    pipeline_status: list[str] | None = Query(default=None),
    location: list[str] | None = Query(default=None),
) -> list[dict]:
    """Return device rows, optionally filtered by status / pipeline / location."""
    df = filter_devices(load_devices(), status, pipeline_status, location)
    return df.to_dict(orient="records")


@app.get("/kpis", response_model=KpiSummary)
def get_kpis(
    status: list[str] | None = Query(default=None),
    pipeline_status: list[str] | None = Query(default=None),
    location: list[str] | None = Query(default=None),
) -> dict:
    """Aggregated KPIs over the (optionally filtered) device set.

    The same filter parameters as ``/devices`` are accepted, so the dashboard can
    use this endpoint as the single source of truth for KPI values while still
    reacting to the sidebar filters.
    """
    df = filter_devices(load_devices(), status, pipeline_status, location)
    return compute_kpis(df)


@app.get("/trends", response_model=list[TrendPoint])
def get_trends() -> list[dict]:
    """Daily aggregated test-run history (pass rate / pipeline rate / duration)."""
    return compute_trends(load_test_runs())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000)

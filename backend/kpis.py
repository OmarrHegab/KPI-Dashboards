"""Pure KPI computation logic.

Everything here is a plain function over a pandas DataFrame with no FastAPI,
no HTTP, and no file I/O, so it is trivially unit-testable. The HTTP layer in
``api.py`` is a thin wrapper that loads data and calls these functions.

Design notes:
* All rates are guarded against the empty-DataFrame case so they return a
  finite ``0.0`` instead of ``NaN`` -- ``NaN`` is not valid JSON and FastAPI
  would otherwise raise a 500 when every device is filtered out.
* ``today`` is injectable so calibration KPIs are deterministic in tests.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from backend.config import CALIBRATION_SOON_DAYS, SLA_THRESHOLD_SEC


def _rate(mask: pd.Series, total: int) -> float:
    """Percentage of ``True`` values in ``mask`` over ``total`` rows.

    Returns a finite, JSON-safe float (0.0 when there are no rows).
    """
    if total == 0:
        return 0.0
    return round(float(mask.sum()) / total * 100, 1)


def compute_calibration(
    df: pd.DataFrame,
    today: date | None = None,
    soon_days: int = CALIBRATION_SOON_DAYS,
) -> tuple[int, int]:
    """Return ``(overdue, due_soon)`` device counts based on ``calibration_due``.

    * overdue  -> calibration date is strictly before ``today``
    * due_soon -> calibration date is between today and ``today + soon_days``
    """
    if df.empty or "calibration_due" not in df.columns:
        return 0, 0
    today = today or date.today()
    due = pd.to_datetime(df["calibration_due"], format="ISO8601", errors="coerce").dt.date
    valid = due.dropna()
    overdue = int((valid < today).sum())
    horizon = today + pd.Timedelta(days=soon_days)
    due_soon = int(((valid >= today) & (valid <= horizon)).sum())
    return overdue, due_soon


def compute_error_breakdown(df: pd.DataFrame) -> list[dict]:
    """Frequency of each non-empty error code, most common first (Pareto)."""
    if df.empty or "error_code" not in df.columns:
        return []
    codes = df["error_code"].fillna("").astype(str).str.strip()
    codes = codes[codes != ""]
    if codes.empty:
        return []
    counts = codes.value_counts()
    return [{"code": str(code), "count": int(count)} for code, count in counts.items()]


def compute_kpis(
    df: pd.DataFrame,
    today: date | None = None,
    sla_threshold: int = SLA_THRESHOLD_SEC,
) -> dict:
    """Compute the full KPI summary over ``df``.

    Returns a plain dict matching :class:`backend.models.KpiSummary`. Safe on an
    empty DataFrame: every numeric field is a finite, JSON-serialisable value.
    """
    total = len(df)

    durations = (
        pd.to_numeric(df["test_duration_sec"], errors="coerce").dropna()
        if total and "test_duration_sec" in df.columns
        else pd.Series(dtype=float)
    )
    avg_duration = round(float(durations.mean()), 1) if not durations.empty else 0.0
    p95_duration = round(float(durations.quantile(0.95)), 1) if not durations.empty else 0.0
    tests_over_sla = int((durations > sla_threshold).sum()) if not durations.empty else 0

    overdue, due_soon = compute_calibration(df, today=today)

    return {
        "total_devices": total,
        "online_devices": int((df["status"] == "Online").sum()) if total else 0,
        "offline_devices": int((df["status"] == "Offline").sum()) if total else 0,
        "maintenance_devices": (int((df["status"] == "Maintenance").sum()) if total else 0),
        "test_pass_rate": (_rate(df["last_test_result"] == "Pass", total) if total else 0.0),
        "pipeline_success_rate": (
            _rate(df["pipeline_status"] == "Success", total) if total else 0.0
        ),
        "avg_test_duration": avg_duration,
        "p95_test_duration": p95_duration,
        "sla_threshold_sec": sla_threshold,
        "tests_over_sla": tests_over_sla,
        "calibration_overdue": overdue,
        "calibration_due_soon": due_soon,
        "error_code_breakdown": compute_error_breakdown(df),
    }


def filter_devices(
    df: pd.DataFrame,
    statuses: list[str] | None = None,
    pipeline_statuses: list[str] | None = None,
    locations: list[str] | None = None,
) -> pd.DataFrame:
    """Return the subset of ``df`` matching the given filters.

    ``None`` (or an empty list) for a dimension means "no constraint". Kept as a
    pure function so the same filtering logic is shared by the API and is unit
    testable without a running server.
    """
    result = df
    if statuses:
        result = result[result["status"].isin(statuses)]
    if pipeline_statuses:
        result = result[result["pipeline_status"].isin(pipeline_statuses)]
    if locations:
        result = result[result["location"].isin(locations)]
    return result


def compute_trends(runs: pd.DataFrame) -> list[dict]:
    """Aggregate the test-run history into one point per calendar day.

    Returns a chronologically sorted list of dicts matching
    :class:`backend.models.TrendPoint`.
    """
    required = {"run_timestamp", "result", "duration_sec", "pipeline_status"}
    if runs.empty or not required.issubset(runs.columns):
        return []

    data = runs.copy()
    data["day"] = pd.to_datetime(data["run_timestamp"], format="ISO8601", errors="coerce").dt.date
    data = data.dropna(subset=["day"])
    if data.empty:
        return []

    points: list[dict] = []
    for day, group in data.groupby("day"):
        total = len(group)
        durations = pd.to_numeric(group["duration_sec"], errors="coerce").dropna()
        points.append(
            {
                "date": day.isoformat(),
                "total_runs": total,
                "pass_rate": _rate(group["result"] == "Pass", total),
                "pipeline_success_rate": _rate(group["pipeline_status"] == "Success", total),
                "avg_duration": (round(float(durations.mean()), 1) if not durations.empty else 0.0),
            }
        )
    points.sort(key=lambda p: p["date"])
    return points

"""Unit tests for the pure KPI logic (no HTTP, no file I/O)."""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest

from backend.kpis import (
    compute_calibration,
    compute_error_breakdown,
    compute_kpis,
    compute_trends,
    filter_devices,
)
from tests.conftest import TODAY


def test_compute_kpis_known_values(sample_df):
    kpis = compute_kpis(sample_df, today=TODAY)

    assert kpis["total_devices"] == 10
    assert kpis["online_devices"] == 7
    assert kpis["offline_devices"] == 2
    assert kpis["maintenance_devices"] == 1
    assert kpis["test_pass_rate"] == 50.0
    assert kpis["pipeline_success_rate"] == 50.0
    assert kpis["avg_test_duration"] == 55.8
    assert kpis["p95_test_duration"] == 85.5
    assert kpis["sla_threshold_sec"] == 60
    assert kpis["tests_over_sla"] == 5
    assert kpis["calibration_overdue"] == 3
    assert kpis["calibration_due_soon"] == 3


def test_status_counts_sum_to_total(sample_df):
    kpis = compute_kpis(sample_df, today=TODAY)
    assert (
        kpis["online_devices"] + kpis["offline_devices"] + kpis["maintenance_devices"]
        == kpis["total_devices"]
    )


def test_error_breakdown_pareto(sample_df):
    breakdown = compute_kpis(sample_df, today=TODAY)["error_code_breakdown"]
    by_code = {item["code"]: item["count"] for item in breakdown}

    assert by_code["E_CONN"] == 2  # most frequent
    assert set(by_code) == {"E_CONN", "E_TEST", "E_CALIB", "E_TIMEOUT"}
    assert sum(by_code.values()) == 5
    # Pareto order: counts must be non-increasing.
    counts = [item["count"] for item in breakdown]
    assert counts == sorted(counts, reverse=True)
    assert "" not in by_code  # empty error codes excluded


def test_empty_dataframe_returns_finite_json_safe_values(empty_df):
    """Regression: an empty (fully-filtered) set must not yield NaN."""
    kpis = compute_kpis(empty_df, today=TODAY)

    assert kpis["total_devices"] == 0
    rate_keys = (
        "test_pass_rate",
        "pipeline_success_rate",
        "avg_test_duration",
        "p95_test_duration",
    )
    for key in rate_keys:
        value = kpis[key]
        assert isinstance(value, float)
        assert math.isfinite(value), f"{key} must be finite, got {value}"
        assert value == 0.0
    assert kpis["error_code_breakdown"] == []


def test_all_pass(sample_df):
    df = sample_df.copy()
    df["last_test_result"] = "Pass"
    df["pipeline_status"] = "Success"
    kpis = compute_kpis(df, today=TODAY)
    assert kpis["test_pass_rate"] == 100.0
    assert kpis["pipeline_success_rate"] == 100.0


def test_all_fail(sample_df):
    df = sample_df.copy()
    df["last_test_result"] = "Fail"
    df["pipeline_status"] = "Failed"
    kpis = compute_kpis(df, today=TODAY)
    assert kpis["test_pass_rate"] == 0.0
    assert kpis["pipeline_success_rate"] == 0.0


def test_single_row(sample_df):
    kpis = compute_kpis(sample_df.head(1), today=TODAY)
    assert kpis["total_devices"] == 1
    assert kpis["test_pass_rate"] == 100.0
    assert kpis["avg_test_duration"] == 30.0


def test_unknown_status_is_ignored_not_crashing(sample_df):
    df = sample_df.copy()
    df.loc[0, "status"] = "Decommissioned"
    kpis = compute_kpis(df, today=TODAY)
    # Unknown status simply isn't counted in any of the three known buckets.
    assert kpis["online_devices"] == 6
    assert kpis["online_devices"] + kpis["offline_devices"] + kpis["maintenance_devices"] == 9


@pytest.mark.parametrize("rate_key", ["test_pass_rate", "pipeline_success_rate"])
def test_rates_within_bounds(sample_df, rate_key):
    assert 0.0 <= compute_kpis(sample_df, today=TODAY)[rate_key] <= 100.0


def test_calibration_overdue_and_soon():
    df = pd.DataFrame(
        {
            "calibration_due": [
                "2026-06-01",  # overdue
                "2026-06-28",  # overdue (yesterday)
                "2026-07-05",  # due soon
                "2026-07-29",  # due soon (boundary, +30d)
                "2026-08-15",  # healthy
            ]
        }
    )
    overdue, due_soon = compute_calibration(df, today=date(2026, 6, 29))
    assert overdue == 2
    assert due_soon == 2


def test_calibration_handles_unparseable_dates():
    df = pd.DataFrame({"calibration_due": ["not-a-date", "", "2026-06-01"]})
    overdue, due_soon = compute_calibration(df, today=date(2026, 6, 29))
    assert overdue == 1
    assert due_soon == 0


def test_error_breakdown_empty_when_no_errors(sample_df):
    df = sample_df.copy()
    df["error_code"] = ""
    assert compute_error_breakdown(df) == []


def test_tests_over_sla_respects_threshold(sample_df):
    assert compute_kpis(sample_df, today=TODAY, sla_threshold=100)["tests_over_sla"] == 0
    assert compute_kpis(sample_df, today=TODAY, sla_threshold=0)["tests_over_sla"] == 10


class TestFilterDevices:
    def test_no_filters_returns_all(self, sample_df):
        assert len(filter_devices(sample_df)) == 10

    def test_status_filter(self, sample_df):
        assert len(filter_devices(sample_df, statuses=["Online"])) == 7

    def test_combined_filters(self, sample_df):
        result = filter_devices(sample_df, statuses=["Online"], pipeline_statuses=["Failed"])
        assert set(result["device_id"]) == {"M003", "M008"}

    def test_location_filter(self, sample_df):
        assert len(filter_devices(sample_df, locations=["Berlin"])) == 4

    def test_filter_excluding_everything_is_empty(self, sample_df):
        assert filter_devices(sample_df, statuses=["Nonexistent"]).empty


class TestTrends:
    def test_empty_runs(self):
        assert compute_trends(pd.DataFrame()) == []

    def test_missing_columns_returns_empty(self):
        # Defensive: a frame without the required columns must not raise KeyError.
        assert compute_trends(pd.DataFrame({"run_timestamp": ["2026-06-01 09:00"]})) == []

    def test_aggregates_per_day(self):
        runs = pd.DataFrame(
            {
                "run_timestamp": [
                    "2026-06-01 09:00",
                    "2026-06-01 10:00",
                    "2026-06-02 09:00",
                ],
                "result": ["Pass", "Fail", "Pass"],
                "duration_sec": [30, 70, 40],
                "pipeline_status": ["Success", "Failed", "Success"],
            }
        )
        points = compute_trends(runs)
        assert [p["date"] for p in points] == ["2026-06-01", "2026-06-02"]
        assert points[0]["total_runs"] == 2
        assert points[0]["pass_rate"] == 50.0
        assert points[1]["pass_rate"] == 100.0

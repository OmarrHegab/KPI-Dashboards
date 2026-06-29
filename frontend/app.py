"""Streamlit dashboard for the Device KPI API.

Architecture:
* The backend ``/kpis`` endpoint is the single source of truth for KPI values;
  the dashboard passes the sidebar filters to it so the cards stay both
  consistent with the API and reactive to filtering.
* ``/devices`` provides row-level data for tables and chart distributions, and
  ``/trends`` provides the historical test-run series.
* All network access is cached and guarded: if the backend is unreachable the
  user sees a clear message instead of a raw traceback.

Run locally:  streamlit run frontend/app.py   (set BACKEND_URL if not default)
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    # Works when the repo root is on sys.path (tests, `python -m`).
    from frontend.formatting import (
        DEVICE_STATUSES,
        PIPELINE_STATUSES,
        render_status_badge,
    )
except ModuleNotFoundError:
    # `streamlit run frontend/app.py` puts the frontend/ dir on sys.path.
    from formatting import (
        DEVICE_STATUSES,
        PIPELINE_STATUSES,
        render_status_badge,
    )

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = 5
PLOTLY_TEMPLATE = "plotly_dark"
TRANSPARENT = "rgba(0,0,0,0)"

STYLES_FILE = Path(__file__).resolve().parent / "styles.css"

TABLE_COLUMNS = {
    "device_id": "Device ID",
    "device_name": "Device Name",
    "location": "Location",
    "status": "Status",
    "firmware_version": "Firmware",
    "last_test_result": "Last Test Result",
    "test_duration_sec": "Test Duration (s)",
    "pipeline_status": "Pipeline Status",
    "error_code": "Error Code",
    "calibration_due": "Calibration Due",
    "last_test_time": "Last Test Time",
}


# --------------------------------------------------------------------------- #
# Data access (cached + guarded)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=30)
def fetch_json(path: str, params: dict | None = None):
    """GET ``BACKEND_URL + path`` and return parsed JSON.

    Cached for 30s so repeated reruns (every filter toggle) don't hammer the
    backend. Raises ``requests.RequestException`` on any failure for the caller.
    """
    response = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def load_css() -> None:
    if STYLES_FILE.exists():
        st.markdown(
            f"<style>{STYLES_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True
        )


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def style_chart(fig, height: int | None = None):
    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.25},
    )
    if height:
        fig.update_layout(height=height)
    return fig


def mini_bar_chart(series: pd.Series, color: str) -> None:
    chart_df = series.reset_index()
    chart_df.columns = ["category", "count"]
    fig = px.bar(chart_df, x="category", y="count", template=PLOTLY_TEMPLATE)
    fig.update_traces(marker_color=color)
    fig.update_layout(
        height=150,
        margin={"l": 0, "r": 0, "t": 5, "b": 0},
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_device_table(table_df: pd.DataFrame) -> None:
    if table_df.empty:
        st.info("No devices match the selected filters.")
        return

    display_df = table_df.rename(columns=TABLE_COLUMNS)
    wanted = [TABLE_COLUMNS[c] for c in TABLE_COLUMNS if c in table_df.columns]
    display_df = display_df[wanted]

    for col in ("Status", "Last Test Result", "Pipeline Status"):
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(render_status_badge)

    html = display_df.to_html(escape=False, index=False)
    st.markdown(f'<div class="custom-table-wrapper">{html}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Page sections
# --------------------------------------------------------------------------- #
def render_sidebar() -> dict[str, list[str]]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-logo"><span>▰</span> Streamlit +</div>
            <div class="sidebar-title"><h1>Device KPI<br>Dashboard</h1></div>
            <div class="sidebar-section">⚙️ Settings</div>
            """,
            unsafe_allow_html=True,
        )
        status_filter = st.multiselect("Device Status", DEVICE_STATUSES, default=DEVICE_STATUSES)
        pipeline_filter = st.multiselect(
            "Pipeline Status", PIPELINE_STATUSES, default=PIPELINE_STATUSES
        )
        st.divider()
        st.caption("☁️ Backend: FastAPI")
        st.caption("🖥️ Frontend: Streamlit")

    params: dict[str, list[str]] = {}
    if status_filter:
        params["status"] = status_filter
    if pipeline_filter:
        params["pipeline_status"] = pipeline_filter
    return params


def render_kpi_cards(kpis: dict, devices: pd.DataFrame) -> None:
    cols = st.columns(4)

    with cols[0], st.container(border=True):
        st.metric("Total Devices", kpis["total_devices"])
        if not devices.empty:
            mini_bar_chart(devices["status"].value_counts(), "#38bdf8")

    with cols[1], st.container(border=True):
        st.metric("Online Devices", kpis["online_devices"])
        # Availability split -> distinct from the Total-Devices status breakdown.
        availability = pd.Series(
            {
                "Online": kpis["online_devices"],
                "Not Online": kpis["offline_devices"] + kpis["maintenance_devices"],
            }
        )
        mini_bar_chart(availability, "#22c55e")

    with cols[2], st.container(border=True):
        st.metric("Test Pass Rate", f"{kpis['test_pass_rate']:.1f}%")
        if not devices.empty:
            mini_bar_chart(devices["last_test_result"].value_counts(), "#ec4899")

    with cols[3], st.container(border=True):
        st.metric("Pipeline Success", f"{kpis['pipeline_success_rate']:.1f}%")
        if not devices.empty:
            mini_bar_chart(devices["pipeline_status"].value_counts(), "#8b5cf6")


def render_alert_cards(kpis: dict) -> None:
    cols = st.columns(4)
    with cols[0], st.container(border=True):
        st.metric("🔴 Calibration Overdue", kpis["calibration_overdue"])
    with cols[1], st.container(border=True):
        st.metric("🟠 Calibration Due Soon", kpis["calibration_due_soon"])
    with cols[2], st.container(border=True):
        st.metric(f"⏱️ Tests over {kpis['sla_threshold_sec']}s SLA", kpis["tests_over_sla"])
    with cols[3], st.container(border=True):
        st.metric("📈 p95 Duration", f"{kpis['p95_test_duration']:.0f}s")


def render_distribution_charts(devices: pd.DataFrame, kpis: dict) -> None:
    col1, col2 = st.columns(2)

    with col1, st.container(border=True):
        status_counts = devices["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(
            status_counts,
            names="status",
            values="count",
            title="Device Status Distribution",
            template=PLOTLY_TEMPLATE,
            hole=0.45,
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    with col2, st.container(border=True):
        breakdown = kpis.get("error_code_breakdown", [])
        if breakdown:
            err_df = pd.DataFrame(breakdown)
            fig = px.bar(
                err_df,
                x="count",
                y="code",
                orientation="h",
                title="Failure Pareto (Error Codes)",
                template=PLOTLY_TEMPLATE,
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(style_chart(fig), use_container_width=True)
        else:
            st.success("No error codes in the current selection. 🎉")


def render_firmware_chart(devices: pd.DataFrame) -> None:
    with st.container(border=True):
        fw = (
            devices.groupby(["firmware_version", "last_test_result"])
            .size()
            .reset_index(name="count")
        )
        fig = px.bar(
            fw,
            x="firmware_version",
            y="count",
            color="last_test_result",
            title="Test Result by Firmware Version",
            template=PLOTLY_TEMPLATE,
            color_discrete_map={"Pass": "#22c55e", "Fail": "#ef4444"},
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)


def render_duration_chart(devices: pd.DataFrame, kpis: dict) -> None:
    with st.container(border=True):
        fig = px.bar(
            devices,
            x="device_id",
            y="test_duration_sec",
            color="last_test_result",
            title="Test Duration per Device",
            template=PLOTLY_TEMPLATE,
            color_discrete_map={"Pass": "#22c55e", "Fail": "#ef4444"},
        )
        fig.add_hline(
            y=kpis["sla_threshold_sec"],
            line_dash="dash",
            line_color="#fbbf24",
            annotation_text=f"SLA {kpis['sla_threshold_sec']}s",
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)


def render_location_chart(devices: pd.DataFrame) -> None:
    with st.container(border=True):
        loc = devices.groupby(["location", "status"]).size().reset_index(name="count")
        fig = px.bar(
            loc,
            x="location",
            y="count",
            color="status",
            title="Devices by Location",
            template=PLOTLY_TEMPLATE,
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)


def render_trend_chart(trends: list[dict]) -> None:
    if not trends:
        return
    with st.container(border=True):
        trend_df = pd.DataFrame(trends)
        fig = px.line(
            trend_df,
            x="date",
            y=["pass_rate", "pipeline_success_rate"],
            title="Pass Rate & Pipeline Success Over Time",
            template=PLOTLY_TEMPLATE,
            markers=True,
        )
        fig.update_layout(yaxis_title="%", xaxis_title=None)
        st.plotly_chart(style_chart(fig), use_container_width=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Device KPI Dashboard", layout="wide")
    load_css()

    params = render_sidebar()

    try:
        kpis = fetch_json("/kpis", params)
        devices_data = fetch_json("/devices", params)
        trends = fetch_json("/trends")
    except requests.RequestException as exc:
        st.error(f"⚠️ Backend not reachable at {BACKEND_URL}. Is the API running?")
        st.caption(f"Details: {exc}")
        st.stop()

    devices = pd.DataFrame(devices_data)

    st.markdown(
        """
        <div class="main-header">
            <h1>Device KPI Overview</h1>
            <p>Automated KPI monitoring for measurement devices
               in a DevOps / Build Engineering environment</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if devices.empty:
        st.warning("No devices match the selected filters. Adjust the filters in the sidebar.")
        st.stop()

    render_kpi_cards(kpis, devices)
    render_alert_cards(kpis)

    st.subheader("Device Overview")
    render_device_table(devices)

    problems = devices[(devices["status"] != "Online") | (devices["last_test_result"] == "Fail")]
    st.subheader("Problematic Devices")
    render_device_table(problems)

    st.subheader("KPI Visualizations")
    render_distribution_charts(devices, kpis)
    render_firmware_chart(devices)
    render_duration_chart(devices, kpis)
    render_location_chart(devices)

    st.subheader("Trends")
    render_trend_chart(trends)


# Streamlit runs this module as "__main__"; the guard also keeps it importable.
if __name__ == "__main__":
    main()

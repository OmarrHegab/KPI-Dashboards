import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Device KPI Dashboard", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(120deg, #060b12 0%, #101820 100%);
    color: white;
}

[data-testid="stSidebar"] {
    background-color: #020204;
    border-right: 2px solid #1f2937;
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Multiselect selected chips */
span[data-baseweb="tag"] {
    background-color: #1f2937 !important;
    color: #f3f4f6 !important;
    border: 1px solid #374151 !important;
}

span[data-baseweb="tag"] span {
    color: #f3f4f6 !important;
}
            
.block-container {
    padding-top: 3.5rem;
    max-width: 1350px;
}

            .custom-table-wrapper {
    border: 1px solid #263241;
    border-radius: 14px;
    overflow: hidden;
    margin-top: 1rem;
    margin-bottom: 2rem;
    background: linear-gradient(145deg, #101722, #0b111a);
}

.custom-table-wrapper tbody tr:last-child td {
    border-bottom: none !important;
}

.custom-table-wrapper table {
    margin-bottom: 0 !important;
}
            
.custom-table-wrapper table {
    width: 100%;
    border-collapse: collapse;
    color: #e5e7eb;
    font-size: 15px;
}

.custom-table-wrapper thead tr {
    background: rgba(255, 255, 255, 0.04);
}

.custom-table-wrapper th {
    color: #cbd5e1;
    font-weight: 600;
    text-align: left;
    padding: 14px 16px;
    border-bottom: 1px solid #263241;
}

.custom-table-wrapper td {
    padding: 13px 16px;
    border-bottom: 1px solid #263241;
    color: #f3f4f6;
}

.custom-table-wrapper tbody tr:last-child td {
    border-bottom: none !important;
}

.custom-table-wrapper tbody tr:hover {
    background: rgba(255, 255, 255, 0.04);
}
            
.sidebar-logo {
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 3rem;
}

.sidebar-logo span {
    color: #ff4b4b;
}

.sidebar-title h1 {
    font-size: 30px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 2.5rem;
}

.sidebar-section {
    font-size: 25px;
    font-weight: 800;
    margin-bottom: 1.5rem;
}

.main-header h1 {
    font-size: 36px;
    font-weight: 850;
    margin-bottom: 0.25rem;
}

.main-header p {
    color: #b8c0cc;
    font-size: 17px;
    margin-bottom: 2rem;
}

[data-testid="stMetricValue"] {
    font-size: 38px !important;
    font-weight: 800 !important;
}

[data-testid="stMetricLabel"] {
    font-size: 17px !important;
    font-weight: 700 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, #101722, #0b111a);
    border: 1px solid #263241;
    border-radius: 16px;
    padding: 10px;
}

hr {
    border-color: #273242;
}

.stDataFrame {
    border-radius: 14px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

API_URL = "http://backend:8000/devices"

response = requests.get(API_URL)
data = response.json()
df = pd.DataFrame(data)

def render_status_badge(value):
    styles = {
        "Online": "background:#052e16;color:#22c55e;border:1px solid #14532d;",
        "Offline": "background:#3f1010;color:#ff5c5c;border:1px solid #7f1d1d;",
        "Maintenance": "background:#4a2506;color:#fb923c;border:1px solid #9a3412;",
        "Pass": "background:#052e16;color:#22c55e;border:1px solid #14532d;",
        "Fail": "background:#3f1010;color:#ff5c5c;border:1px solid #7f1d1d;",
        "Success": "background:#052e16;color:#22c55e;border:1px solid #14532d;",
        "Failed": "background:#3f1010;color:#ff5c5c;border:1px solid #7f1d1d;",
        "Warning": "background:#4a2506;color:#fb923c;border:1px solid #9a3412;",
    }

    style = styles.get(str(value), "background:#111827;color:#d1d5db;border:1px solid #374151;")
    return f'<span style="{style} padding:4px 10px;border-radius:8px;font-weight:700;font-size:13px;">{value}</span>'


def render_device_table(table_df):
    display_df = table_df.copy()

    display_df = display_df.rename(
        columns={
            "device_id": "Device ID",
            "device_name": "Device Name",
            "status": "Status",
            "last_test_result": "Last Test Result",
            "test_duration_sec": "Test Duration (s)",
            "pipeline_status": "Pipeline Status",
            "last_test_time": "Last Test Time",
        }
    )

    wanted_cols = [
        "Device ID",
        "Device Name",
        "Status",
        "Last Test Result",
        "Test Duration (s)",
        "Pipeline Status",
        "Last Test Time",
    ]

    display_df = display_df[[col for col in wanted_cols if col in display_df.columns]]

    for col in ["Status", "Last Test Result", "Pipeline Status"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(render_status_badge)

    html = display_df.to_html(escape=False, index=False)

    st.markdown(
        f"""
        <div class="custom-table-wrapper">
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <span>▰</span> Streamlit +
    </div>

    <div class="sidebar-title">
        <h1>Device KPI<br>Dashboard</h1>
    </div>

    <div class="sidebar-section">⚙️ Settings</div>
    """, unsafe_allow_html=True)

    status_filter = st.multiselect(
        "Device Status",
        options=df["status"].unique(),
        default=df["status"].unique(),
    )

    pipeline_filter = st.multiselect(
        "Pipeline Status",
        options=df["pipeline_status"].unique(),
        default=df["pipeline_status"].unique(),
    )

    st.divider()
    st.caption("☁️ Backend: FastAPI")
    st.caption("🖥️ Frontend: Streamlit")

df = df[
    (df["status"].isin(status_filter))
    & (df["pipeline_status"].isin(pipeline_filter))
]

total_devices = len(df)
online_devices = (df["status"] == "Online").sum()
pass_rate = (df["last_test_result"] == "Pass").mean() * 100
pipeline_success_rate = (df["pipeline_status"] == "Success").mean() * 100

st.markdown("""
<div class="main-header">
    <h1>Device KPI Overview</h1>
    <p>Automated KPI monitoring for measurement devices in a DevOps / Build Engineering environment</p>
</div>
""", unsafe_allow_html=True)

def mini_bar_chart(series, color):
    chart_df = series.reset_index()
    chart_df.columns = ["category", "count"]

    fig = px.bar(
        chart_df,
        x="category",
        y="count",
        template="plotly_dark",
    )

    fig.update_traces(marker_color=color)

    fig.update_layout(
        height=150,
        margin=dict(l=0, r=0, t=5, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
    )

    st.plotly_chart(fig, use_container_width=True)

kpi_cols = st.columns(4)

with kpi_cols[0]:
    with st.container(border=True):
        st.metric("Total Devices", total_devices)
        mini_bar_chart(df["status"].value_counts(), "#38bdf8")

with kpi_cols[1]:
    with st.container(border=True):
        st.metric("Online Devices", online_devices)
        mini_bar_chart(df["status"].value_counts(), "#22c55e")

with kpi_cols[2]:
    with st.container(border=True):
        st.metric("Test Pass Rate", f"{pass_rate:.1f}%")
        mini_bar_chart(df["last_test_result"].value_counts(), "#ec4899")

with kpi_cols[3]:
    with st.container(border=True):
        st.metric("Pipeline Success", f"{pipeline_success_rate:.1f}%")
        mini_bar_chart(df["pipeline_status"].value_counts(), "#8b5cf6")

problems = df[
    (df["status"] == "Offline")
    | (df["status"] == "Maintenance")
    | (df["last_test_result"] == "Fail")
]

st.subheader("Device Overview")
render_device_table(df)

st.subheader("Problematic Devices")
render_device_table(problems)

st.subheader("KPI Visualizations")

col1, col2 = st.columns(2)

status_counts = df["status"].value_counts().reset_index()
status_counts.columns = ["status", "count"]

fig_status = px.pie(
    status_counts,
    names="status",
    values="count",
    title="Device Status Distribution",
    template="plotly_dark",
)

test_counts = df["last_test_result"].value_counts().reset_index()
test_counts.columns = ["test_result", "count"]

fig_tests = px.bar(
    test_counts,
    x="test_result",
    y="count",
    title="Test Results",
    template="plotly_dark",
)

with col1:
    with st.container(border=True):
        st.plotly_chart(fig_status, use_container_width=True)

with col2:
    with st.container(border=True):
        st.plotly_chart(fig_tests, use_container_width=True)

fig_duration = px.bar(
    df,
    x="device_id",
    y="test_duration_sec",
    color="last_test_result",
    title="Test Duration per Device",
    template="plotly_dark",
)

with st.container(border=True):
    st.plotly_chart(fig_duration, use_container_width=True)
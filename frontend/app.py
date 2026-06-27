import pandas as pd
import streamlit as st
import plotly.express as px
import requests

# python -m streamlit run frontend/app.py
st.set_page_config(page_title="Device KPI Dashboard", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #111827;
}

[data-testid="stSidebar"] section {
    padding-top: 0rem !important;
}

[data-testid="stSidebar"] .block-container {
    padding-top: 0rem !important;
    margin-top: -2rem !important;
}

[data-testid="stSidebar"] * {
    font-size: 16px;
}

[data-testid="stSidebar"] h2 {
    font-size: 24px !important;
    font-weight: 800 !important;
    margin-top: 0rem !important;
}

[data-testid="stSidebar"] h3 {
    font-size: 20px !important;
    font-weight: 700 !important;
}

.block-container {
    padding-top: 2rem;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}
</style>
""", unsafe_allow_html=True)



st.markdown("""
# ⚙️ Siemens-style Device KPI Dashboard
### Automated KPI monitoring for measurement devices in a DevOps / Build Engineering environment
""")

st.success("Connected to FastAPI backend")
st.markdown("[Open API Documentation](http://127.0.0.1:8000/docs)")

API_URL = "http://backend:8000/devices"

response = requests.get(API_URL)
data = response.json()

df = pd.DataFrame(data)

with st.sidebar:
    st.markdown("## Device KPI Dashboard")
    st.markdown("### Settings")

    st.divider()

    status_filter = st.multiselect(
        "Device Status",
        options=df["status"].unique(),
        default=df["status"].unique()
    )

    pipeline_filter = st.multiselect(
        "Pipeline Status",
        options=df["pipeline_status"].unique(),
        default=df["pipeline_status"].unique()
    )

    chart_selection = st.selectbox(
        "Select chart type",
        ("Bar", "Area")
    )

    st.divider()

    st.caption("Backend: FastAPI")
    st.caption("Frontend: Streamlit")


df = df[
    (df["status"].isin(status_filter)) &
    (df["pipeline_status"].isin(pipeline_filter))
]

total_devices = len(df)
online_devices = (df["status"] == "Online").sum()
offline_devices = (df["status"] == "Offline").sum()
pass_rate = (df["last_test_result"] == "Pass").mean() * 100
avg_test_duration = df["test_duration_sec"].mean()
pipeline_success_rate = (df["pipeline_status"] == "Success").mean() * 100
maintenance_devices = (df["status"] == "Maintenance").sum()

st.subheader("Device KPI Overview")

kpi_cols = st.columns(4)

with kpi_cols[0]:
    with st.container(border=True):
        st.metric("Total Devices", total_devices)
        mini_data = df["status"].value_counts()
        st.bar_chart(mini_data, height=120)

with kpi_cols[1]:
    with st.container(border=True):
        st.metric("Online Devices", online_devices)
        mini_data = df["status"].value_counts()
        st.bar_chart(mini_data, height=120)

with kpi_cols[2]:
    with st.container(border=True):
        st.metric("Test Pass Rate", f"{pass_rate:.1f}%")
        mini_data = df["last_test_result"].value_counts()
        st.bar_chart(mini_data, height=120)

with kpi_cols[3]:
    with st.container(border=True):
        st.metric("Pipeline Success", f"{pipeline_success_rate:.1f}%")
        mini_data = df["pipeline_status"].value_counts()
        st.bar_chart(mini_data, height=120)

problems = df[
    (df["status"] == "Offline") |
    (df["status"] == "Maintenance") |
    (df["last_test_result"] == "Fail")
]

st.subheader("Device Overview")
st.dataframe(df, use_container_width=True, height=300)

st.subheader("Problematic Devices")
st.dataframe(problems, use_container_width=True, height=250)

st.subheader("KPI Visualizations")

col5, col6 = st.columns(2)

status_counts = df["status"].value_counts().reset_index()
status_counts.columns = ["status", "count"]

fig_status = px.pie(
    status_counts,
    names="status",
    values="count",
    title="Device Status Distribution"
)
with col5:
    with st.container(border=True):
        st.plotly_chart(fig_status, use_container_width=True)

test_counts = df["last_test_result"].value_counts().reset_index()
test_counts.columns = ["test_result", "count"]

fig_tests = px.bar(
    test_counts,
    x="test_result",
    y="count",
    title="Test Results"
)
with col6:
    with st.container(border=True):
        st.plotly_chart(fig_tests, use_container_width=True)

fig_duration = px.bar(
    df,
    x="device_id",
    y="test_duration_sec",
    color="last_test_result",
    title="Test Duration per Device"
)

with st.container(border=True):
    st.plotly_chart(fig_duration, use_container_width=True)
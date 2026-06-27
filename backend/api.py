import pandas as pd
from fastapi import FastAPI
from pathlib import Path

# python -m uvicorn backend.api:app --reload
app = FastAPI(title="Device KPI API")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "devices.csv"

def load_devices():
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    df = df.fillna("")
    return df

@app.get("/")
def root():
    return {"message": "Device KPI API is running"}


@app.get("/devices")
def get_devices():
    df = load_devices()
    return df.to_dict(orient="records")


@app.get("/kpis")
def get_kpis():
    df = load_devices()

    return {
        "total_devices": len(df),
        "online_devices": int((df["status"] == "Online").sum()),
        "offline_devices": int((df["status"] == "Offline").sum()),
        "maintenance_devices": int((df["status"] == "Maintenance").sum()),
        "test_pass_rate": float((df["last_test_result"] == "Pass").mean() * 100),
        "pipeline_success_rate": float((df["pipeline_status"] == "Success").mean() * 100),
        "avg_test_duration": float(df["test_duration_sec"].mean())
    }
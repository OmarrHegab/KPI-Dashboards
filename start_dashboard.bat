@echo off
cd /d C:\Users\omarh\OneDrive\Desktop\device-kpi-dashboard
start http://localhost:8501
docker compose up --build
pause
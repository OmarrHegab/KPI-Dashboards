@echo off
REM Launch the dashboard from wherever this repo is checked out.
cd /d "%~dp0"
start http://localhost:8501
docker compose up --build
pause

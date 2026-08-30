@echo off
cd /d "%~dp0.."
start "Backend" /min cmd /c "ecological_env\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > %TEMP%\eco_backend.log 2>&1"

@echo off
echo Starting FastAPI Backend for Hermes Agent System...
cd /d "%~dp0.."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

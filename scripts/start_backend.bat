@echo off
echo Starting FastAPI Backend for Hermes Agent System...
cd /d "%~dp0.."
REM 释放可能占用的端口
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000" ^| find "LISTENING"') do (
    taskkill //F //PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul
REM 使用项目的虚拟环境 (Python 3.12.12) 和端口 8000
echo Starting backend on port 8000...
%~dp0..\ecological_env\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

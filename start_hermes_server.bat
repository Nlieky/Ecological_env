@echo off
REM ========================================
REM Hermes API Server Startup Script
REM ========================================
REM
REM This script starts the Hermes API Server with correct configuration.
REM Make sure D:\Hermes\config.yaml and D:\Hermes\.env exist and are correct.
REM

echo ========================================
echo Starting Hermes API Server
echo ========================================
echo.

REM Critical: Set HERMES_HOME before launching Python
set HERMES_HOME=D:\Hermes

REM Set API Server configuration
set API_SERVER_KEY=admin123456
set API_SERVER_PORT=8642
set API_SERVER_HOST=127.0.0.1
set GATEWAY_ALLOW_ALL_USERS=true

REM Change to Hermes directory
cd /d D:\Hermes\hermes-agent

echo Configuration:
echo   HERMES_HOME=%HERMES_HOME%
echo   API_SERVER_KEY=%API_SERVER_KEY%
echo   API_SERVER_PORT=%API_SERVER_PORT%
echo   API_SERVER_HOST=%API_SERVER_HOST%
echo.
echo Config files:
echo   %HERMES_HOME%\config.yaml
echo   %HERMES_HOME%\.env
echo.
echo ========================================
echo Starting Hermes Gateway...
echo ========================================
echo.

REM Start the gateway
python -m gateway.run

pause

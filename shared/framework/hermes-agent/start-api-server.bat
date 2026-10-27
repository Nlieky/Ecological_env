@echo off
REM Hermes API Server Startup Script

REM Set API Server Configuration
set API_SERVER_KEY=test-key-123
set API_SERVER_PORT=8642
set API_SERVER_HOST=127.0.0.1
set API_SERVER_CORS_ORIGINS=*

REM Set LLM Configuration
set LLM_BASE_URL=http://172.xx.xx.xx:30000/v1
set LLM_API_KEY=sk-test
set LLM_MODEL=ctgu-vlm

REM Start Hermes Gateway
venv\Scripts\hermes.exe gateway run --replace --accept-hooks

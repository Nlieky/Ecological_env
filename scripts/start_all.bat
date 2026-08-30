@echo off
chcp 65001 >nul
title 废水监测系统 - 全服务启动
echo ============================================
echo   废水监测系统 全服务一键启动
echo   InfluxDB / Agent / Backend / Frontend / 模拟器
echo ============================================
echo.

cd /d "%~dp0.."
set "ROOT=%cd%"
set "PY=%ROOT%\ecological_env\Scripts\python.exe"

REM ── 端口占用清理(哪个占就杀哪个;没占用跳过) ──
echo [0/5] 检查端口占用...
for %%p in (8086 8642 8000 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":%%p" ^| find "LISTENING"') do (
        echo       端口 %%p 被 PID %%a 占用,结束它
        taskkill //F //PID %%a >nul 2>&1
    )
)
timeout /t 2 /nobreak >nul

REM ── 1. InfluxDB(数据已持久化在默认目录,重启不丢) ──
echo [1/5] 启动 InfluxDB :8086 ...
if not exist "D:\influxdb2-2.7.12-windows\influxd.exe" (
    echo   [警告] 未找到 D:\influxdb2-2.7.12-windows\influxd.exe,跳过
) else (
    start "InfluxDB" /min cmd /c ""D:\influxdb2-2.7.12-windows\influxd.exe" > "%TEMP%\eco_influxdb.log" 2>&1"
)

REM ── 2. 模拟器(持续写新监测点;不需要可注释掉这段) ──
echo [2/5] 启动数据模拟器(10s/点) ...
start "DataSimulator" /min cmd /c ""%PY%" "%ROOT%\shared\data\data_simulator.py" --tick 10 > "%TEMP%\eco_simulator.log" 2>&1"

REM ── 3. Agent 服务(主智能体+动作短路器) ──
echo [3/5] 启动 Agent 服务 :8642 ...
start "AgentService" /min cmd /c ""%PY%" "%ROOT%\scripts\start_agent.py" > "%TEMP%\eco_agent.log" 2>&1"

REM ── 4. Backend(FastAPI) ──
echo [4/5] 启动 Backend :8000 ...
timeout /t 3 /nobreak >nul
start "Backend" /min cmd /c ""%PY%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > "%TEMP%\eco_backend.log" 2>&1"

REM ── 5. Frontend(Vite) ──
echo [5/5] 启动 Frontend :5173 ...
start "Frontend" /min cmd /c "cd /d "%ROOT%\frontend" && npm run dev > "%TEMP%\eco_frontend.log" 2>&1"

echo.
echo 等待服务就绪(~15s)...
timeout /t 15 /nobreak >nul

echo ────────── 健康检查 ──────────
curl -s -o nul -w "  InfluxDB  :8086  %%{http_code}\n" http://localhost:8086/health
curl -s -o nul -w "  Frontend  :5173  %%{http_code}\n" http://localhost:5173/
"%PY%" -c "import urllib.request,sys;
try:
    r=urllib.request.urlopen('http://localhost:8000/api/health',timeout=5); print('  Backend   :8000  %s' % r.status)
except Exception as e: print('  Backend   :8000  FAIL', e)
try:
    r=urllib.request.urlopen('http://localhost:8642/health',timeout=5); print('  Agent     :8642  %s' % r.status)
except Exception as e: print('  Agent     :8642  FAIL', e)"

echo.
echo ══════════════════════════════════════════
echo   全部服务已在独立窗口运行(最小化到任务栏)
echo   入口: http://localhost:5173/dashboard
echo   日志: %%TEMP%%\eco_*.log
echo   停止: 关闭对应任务栏窗口,或双击 scripts\stop_all.bat
echo ══════════════════════════════════════════
pause

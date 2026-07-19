@echo off
echo ======================================================================
echo 废水监测系统 - Agent 服务重启脚本
echo ======================================================================
echo.
echo 此脚本将：
echo 1. 停止现有的 Agent 服务进程
echo 2. 启动修复后的 Agent 服务
echo 3. 运行功能验证测试
echo.
echo ======================================================================
echo.

echo [步骤 1/3] 停止现有服务进程...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo   ✓ 已停止现有 Python 进程
) else (
    echo   - 没有发现运行中的 Python 进程
)
timeout /t 2 >nul

echo.
echo [步骤 2/3] 启动修复后的 Agent 服务...
echo   服务将在后台启动，端口: 8642
start /B python scripts\start_agent.py > logs\agent_service.log 2>&1
echo   ✓ Agent 服务启动中...
timeout /t 5 >nul

echo.
echo [步骤 3/3] 运行功能验证测试...
python scripts\test_agent_api.py

echo.
echo ======================================================================
echo 服务状态检查
echo ======================================================================
curl -s http://localhost:8642/health
echo.
echo.
echo 如果看到 {"status": "healthy", "agent_initialized": True}，则服务正常运行
echo.
echo 服务日志位置: logs\agent_service.log
echo 查看日志: type logs\agent_service.log
echo ======================================================================
pause

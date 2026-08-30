@echo off
chcp 65001 >nul
title 废水监测系统 - 停止全部服务
echo 停止全部服务...

REM 按窗口标题关(独立窗口方式启动的)
for %%t in (InfluxDB DataSimulator AgentService Backend Frontend) do (
    echo   关闭 %%t
    taskkill //F //FI "WINDOWTITLE eq %%t*" >nul 2>&1
)
REM 兜底:按端口清残留
for %%p in (8086 8642 8000 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":%%p" ^| find "LISTENING"') do (
        taskkill //F //PID %%a >nul 2>&1
    )
)
echo 完成。全部服务已停止。
pause

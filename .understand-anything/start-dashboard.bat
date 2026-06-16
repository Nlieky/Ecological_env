@echo off
setlocal

REM 设置项目目录
set GRAPH_DIR=E:\project\Ecological_env

REM 设置仪表板目录
set DASHBOARD_DIR=C:\Users\86157\.claude\plugins\marketplaces\understand-anything\understand-anything-plugin\packages\dashboard

echo 启动 Understand Anything 仪表板...
echo 项目目录: %GRAPH_DIR%
echo.

cd /d "%DASHBOARD_DIR%"
pnpm run dev -- --host 127.0.0.1 --port 5173

pause

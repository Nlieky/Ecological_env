@echo off
REM ========================================
REM Hermes API Server 启动脚本
REM (主智能体 workspace + 4 个子智能体)
REM ========================================

echo ========================================
REM 启动 Hermes API Server - 多智能体系统
REM ========================================
echo.

REM 关键配置：设置 HERMES_HOME 指向主智能体目录
set HERMES_HOME=E:\project\Ecological_env\workspace

REM API Server 配置
set API_SERVER_KEY=admin123456
set API_SERVER_PORT=8642
set API_SERVER_HOST=127.0.0.1
set GATEWAY_ALLOW_ALL_USERS=true

REM 切换到 Hermes 目录
cd /d D:\Hermes\hermes-agent

echo ========================================
echo 配置信息
echo ========================================
echo.
echo 主智能体 (HERMES_HOME):
echo   %HERMES_HOME%
echo.
echo API Server:
echo   端口: %API_SERVER_PORT%
echo   主机: %API_SERVER_HOST%
echo.
echo 主智能体文件:
echo   配置: %HERMES_HOME%\config.yaml
echo   身份: %HERMES_HOME%\SOUL.md
echo   规范: %HERMES_HOME%\AGENTS.md
echo   记忆: %HERMES_HOME%\MEMORY.md
echo.
echo 主智能体编排技能:
echo   - skills/orchestrator-core
echo.
echo 子智能体位置:
echo   - ../subagents/multi-dimensional-data-perception-agent
echo   - ../subagents/anomaly-detection-agent
echo   - ../subagents/rule-reasoning-agent
echo   - ../subagents/disposition-execution-agent
echo.
echo ========================================
echo 启动中...
echo ========================================
echo.

python -m gateway.run

pause

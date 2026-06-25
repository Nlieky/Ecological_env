@echo off
rem Hermes Agent Gateway - 废水监测系统项目专用
rem 从项目目录启动，使用项目的 .hermes/config.yaml 配置

cd /d E:\project\Ecological_env
set "HERMES_HOME=E:\project\Ecological_env"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=D:\Hermes\hermes-agent\venv"

echo Starting Hermes API Server from project directory...
echo Using config: %HERMES_HOME%\.hermes\config.yaml
echo Skills directories will be loaded from project config...
echo.

D:\Hermes\hermes-agent\venv\Scripts\pythonw.exe -m hermes_cli.main gateway run

@echo off
REM 废水监测后端启动脚本
REM 使用项目虚拟环境 ecological_env 的 Python 来运行后端

echo ========================================
echo 废水监测后端启动
echo ========================================
echo.

REM 设置项目目录
cd /d %~dp0..\

REM 设置 Python 路径 (使用项目虚拟环境)
set PYTHON_PATH=%~dp0..\ecological_env\Scripts\python.exe

echo 项目目录: %CD%
echo 使用 Python: %PYTHON_PATH%
"%PYTHON_PATH%" --version
echo.

REM 启动后端
echo 启动 FastAPI 后端...
"%PYTHON_PATH%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

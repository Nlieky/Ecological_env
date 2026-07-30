FROM python:3.12-slim

WORKDIR /app

# 系统依赖(gcc/g++ 编译 scipy/sklearn 等;curl 健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖(用项目根 requirements.txt,不再用已删除的 requirements-core.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 项目代码
COPY . .

# Hermes Agent 框架(vendored 在 shared/framework/hermes-agent/)——editable 安装,
# 让 hermes_constants / agent.* 等顶层模块可 import(本地 venv 就是这么装的),
# 同时拉框架的核心依赖(openai 等,requirements.txt 里没有)
RUN pip install --no-cache-dir -e shared/framework/hermes-agent

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 后端(8000)+ 主智能体 Agent 服务(8642)
EXPOSE 8000 8642

# 默认起后端;docker-compose 里用 command 覆盖以起 agent 服务
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

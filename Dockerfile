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

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 后端(8000)+ 主智能体 Agent 服务(8642)
EXPOSE 8000 8642

# 默认起后端;docker-compose 里用 command 覆盖以起 agent 服务
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

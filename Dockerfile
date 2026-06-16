FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（使用精简版本）
COPY requirements-core.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements-core.txt

# 复制整个项目
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app:/app/middleware:/app/subagents
ENV PYTHONUNBUFFERED=1

EXPOSE 8080 5001 5000

# 默认启动 Web 服务（可被覆盖）
CMD ["python", "-m", "middleware.web_interface"]

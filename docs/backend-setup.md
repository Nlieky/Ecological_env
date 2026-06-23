# 后端开发环境设置

## Python 环境

本项目使用 **uv** 创建的 Python 3.12 虚拟环境。

### 环境位置

```
E:\project\Ecological_env\ecological_env\
```

### 安装依赖

```bash
# 使用 uv 安装依赖
cd E:\project\Ecological_env
uv pip install --python ecological_env/Scripts/python.exe -r requirements.txt
```

### 启动后端

```bash
# 方式1: 直接启动
cd E:\project\Ecological_env
ecological_env\Scripts\uvicorn.exe backend.main:app --reload

# 方式2: 使用启动脚本
cd E:\project\Ecological_env
scripts\start_backend.bat
```

### 访问接口

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health
- **Hermes 系统**: http://localhost:8000/api/hermes/system
- **Prometheus 指标**: http://localhost:8000/metrics

## 前置条件

1. **Hermes API Server** 运行在 `http://localhost:8642`
2. **环境变量** 已配置（复制 `.env.example` 到 `.env` 并填入实际值）

## 故障排查

### ModuleNotFoundError

如果遇到模块缺失错误，重新安装依赖：

```bash
uv pip install --python ecological_env/Scripts/python.exe -r requirements.txt
```

### Hermes API Server 连接失败

确保 Hermes API Server 正在运行：

```bash
# 检查连接
curl http://localhost:8642/health
```

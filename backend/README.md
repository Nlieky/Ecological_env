# 废水监测系统后端 API

## 系统定位

**本后端通过 Hermes API Server 调用已完成的 Hermes 智能体系统**

Hermes 智能体系统是核心创新（位于 `workspace/` 和 `subagents/`），后端只是为它提供 HTTP 访问能力。

## 核心接口

### 1. 查询接口 `/api/query`

调用 Hermes 主智能体，展示其完整决策过程：

- **决策路径**：展示主智能体走了决策树的哪些分支
- **子智能体调用链**：哪些子智能体被调用
- **数据溯源**：数据来源
- **LLM 推理过程**：意图识别和决策逻辑

### 2. Hermes 系统信息 `/api/hermes/system`

展示 Hermes 系统的完整结构：

- 主智能体信息和决策树
- 4 个子智能体详情
- 三库一体资源位置

### 3. 健康检查 `/api/health`

系统健康状态和 Hermes API Server 连接状态

## 快速开始

### 前置条件

1. Hermes API Server 运行在 `http://localhost:8642`
2. 项目根目录 `.env` 文件已配置

### 安装依赖

```bash
pip install -e .
```

### 启动服务

```bash
# 方式1: 直接启动
python -m uvicorn backend.main:app --reload

# 方式2: 使用启动脚本
./scripts/start_backend.sh  # Linux/Mac
scripts\\start_backend.bat   # Windows
```

### 访问文档

```
http://localhost:8000/docs
```

## 架构

```
前端 → FastAPI (8000) → Hermes API Server (8642) → 主智能体 → 4 个子智能体
```

## 主智能体决策树

1. **需要数据吗？** → data-perception
2. **需要异常检测吗？** → anomaly-detection
3. **需要违规判定吗？** → rule-reasoning
4. **需要预警/工单吗？** → disposition-execution
5. **整合结果** → 自然语言回答

## 示例查询

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近24小时出水COD异常吗？"}'
```

## Prometheus 指标

访问 `http://localhost:8000/metrics` 查看指标：

- `hermes_query_total` - Hermes 查询总数
- `decision_tree_branch_taken_total` - 决策树分支执行次数
- `sub_agent_called_total` - 子智能体调用次数

详细架构见：`docs/architecture/technical-design.md`

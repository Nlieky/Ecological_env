# TOOLS.md - Local Notes

技能（skills）定义工具**怎么用**。这个文件记**你这套环境特有的**东西——命令、路径、端口。

## 编排工具

主智能体运行时挂载项目根 `skills/orchestrator-core/` 的编排工具（详见其 `SKILL.md` 与 `scripts/tool_registration.py`）：

- `call_subagent(subagent_name, task, context?)` — 调用子智能体（主要工具）
- `list_subagents()` — 列出可用子智能体
- `create_session()` — 创建会话目录
- `read_result()` — **已废弃**（call_subagent 返回的摘要已足够，不需要读完整文件）

子智能体经**共享入口** `subagent_entry.py` 以 subprocess 启动，靠环境变量定位：

- `HERMES_HOME` = 该子智能体目录（身份文件 + skills/ 从这里读）
- `SUBAGENT_NAME` = 子智能体名
- `SESSION_DIR` = 公共会话区（`task.json` + 各 `*_result.json` 链式传递）

## 数据路径

| 数据 | 真实路径 |
|------|---------|
| 时序监测数据 | InfluxDB 2.7（bucket=`monitoring-real`, org=`ecological_env`） |
| 日志库 | `shared/data/ecological_logs.db`（SQLite） |
| 算子库 | `shared/operators/`（`machine_learning/` · `specialized/` · `deep_learning/`） |
| 知识库 | `shared/knowledge/`（法规 / 工艺 / 违规模式 / 专家经验） |
| 可视化工具 | `shared/viz/build_chart.py` |

## 后端服务

| 项 | 值 |
|----|-----|
| 主文件 | `backend/main.py` |
| 框架 | FastAPI |
| 端口 | 8000 |
| Agent 服务 | `scripts/start_agent.py`（Hermes API，端口 8642） |
| InfluxDB | `localhost:8086`（原生 Windows 二进制） |
| Prometheus | `localhost:9090` |
| Grafana | `localhost:3000` |

## 关键端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/query` | POST | 主智能体查询（同步） |
| `/api/query/stream` | POST | 主智能体查询（SSE 流式 + 进度） |
| `/api/v1/monitoring/realtime` | GET | 实时监测数据 |
| `/api/v1/data/history` | GET | 历史数据 |
| `/api/v1/conversations` | GET | 对话历史 |
| `/api/logs/trace/{session_id}` | GET | 审计追踪 |
| `/docs` | GET | API 文档 |

---

把有助于你干活的都加进来。这是你的备忘单。

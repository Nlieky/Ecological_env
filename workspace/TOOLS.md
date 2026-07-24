# TOOLS.md - Local Notes

技能（skills）定义工具**怎么用**。这个文件记**你这套环境特有的**东西——命令、路径、端口。

## Runtime

主智能体由 LLM 驱动，运行时只挂载编排工具（详见 `skills/orchestrator-core/SKILL.md` 与 `tool_registration.py`）：

- `call_subagent(subagent_name, task, context?)` — 调用子智能体
- `list_subagents()` — 列出可用子智能体
- `create_session()` / `read_result()` — 会话与结果读取

子智能体经**共享入口** `subagent_entry.py` 以 subprocess 启动，靠环境变量定位：

- `HERMES_HOME` = 该子智能体目录（身份文件 + skills/ 从这里读）
- `SUBAGENT_NAME` = 子智能体名
- `SESSION_DIR` = 公共会话区（`task.json` + 各 `*_result.json` 链式传递）

## 数据路径（以代码实际读取为准）

| 数据 | 真实路径 |
|------|---------|
| 进水数据 | `data/pollution_water_in.csv` |
| 出水数据 | `data/pollution_water_out.csv` |
| 日志库 | `shared/data/ecological_logs.db` |
| 算子库 | `shared/operators/`（`machine_learning/` · `specialized/` · `deep_learning/`） |
| 知识库 | `shared/knowledge/` |

> 注：取数脚本 `get_data.py` 与后端 `monitoring_data_loader.py` 都读顶层 `data/`，不是 `shared/data/`。

## 后端服务

| 项 | 值 |
|----|-----|
| 主文件 | `backend/main.py` |
| 框架 | FastAPI |
| 端口 | 8000 |
| Agent 服务 | `scripts/start_agent.py`（Hermes API，端口 8642） |

## 关键端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/query` | POST | 主智能体查询（同步） |
| `/api/query/stream` | POST | 主智能体查询（SSE 流式 + 进度） |
| `/api/v1/monitoring/realtime` | GET | 实时监测（历史数据最新行模拟） |
| `/api/v1/conversations` | GET | 对话历史 |
| `/docs` | GET | API 文档 |

---

把有助于你干活的都加进来。这是你的备忘单。

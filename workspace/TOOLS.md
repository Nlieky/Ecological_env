# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Environment Configuration

### Backend API

| 配置项 | 值 |
|-------|-----|
| 主文件 | backend/main.py |
| 端口 | 8000 |
| 主机 | 0.0.0.0 |
| 框架 | FastAPI |

### Data Paths

| 数据类型 | 路径 |
|---------|------|
| 进水数据 | shared/data/pollution_water_in.csv |
| 出水数据 | shared/data/pollution_water_out.csv |
| 历史数据 | shared/data/historical/ |
| 知识库 | shared/knowledge/ |
| 算子库 | shared/operators/ |

### Sub-Agent Paths

| 子智能体 | 路径 |
|---------|------|
| multi-dimensional-data-perception-agent | subagents/multi-dimensional-data-perception-agent/ |
| anomaly-detection-agent | subagents/anomaly-detection-agent/ |
| rule-reasoning-agent | subagents/rule-reasoning-agent/ |
| disposition-execution-agent | subagents/disposition-execution-agent/ |

### Endpoints

| 端点 | 方法 | 功能 |
|------|------|------|
| /health | GET | 健康检查 |
| /metrics | GET | Prometheus指标 |
| /api/dual-stream | POST | 接收双数据流 |
| /api/analyze/stats | GET | 获取分析器状态 |
| /api/query | POST | 主智能体查询接口 |
| /docs | GET | API文档 |

### Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Hermes API**: http://localhost:8642

---

Add whatever helps you do your job. This is your cheat sheet.

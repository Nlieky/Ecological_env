# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Environment Configuration

### Flask Middleware

| 配置项 | 值 |
|-------|-----|
| 路径 | middleware/app_orchestrator.py |
| 端口 | 5000 |
| 主机 | 0.0.0.0 |

### Data Paths

| 数据类型 | 路径 |
|---------|------|
| 进水数据 | data/pollution_water_in.csv |
| 出水数据 | data/pollution_water_out.csv |
| 历史数据 | shared/data/historical/ |
| 知识库 | shared/knowledge/ |

### Sub-Agent Scripts

| 子智能体 | 脚本路径 |
|---------|---------|
| data-governance-agent | subagents/data-governance-agent/skills/data-governance-core/scripts/ |
| feature-analysis-agent | subagents/feature-analysis-agent/skills/feature-analysis-core/scripts/ |
| anomaly-detection-agent | subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/ |
| rule-reasoning-agent | subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/ |

### Endpoints

| 端点 | 方法 | 功能 |
|------|------|------|
| /health | GET | 健康检查 |
| /metrics | GET | Prometheus指标 |
| /api/dual-stream | POST | 接收双数据流 |
| /api/analyze/stats | GET | 获取分析器状态 |

### Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)

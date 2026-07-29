# HEARTBEAT.md - 周期检查清单

> heartbeat 触发时，轮换检查以下项目（每次挑 2-3 项，不必全查）。
> 无异常时回 HEARTBEAT_OK；有情况时主动告知用户。

## 检查项

### 数据连续性
- InfluxDB 最近数据到什么时候？（`/api/v1/data/history?time_range=1h`）
- 是否有数据中断（超过预期无新数据）？

### 系统健康
- 后端健康：`/api/health` 是否 200？agent_initialized 是否 true？
- Agent 服务：`:8642/health` 是否 200？

### 异常回顾
- 最近查询有没有检出的异常？（查 `sessions/` 最新 `anomaly_result.json`）
- 有没有未处理的高风险违规？

## 通知阈值

- **立即通知**：高风险违规（suspicion=high）、数据中断 >6h、服务宕机
- **安静**：一切正常、深夜（23:00-08:00）、距上次检查 <30min

## 后台工作（无异常时可做）

- 整理 `memory/` 文件，更新 `MEMORY.md`（见 AGENTS.md Memory Maintenance）

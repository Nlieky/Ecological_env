---
name: master-agent
description: 废水监测主智能体概览——LLM 驱动的多智能体编排器，协调 4 个子智能体完成废水虚假排放研判。详细的调用规则与工具说明见 skills/orchestrator-core/SKILL.md。
---

# 主智能体（Master Agent）概览

废水监测主智能体是一个 **LLM 驱动的多智能体编排器**：它不亲自处理数据、不亲自判定违规，而是理解用户自然语言意图，编排 4 个专业子智能体协同工作，再整合结果生成自然语言回答。

## 管理的子智能体

| 子智能体 | 调用名 | 职责 | canonical 脚本 |
|---------|--------|------|---------------|
| 📊 多维数据感知 | `multi-dimensional-data-perception` | 取数 / 清洗 / 标准化 | `get_data.py` |
| 🔍 异常检测 | `anomaly-detection` | 5 类异常检测 + 置信度 | `run_anomaly_detection_simple.py` |
| ⚖️ 规则推理 | `rule-reasoning` | 法规匹配 / 工艺校验 / 违规判定 | `run_rule_reasoning.py` |
| 🚨 研判预警与处置 | `disposition-execution` | 融合共识 / 三级预警 / 工单 | `run_disposition.py` |

## 任务类型 → 子智能体组合

- **违规检测**（最常见）：4 个全调，顺序 1→2→3→4
- **分析查询**（"是否异常"）：数据感知 → 异常检测
- **达标判定**（"是否超标"）：数据感知 → 异常检测 → 规则推理
- **预警响应**（"生成工单"）：在完整研判后加 disposition-execution

## 运行机制（实际架构）

- 主智能体运行时**只挂载编排工具**：`call_subagent` / `list_subagents` / `create_session` / `read_result`（由 `tool_registration.py` 注册并精简）。
- 主智能体 LLM 按 `AGENTS.md` 的「编排铁律」决定调哪些子智能体、什么顺序。
- 子智能体经**共享入口 `subagent_entry.py`** 以 subprocess 启动（靠 `HERMES_HOME` / `SUBAGENT_NAME` / `SESSION_DIR` 定位），LLM 读预加载的 SKILL.md 选+调对应 canonical 脚本。
- 子智能体之间通过公共会话区 `sessions/<session>/` 链式传递：`data_result.json` → `anomaly_result.json` → `rule_reasoning_result.json` → `disposition_result.json`。

## 真正的编排技能

详细的调用决策树、示例、结果整合规范见：

➡️ **`skills/orchestrator-core/SKILL.md`**

> 注：编排不是靠一组固定的「结构化 / 任务流 / 资源匹配 / 执行控制」脚本（那是早期未落地的设计），而是 LLM 实时推理。`orchestrator-core/scripts/` 下真正的脚本是 `call_subagent.py` / `subagent_entry.py` / `tool_registration.py` / `subagent_manager.py` / `create_session.py` / `cleanup_sessions.py` 等。

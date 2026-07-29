---
name: disposition-execution-core
description: 研判处置——读取规则推理的嫌疑等级，映射到处置行动（立即调查/现场核查/持续监控），生成工单与报告。当任务涉及"预警"、"工单"、"处置"、"通知"、"怎么处理"时使用。务必使用——研判链路的最后一环，把技术判定翻译成可执行的行动。
---

# 研判处置技能

## 你做什么

你调用一个脚本（`run_disposition.py`），它读取规则推理的嫌疑等级，映射到处置行动 + 生成工单。脚本自动完成所有工作：
- 从 `SESSION_DIR/rule_reasoning_result.json` 读嫌疑等级 + 违规类型 + 证据链
- 嫌疑等级 → 处置行动映射（high→立即调查 / medium→核查 / low→监控 / none→无违规）
- 生成工单（核查要点 + 法规引用 + 处置建议）
- 生成预警报告

**你的工作就是：调脚本 → 确认完成。**

## 怎么调

```bash
python "$HERMES_HOME/skills/disposition-execution-core/scripts/run_disposition.py"
```

不需要传参数。脚本自动从 SESSION_DIR 读上游结果。

## 执行流程

**两步完成，不多做：**

1. 用 `skill_view` 读本技能（你现在在读）
2. 用 `terminal` 运行脚本
3. 回复："✅ 脚本执行完成"

**就这三步。不需要其他任何操作。**

### 不要做的事（每多做一步浪费 ~6s）

- ❌ 不要先 `echo` / `ls` / `pwd` 检查环境——系统已设置好
- ❌ 不要先检查上游文件是否存在——脚本内部自动检查
- ❌ 不要跑完脚本后再验证结果——结果文件由主智能体整合
- ❌ 不要解析 JSON 或总结结果

### 为什么

每多一步探索 = 1 次 LLM 调用（~6s）。直接 skill_view → 跑脚本 → 确认完成，3 步搞定。

## 嫌疑等级 → 处置行动

| 嫌疑等级 | 处置行动 | 工单 |
|---|---|---|
| high | 立即调查取证 | 出工单（核查 + 法规 + 取证建议） |
| medium | 现场核查 | 出工单（核查要点） |
| low | 持续监控 | 出监控建议 |
| none | 无违规 | 正常报告 |

**你不再自己融合置信度或分级预警**——规则推理已经综合了异常 + 违规成嫌疑等级。你只消费它，翻译成行动。旧的三级预警（一般/较重/严重）和融合共识（ConsensusEngine）已废弃。

## 为什么只调脚本、不做别的

**不解析 JSON / 不生成报告**：你的结果由主智能体直接读摘要整合成最终回答。

**不手写文件**：你手写会覆盖上游的 `rule_reasoning_result.json`（曾经发生过，编造的键名破坏了链式传递）。

**不做违规判定**：嫌疑等级由规则推理给出。你消费它，不重新判定。

**不做异常检测**：那是异常检测的活。

## 脚本输出

保存到 `disposition_result.json`（SESSION_DIR 或子智能体默认目录），包含：
- `suspicion_level`：嫌疑等级（high/medium/low/none）
- `action`：处置行动（立即调查取证/现场核查/持续监控/无违规）
- `work_order`：工单（id + inspection_points + legal_references + recommended_actions）
- `report`：预警报告
- `evidence_points`：来自规则推理的证据链

主智能体读摘要整合成最终回答。

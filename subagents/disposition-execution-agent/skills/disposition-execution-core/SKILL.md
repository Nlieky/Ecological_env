---
name: disposition-execution-core
description: 预警分级和处置执行。**触发条件**：当用户提到"预警"、"工单"、"处置"、"生成预警"、"创建工单"、"通知"时调用。基于违规判定结果进行融合共识、预警分级、工单生成和报告输出。需要违规判定结果作为输入。
---

# 预警分级和处置执行技能

## 核心规则

**只做一件事：调用脚本，传递结果。不要解析，不要生成报告。**

## ⚠️ 执行纪律（严格白名单，违反必失败）

**你只能执行下面"执行流程"里那一条 `python` 命令，敲完就停。严禁任何其他终端操作：**
- ❌ 禁止 `cat >` / `>>` / `echo >` 写入、修改、删除任何文件——结果只能由脚本产出，你一写就会**覆盖/污染上游结果**（曾发生：编造 anomaly_result 覆盖了真实结果，键名都是瞎编的）
- ❌ 禁止 `python -c` / 内联代码 / 自己写脚本
- ❌ 禁止 `ls` / `find` / `head` / `tail` / `grep` / `cat` 读文件或探索目录
- ❌ 禁止 `cd` / `pwd` / `echo` 等闲逛操作
- ✅ **唯一允许**：直接 `python "$HERMES_HOME/skills/disposition-execution-core/scripts/run_disposition.py"`

输入（异常/违规结果）会自动从 SESSION_DIR 读取，不需要你研究脚本。之前有子智能体因 `cat >` 编造结果、`python -c` 跑内联代码、`find` 乱翻，烧光迭代还污染数据导致整条链失败——别重蹈覆辙。

## 执行流程

1. **调用脚本**
   ```bash
   python "$HERMES_HOME/skills/disposition-execution-core/scripts/run_disposition.py"
   ```

2. **确认执行完成**
   响应："✅ 脚本执行完成"

## 脚本输出

脚本自动保存结果到 `disposition_result.json`，包含：
- `alert` (dict): 预警信息
  - `level` (str): 预警级别（general/moderate/serious）
  - `level_cn` (str): 预警级别中文（一般/较重/严重）
  - `confidence` (float): 融合置信度
  - `action` (str): 处置行动
  - `action_cn` (str): 处置行动中文
- `violation_type` (str): 违规类型
- `work_order` (dict): 工单信息
  - `id` (str): 工单编号
  - `alert_level` (str): 预警级别
  - `inspection_points` (list): 现场核查要点
  - `legal_references` (list): 法规条款引用
  - `recommended_actions` (list): 处置建议
- `report` (dict): 预警报告
- `fusion` (dict): 融合信息

**你不需要处理输出，系统会自动读取。**

## 输入要求

此技能需要以下输入（按优先级）：
1. **违规判定结果** - 推荐使用，来自 rule-reasoning 子智能体
2. **异常检测结果** - 可选，来自 anomaly-detection 子智能体

脚本会自动查找以下位置的输入文件：
- `SESSION_DIR/rule_reasoning_result.json`
- `subagents/rule-reasoning-agent/rule_reasoning_result.json`
- `SESSION_DIR/anomaly_result.json`
- `subagents/anomaly-detection-agent/anomaly_result.json`

## 处理流程

```
违规判定结果 + 异常检测结果 → 融合共识算法 → 预警分级 → 工单生成 → 预警报告
```

### 融合共识算法
- 提取异常检测置信度
- 提取违规判定置信度
- 动态调整权重
- 计算融合置信度

### 预警分级
- **一般（黄色/general）**: 置信度 ≤ 0.6，持续监控
- **较重（橙色/moderate）**: 置信度 0.6-0.8，现场核查
- **严重（红色/serious）**: 置信度 > 0.8，立即调查取证

### 工单生成
- 唯一工单编号（WO-YYYYMMDD-XXX-XXXXXX）
- 数据溯源（时间范围、受影响指标）
- 现场核查要点（根据违规类型定制）
- 法规条款引用
- 处置建议

### 预警报告
- 报告编号（ALERT-工单ID-时间戳）
- 完整预警信息
- 支持导出 JSON 和 Markdown 格式

## 预警级别

| 级别 | 英文 | 中文 | 置信度范围 | 处置行动 |
|------|------|------|-----------|---------|
| 一般 | general | 一般（黄色） | ≤ 0.6 | 持续监控 |
| 较重 | moderate | 较重（橙色） | 0.6 - 0.8 | 现场核查 |
| 严重 | serious | 严重（红色） | > 0.8 | 立即调查取证 |

## 处置行动

| 行动 | 英文 | 中文 |
|------|------|------|
| 持续监控 | monitor | 持续监控 |
| 现场核查 | investigate | 现场核查 |
| 立即调查取证 | immediate_investigation | 立即调查取证 |

## 工单编号格式

```
WO-YYYYMMDD-序号-随机后缀
```

示例：`WO-20260715-001-a3b4c5d6`

## 命令行参数

```bash
# 使用默认路径
python "$HERMES_HOME/skills/disposition-execution-core/scripts/run_disposition.py"

# 指定会话目录
python "$HERMES_HOME/skills/disposition-execution-core/scripts/run_disposition.py" --session-dir <path>
```

## 输出路径

```
SESSION_DIR/disposition_result.json  # 如果设置了 SESSION_DIR
subagents/disposition-execution-agent/disposition_result.json  # 默认路径
```

## 典型使用场景

1. **生成预警工单**: "检测到异常后生成预警工单"
2. **违规处置**: "确认违规后生成处置方案"
3. **预警分级**: "根据严重程度对预警进行分级"
4. **定期报告**: "生成本周预警汇总报告"

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要做违规判定（由rule-reasoning负责）
- ❌ 不要做异常检测（由anomaly-detection负责）

---

# 真正 Hermes SKILL.md 和 SOUL.md 设计文档

## 目标

将当前的固定编排架构改造为真正的 LLM 驱动的 Hermes 架构，让 LLM 自主决定调用哪些子智能体。

---

## 当前问题

### 固定编排架构

当前的 `query_interface.py` 使用固定编排：

```
用户查询 → llm_parse_query_intent() (固定步骤1)
          → fetch_data_for_query() (固定步骤2)
          → coordinate_agent_execution() (固定步骤3)
          → llm_generate_summary() (固定步骤4)
```

**问题：**
- LLM 没有决策空间
- `coordinate_agent_execution()` 中的 `agent_id` 参数被忽略
- 不是真正的 Hermes

### 真正 Hermes 的目标

```
用户查询 → AIAgent.run_conversation()
          ↓
       LLM 自主决策:
       ├─ 需要数据？→ delegate_task(data-perception)
       ├─ 需要异常检测？→ delegate_task(anomaly-detection)
       ├─ 需要违规判定？→ delegate_task(rule-reasoning)
       └─ 需要预警？→ delegate_task(disposition-execution)
          ↓
       自然语言响应
```

---

## 核心设计决策

| 维度 | 选择 | 原因 |
|------|------|------|
| SKILL.md 格式 | 纯 LLM 格式，详细文档放 references/ | 遵循 skill-creator 原则 |
| 数据获取 | 集成到 data-perception 内部 | 符合子智能体专业分工 |
| 调用指导 | 在 SOUL.md 中描述决策树 | 主智能体需要调用指导 |
| 错误处理 | 在各 SKILL.md 中分别描述 | 不同子智能体失败策略不同 |
| 迁移策略 | 渐进式，保留 Flask 入口 | 降低风险，便于验证 |

---

## 修改的文件

### 主智能体文件（2个）

1. **workspace/SOUL.md** - 增加子智能体调用决策树
2. **workspace/AGENTS.md** - 清理旧的固定编排描述

### 子智能体 SKILL.md 文件（4个）

3. **subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md**
4. **subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md**
5. **subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md**
6. **subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md**

---

## 1. data-perception-core / SKILL.md

### LLM 调用指南

**职责：** 获取并预处理多维时序数据，自动完成数据获取、时间对齐、数据清洗、字段标准化。

**触发条件：** 用户提到"进水"、"出水"、"监测数据"、"数据"、"指标"或时间范围（"最近N小时"、"今天"、"昨天"）。

**调用参数：**
```json
{
  "task_id": "唯一任务ID（可选）",
  "query": "原始用户查询",
  "requirements": {
    "data_source": "influent|effluent|both",
    "indicators": ["pH", "COD", ...],
    "time_range": {
      "hours_back": 数字,
      "start": "ISO时间戳",
      "end": "ISO时间戳"
    }
  }
}
```

**输出格式：**
```json
{
  "status": "success|error",
  "processed_data": {
    "influent": [{"timestamp": "...", "pH": 7.2, "COD": 45.3, ...}, ...],
    "effluent": [...]
  },
  "quality_report": {
    "completeness": 0.95,
    "anomaly_rate": 0.02,
    "missing_count": 10
  }
}
```

**内部处理流程：**
1. 调用 historical_data_fetcher 获取 CSV 数据
2. 时间对齐（进水-出水2小时滞后）
3. 数据清洗（缺失值/异常值处理）
4. 字段标准化（中文字段名→英文）

**错误处理：**
- 数据文件不存在 → 向用户说明，询问其他时间范围
- 时间范围无数据 → 返回最近数据，说明实际时间范围
- 数据质量差（异常率>50%） → 提示传感器可能有问题

**后续调用：** 输出传递给 anomaly-detection、correlation-analysis、trend-analysis

**详细文档：**
- [数据获取 API](references/data-acquisition.md)
- [配置参数](references/configuration.md)
- [质量阈值](references/quality-thresholds.md)

---

## 2. anomaly-detection-core / SKILL.md

### LLM 调用指南

**职责：** 时序数据异常点检测。检测异常时间段、异常分数、异常点位置，不判定违规性质。

**触发条件：** 用户提到"异常"、"不正常"、"突变"、"趋势"、"是否正常"、"检测异常"。

**前置条件：** 必须有来自 data-perception 的预处理数据。如果用户查询包含数据需求但尚未调用 data-perception，先调用 data-perception。

**调用参数：**
```json
{
  "task_id": "唯一任务ID（可选）",
  "query": "原始用户查询",
  "data": {
    "influent": [{"timestamp": "...", "pH": 7.2, "COD": 45.3, ...}, ...],
    "effluent": [...]
  },
  "requirements": {
    "indicators": ["需要检测的指标"],
    "detection_types": ["anomaly"],
    "operators": ["zscore", "iqr", "isolation_forest"]
  }
}
```

**输出格式：**
```json
{
  "status": "success|error",
  "anomalies": [
    {
      "indicator": "COD",
      "timestamp": "2026-06-22 10:00:00",
      "type": "spike",
      "score": 0.85,
      "value": 85.3,
      "expected_range": [30, 50]
    }
  ],
  "summary": {
    "total_anomalies": 3,
    "by_indicator": {"COD": 2, "pH": 1},
    "by_type": {"spike": 2, "trend": 1}
  }
}
```

**异常类型：**
- constant - 数值长时间不变
- spike - 相邻点剧烈变化
- trend - 均匀上升/下降
- periodic - 非自然周期变化
- high-frequency - 高频波动

**算子选择策略：**
| 数据量 | 自相关性 | 推荐算子 |
|--------|---------|----------|
| n < 1000 | 弱 | IQR、3σ |
| 1000 ≤ n < 10000 | 强 | Isolation Forest |
| n ≥ 10000 | 强 | LSTM Autoencoder |

**错误处理：**
- 数据为空 → 提示需要先获取数据
- 数据量不足（<10条） → 提示数据太少，建议扩大时间范围
- 指标字段缺失 → 跳过该指标，说明可用指标

**后续调用：** 输出传递给 rule-reasoning 进行违规判定

**详细文档：**
- [算子库参考](references/operators.md)
- [算子选择算法](references/operator-selection.md)

---

## 3. rule-reasoning-core / SKILL.md

### LLM 调用指南

**职责：** 违规判定和规则推理，结合知识库验证。基于异常点判定违规模式，检索工艺知识库验证是否为正常工艺，检索专家经验库匹配历史案例，综合生成违规结论。

**触发条件：** 用户提到"违规"、"超标"、"违反标准"、"是否达标"、"瓶装"、"稀释"、"排放异常"。

**前置条件：** 建议先有来自 anomaly-detection 的异常点列表。

**处理流程：**
1. 规则引擎 - 基于异常特征初步判定违规模式
2. 知识检索 - 检索工艺知识库验证异常是否对应正常工艺
3. 专家推理 - 解决知识冲突，评估可疑度
4. 违规结论 - 综合规则和知识的最终判定

**调用参数：**
```json
{
  "task_id": "唯一任务ID",
  "query": "原始用户查询",
  "data": {
    "influent": [...],
    "effluent": [...]
  },
  "anomalies": [
    {
      "indicator": "COD",
      "timestamp": "2026-06-22 10:00:00",
      "type": "constant",
      "score": 0.85,
      "value": 45.2
    }
  ],
  "requirements": {
    "regulation_standard": "GB_18918_2002_1A",
    "enable_knowledge_validation": true
  }
}
```

**输出格式：**
```json
{
  "status": "success|error",
  "rule_engine_result": {
    "detected_patterns": ["bottle_interference"],
    "confidence": 0.85
  },
  "knowledge_validation": {
    "process_knowledge": {
      "found": true,
      "explanation": "工艺调整期间pH稳定是正常现象",
      "reduces_suspicion": true
    },
    "expert_cases": [...]
  },
  "conclusion": {
    "suspicion_level": "low",
    "reasoning": "规则判定为插瓶干扰，但工艺知识库表明该时段有工艺调整，降低可疑度",
    "evidence_points": [...],
    "legal_references": [...]
  }
}
```

**可疑度等级：**
| 条件 | 等级 |
|------|------|
| 规则判定违规 AND 工艺知识库无解释 AND 专家案例匹配≥0.8 | 高 |
| 规则判定违规 AND 工艺知识库有解释 OR 专家案例匹配<0.8 | 中 |
| 规则判定违规但工艺知识库完全解释 | 低 |

**知识库文件：**
- [法规库](../shared/knowledge/regulations/)
- [工艺知识库](../shared/knowledge/process_knowledge/)
- [违规模式库](../shared/knowledge/violation_patterns/)
- [专家经验库](../shared/knowledge/expert_experience/)

---

## 4. disposition-execution-core / SKILL.md

### LLM 调用指南

**职责：** 预警分级和处置执行。根据违规结论进行三级预警分级，融合多源检测结果，生成标准化工单，多渠道执行。

**触发条件：** 用户提到"预警"、"工单"、"通知"、"处置"、"生成预警"、"创建工单"。

**前置条件：** 建议先有来自 rule-reasoning 的违规结论。

**调用参数：**
```json
{
  "task_id": "唯一任务ID",
  "query": "原始用户查询",
  "anomaly_result": {
    "anomalies": [...],
    "summary": "检测到3个异常点"
  },
  "violation_result": {
    "conclusion": {
      "suspicion_level": "high",
      "evidence_points": [...],
      "legal_references": [...]
    }
  },
  "requirements": {
    "alert_scene": "default|critical|normal",
    "execution_channels": ["FeishuPush", "LocalArchive"]
  }
}
```

**输出格式：**
```json
{
  "status": "success|error",
  "alert": {
    "level": "serious|moderate|general",
    "reasoning": "高可疑度 + 多个违规模式"
  },
  "fused_result": {
    "conclusion": "综合判定：严重预警",
    "confidence": 0.88
  },
  "work_order": {
    "order_id": "WO_20260622_001",
    "alert_level": "serious",
    "violation_type": "dilution_discharge",
    "evidence": {...},
    "inspection_points": [...],
    "legal_references": [...]
  },
  "execution_status": {
    "FeishuPush": "success",
    "LocalArchive": "success"
  }
}
```

**预警分级规则：**
| 输入条件 | 预警级别 |
|---------|---------|
| 高可疑度 + 多个违规模式 | 严重 |
| 中可疑度 + 单个违规模式 | 中度 |
| 低可疑度 + 无违规模式 | 一般 |

**融合策略：**
| 场景 | 异常权重 | 违规权重 |
|------|---------|---------|
| default（默认） | 0.6 | 0.4 |
| critical（关键） | 0.4 | 0.6 |
| normal（正常） | 0.7 | 0.3 |

**执行渠道选择：**
| 预警级别 | 执行渠道 |
|---------|---------|
| 严重 | 全部渠道 |
| 中度 | 飞书 + 本地归档 |
| 一般 | 本地归档 |

**详细文档：**
- [融合配置](../shared/configs/consensus_config.yaml)
- [工单模板](references/work-order-template.md)

---

## workspace/SOUL.md 增强

### 子智能体调用决策树

```
用户查询
    ↓
[1] 需要数据吗？
    ├─ 提到"数据"、"指标"、"监测"、"进水"、"出水"
    ├─ 提到"最近N小时"、"今天"、"昨天"
    └─ YES → 调用 data-perception
    │         （会自动获取历史数据、预处理）
    └─ NO → 跳过数据分析步骤
    ↓
[2] 需要异常检测吗？
    ├─ 提到"异常"、"不正常"、"突变"、"是否正常"
    └─ YES → 调用 anomaly-detection
    │         （需要 data-perception 的输出）
    └─ NO → 跳过异常检测
    ↓
[3] 需要违规判定吗？
    ├─ 提到"违规"、"超标"、"违反标准"、"是否达标"
    ├─ 提到"瓶装"、"稀释"、"排放异常"
    └─ YES → 调用 rule-reasoning
    │         （需要 anomaly-detection 的输出）
    └─ NO → 跳过违规判定
    ↓
[4] 需要预警/工单吗？
    ├─ 提到"预警"、"工单"、"通知"、"处置"
    └─ YES → 调用 disposition-execution
    │         （需要 rule-reasoning 的输出）
    └─ NO → 跳过处置执行
    ↓
[5] 整合结果，生成自然语言回答
```

### 示例分析

**示例1："最近24小时出水COD异常吗？"**
- ✅ 需要数据 → data-perception
- ✅ 需要异常检测 → anomaly-detection
- ❌ 不需要违规判定 → 跳过 rule-reasoning
- ❌ 不需要预警 → 跳过 disposition-execution

**示例2："最近24小时出水是否超标？"**
- ✅ 需要数据 → data-perception
- ✅ 需要异常检测 → anomaly-detection
- ✅ 需要违规判定 → rule-reasoning
- ❌ 不需要预警 → 跳过 disposition-execution

**示例3："生成今天的异常预警工单"**
- ✅ 需要数据 → data-perception
- ✅ 需要异常检测 → anomaly-detection
- ✅ 需要违规判定 → rule-reasoning
- ✅ 需要预警 → disposition-execution

### 子智能体协作关系

```
data-perception (第一步)
    ↓ processed_data
anomaly-detection (第二步)
    ↓ anomalies
rule-reasoning (第三步)
    ↓ conclusion
disposition-execution (第四步，可选)
    ↓ work_order
```

**重要：** 子智能体可以并行调用（当互不依赖时），也可以串行调用（当存在依赖时）。

---

## workspace/AGENTS.md 清理

### 需要移除的内容

以下内容与真正的 Hermes 冲突，需要移除：

1. **"双驱动运行机制"章节** - 描述固定编排流程
2. **"任务编排层"相关描述** - task_structuring.py、task_flow_generation.py 等
3. **"结果复用判断"** - 固定流程的缓存机制
4. **"核心技能包"中的 orchestrator-core** - 自定义编排技能

### 保留的内容

以下内容应该保留：

1. **工作原则** - 全局优先、数据驱动、及时响应
2. **职责边界** - 主智能体应该/不应该做什么
3. **子智能体列表** - 4个子智能体的名称和职责
4. **Red Lines** - 安全边界

---

## 架构变化总结

### 当前（固定编排）

```
用户查询 → query_interface.py
              ↓
         [固定步骤1] 解析意图 (llm_parse_query_intent)
         [固定步骤2] 获取数据 (fetch_data_for_query)
         [固定步骤3] 调用子智能体 (coordinate_agent_execution)
         [固定步骤4] 生成总结 (llm_generate_summary)
```

### 目标（真正 Hermes）

```
用户查询 → query_interface.py (简化)
              ↓
         AIAgent.run_conversation()
              ↓
         LLM 自主决策:
         ├─ 需要数据？→ delegate_task(data-perception)
         ├─ 需要异常检测？→ delegate_task(anomaly-detection)
         ├─ 需要违规判定？→ delegate_task(rule-reasoning)
         └─ 需要预警？→ delegate_task(disposition-execution)
              ↓
         自然语言响应
```

---

## 数据流程

### data-perception 内部处理

```
LLM 调用 data-perception
    ↓
historical_data_fetcher 获取 CSV 数据
    ↓
时间对齐（2小时滞后）
    ↓
数据清洗（缺失值/异常值处理）
    ↓
字段标准化（中文字段名→英文）
    ↓
返回 processed_data
```

### rule-reasoning 知识验证流程

```
规则引擎判定违规模式
    ↓
检索工艺知识库（是否为正常工艺）
    ↓
检索专家经验库（匹配历史案例）
    ↓
综合推理（解决知识冲突）
    ↓
生成违规结论
```

---

## 知识库结构

```
shared/knowledge/
├── regulations/         # 法规库
│   ├── 排放标准.md
│   └── 水污染防治法.md
├── process_knowledge/   # 工艺知识库
│   └── 生化处理工艺.md
├── violation_patterns/  # 违规模式库
│   ├── violation_patterns.md
│   └── violation_patterns.py
└── expert_experience/   # 专家经验库
    ├── suspicion_rules.py
    └── 典型违规模式.md
```

---

## 实现说明

### 使用 skill-creator 技能

所有 SKILL.md 的创建/更新应使用 skill-creator 技能，确保格式符合 Hermes 标准。

### SKILL.md 格式要求

- **Frontmatter** - 包含 name 和 description 字段
- **description** - 必须包含所有触发条件信息（LLM 读取决定何时使用）
- **Body** - 只保留 LLM 需要的核心信息（参数、输出、错误处理）
- **详细文档** - 放到 references/ 目录，通过链接引用

### 不需要修改的文件

- 子智能体的 SOUL.md、AGENTS.md、MEMORY.md 等（专业领域知识，不受架构变化影响）
- workspace/IDENTITY.md、USER.md、TOOLS.md（与架构无关）

---

## 验证标准

设计实现后，应满足以下标准：

1. **LLM 自主决策** - LLM 通过 `delegate_task` 自主决定调用哪些子智能体
2. **无固定编排** - 没有固定的"步骤1→步骤2→步骤3"流程
3. **职责清晰** - 每个子智能体职责明确，边界清晰
4. **知识验证** - rule-reasoning 能够检索知识库验证违规判定
5. **SKILL.md 简洁** - SKILL.md 保持简洁，详细文档在 references/

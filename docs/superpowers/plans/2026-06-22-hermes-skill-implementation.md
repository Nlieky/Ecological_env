# 真正 Hermes SKILL.md 和 SOUL.md 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前固定编排架构改造为真正的 LLM 驱动的 Hermes 架构，让 LLM 自主决定调用哪些子智能体。

**Architecture:** 通过重写 SKILL.md 和 SOUL.md，移除固定编排逻辑，让 LLM 通过 delegate_task 工具自主决策调用子智能体。data-perception 内部集成数据获取，rule-reasoning 结合知识库验证违规判定。

**Tech Stack:** Hermes Agent Framework, skill-creator, Markdown, YAML frontmatter

---

## File Structure

### 修改的文件（6个）

**主智能体文件：**
1. `workspace/SOUL.md` - 增加子智能体调用决策树
2. `workspace/AGENTS.md` - 清理旧的固定编排描述

**子智能体 SKILL.md 文件：**
3. `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`
4. `subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md`
5. `subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md`
6. `subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`

### 创建的 references 文件（可选）

如果需要新的详细文档文件，在相应的 references/ 目录中创建。

---

## Task 1: 修改 workspace/SOUL.md

**Files:**
- Modify: `workspace/SOUL.md`

- [ ] **Step 1: 读取当前的 SOUL.md 文件**

Run: `cat workspace/SOUL.md`
Expected: 查看当前内容，确认文件结构

- [ ] **Step 2: 在 "## Subagent Calling" 章节后插入决策树**

在 "Subagent Calling" 章节的 "可用子智能体" 表格之后，插入以下内容：

```markdown
### 子智能体调用决策树

当用户查询包含以下需求时，按决策树调用子智能体：

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
```

- [ ] **Step 3: 验证修改后的格式**

Run: `cat workspace/SOUL.md | grep -A 5 "决策树"`
Expected: 看到新插入的决策树内容

- [ ] **Step 4: 提交修改**

```bash
git add workspace/SOUL.md
git commit -m "feat: add subagent calling decision tree to SOUL.md

- Add decision tree for LLM to decide which subagents to call
- Add example analysis for common query patterns
- Add collaboration relationship between subagents

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 清理 workspace/AGENTS.md

**Files:**
- Modify: `workspace/AGENTS.md`

- [ ] **Step 1: 读取当前的 AGENTS.md 文件**

Run: `cat workspace/AGENTS.md`
Expected: 查看当前内容，特别关注"双驱动运行机制"和"核心技能包"章节

- [ ] **Step 2: 删除"双驱动运行机制"章节**

删除以下内容：
- 从 `### 双驱动运行机制` 开始
- 到 `## Tools` 之前结束
- 包括"实时监测模式"和"查询响应模式"两个子节

- [ ] **Step 3: 删除"核心技能包"中的 orchestrator-core**

删除以下内容：
```markdown
- **orchestrator-core** (`workspace/skills/orchestrator-core/`) - 任务编排层
  - task_structuring.py - 任务结构化
  - task_flow_generation.py - 任务流生成
  - resource_matching.py - 资源匹配
  - execution_control.py - 执行控制
```

- [ ] **Step 4: 删除"子智能体调度规则"章节**

删除从 `## 子智能体调度规则` 开始到文件末尾或下一个主章节之前的所有内容。

- [ ] **Step 5: 添加简化的子智能体描述**

在 "### 子智能体" 章节中，保留以下简化描述：

```markdown
### 子智能体

- 📊 multi-dimensional-data-perception-agent - 多维数据感知（数据获取、清洗、标准化）
- 🔍 anomaly-detection-agent - 异常检测（异常识别、特征提取）
- ⚖️ rule-reasoning-agent - 规则推理（违规判定、知识验证）
- 🚨 disposition-execution-agent - 研判预警与处置执行（预警分级、工单生成）

子智能体由主智能体通过 `delegate_task` 工具调用，LLM 根据用户查询自主决定调用哪些子智能体。
```

- [ ] **Step 6: 验证修改后的内容**

Run: `grep -E "(双驱动|任务编排|orchestrator-core|task_structuring)" workspace/AGENTS.md`
Expected: 没有匹配结果（确认旧内容已删除）

- [ ] **Step 7: 提交修改**

```bash
git add workspace/AGENTS.md
git commit -m "refactor: remove fixed orchestration from AGENTS.md

- Remove dual-drive operation mechanism (fixed orchestration)
- Remove orchestrator-core skill references
- Remove subagent scheduling rules (fixed patterns)
- Keep simplified subagent descriptions for reference

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 重写 data-perception-core/SKILL.md

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`

- [ ] **Step 1: 读取当前的 SKILL.md 文件**

Run: `cat subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`
Expected: 查看当前格式和内容

- [ ] **Step 2: 备份当前文件**

Run: `cp subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md.backup`
Expected: 创建备份文件

- [ ] **Step 3: 重写 SKILL.md 为 LLM 格式**

用以下内容完全替换 SKILL.md：

```markdown
---
name: data-perception-core
description: 获取并预处理多维时序数据。**触发条件**：当用户查询提到"进水"、"出水"、"监测数据"、"数据"、"指标"或时间范围（"最近N小时"、"今天"、"昨天"）时调用。自动完成数据获取（CSV）、时间对齐（进水-出水2小时滞后）、数据清洗、字段标准化（中文字段名→英文）。支持指标：pH、COD、TN、NH3-N、TP、SS、流量。这是数据分析的第一步，输出预处理数据给 anomaly-detection、correlation-analysis、trend-analysis 等后续技能使用。
---

# 多维数据感知

## 调用参数

传递给此技能的参数格式：

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

**参数推断规则**:
- `data_source`: "出水"→"effluent"，"进水"→"influent"，未指定→"both"
- `indicators`: 从查询中提取，未指定则使用默认["pH", "COD"]
- `time_range`: "最近24小时"→{"hours_back": 24}

## 输出格式

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
    "missing_count": 10,
    "time_range_actual": {"start": "...", "end": "..."}
  }
}
```

## 内部处理流程

此技能**自动完成**以下步骤（无需 LLM 预处理）：
1. **数据获取** - 调用 historical_data_fetcher 从 CSV 获取数据
2. **时间对齐** - 补偿进水-出水2小时处理滞后
3. **数据清洗** - 处理缺失值、异常值（超出物理范围的值）
4. **字段标准化** - 中文字段名转英文（"pH值"→"pH"）

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 数据文件不存在 | 向用户说明数据不可用，询问其他时间范围 |
| 时间范围无数据 | 返回最近数据，说明实际时间范围 |
| 字段缺失 | 跳过该指标，说明可用指标 |
| 数据质量差（异常率>50%） | 提示传感器可能有问题，建议检查传感器 |

## 后续调用

此技能的输出（`processed_data`）应传递给：
- **anomaly-detection** - 异常检测
- **correlation-analysis** - 相关性分析
- **trend-analysis** - 趋势分析

## 详细文档

- [数据获取 API](references/data-acquisition.md)
- [配置参数](references/configuration.md)
- [质量阈值](references/quality-thresholds.md)
```

- [ ] **Step 4: 验证新格式**

Run: `head -20 subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`
Expected: 看到新的 frontmatter 和 LLM 指南格式

- [ ] **Step 5: 提交修改**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md
git commit -m "refactor: rewrite data-perception-core SKILL.md for LLM

- Remove Python code examples (not for LLM)
- Add LLM calling guide (parameters, output, error handling)
- Add parameter inference rules
- Move detailed docs to references/ links
- Focus on LLM decision-making

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: 重写 anomaly-detection-core/SKILL.md

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md`

- [ ] **Step 1: 读取当前的 SKILL.md 文件**

Run: `cat subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md`
Expected: 查看当前格式和内容

- [ ] **Step 2: 备份当前文件**

Run: `cp subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md.backup`
Expected: 创建备份文件

- [ ] **Step 3: 重写 SKILL.md 为 LLM 格式**

用以下内容完全替换 SKILL.md：

```markdown
---
name: anomaly-detection-core
description: 时序数据异常点检测。**触发条件**：当用户查询提到"异常"、"不正常"、"突变"、"趋势"、"是否正常"、"检测异常"时调用。检测异常时间段、异常分数、异常点位置，不判定违规性质。使用统计算子（3σ、IQR、Grubbs）、ML算子（孤立森林、One-Class SVM）、深度学习（LSTM自编码器）。需要预处理后的数据（来自 data-perception）作为输入。输出异常点列表传递给 rule-reasoning 进行违规判定。
---

# 异常检测

## 职责范围

**此技能只负责检测异常点，不判定违规性质。**
- ✅ 检测异常时间段、异常分数、异常点位置
- ✅ 识别异常类型（constant、spike、trend、periodic、high-frequency）
- ❌ 不判定违规模式（违规判定由 rule-reasoning 负责）

## 前置条件

**必须有数据**：此技能需要来自 data-perception 的预处理数据。
如果用户查询包含数据需求但尚未调用 data-perception，**先调用 data-perception**。

## 调用参数

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

**参数推断规则**:
- `indicators`: 从用户查询提取，未指定则检测所有可用指标
- `operators`: 根据数据量自动选择（n<1000→IQR/3σ，1000≤n<10000→isolation_forest）

## 输出格式

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

## 异常类型定义

| 类型 | 描述 | 检测依据 |
|------|------|----------|
| constant | 数值长时间不变 | 方差接近0 |
| spike | 相邻点剧烈变化 | 差分超过阈值 |
| trend | 均匀上升/下降 | 二阶导数接近0 |
| periodic | 非自然周期变化 | FFT 功率谱 |
| high-frequency | 高频波动 | 符号变化率高 |

## 算子选择策略

| 数据量 | 自相关性 | 推荐算子 |
|--------|---------|----------|
| n < 1000 | 弱 | IQR、3σ |
| 1000 ≤ n < 10000 | 强 | Isolation Forest |
| n ≥ 10000 | 强 | LSTM Autoencoder |

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 数据为空 | 提示需要先获取数据，调用 data-perception |
| 数据量不足（<10条） | 提示数据太少，建议扩大时间范围 |
| 指标字段缺失 | 跳过该指标，说明可用指标 |

## 后续调用

此技能的输出（异常点列表）应传递给：
- **rule-reasoning** - 进行违规判定（当用户提到"违规"、"超标"、"瓶装"、"稀释"时）

## 详细文档

- [算子库参考](references/operators.md)
- [算子选择算法](references/operator-selection.md)
```

- [ ] **Step 4: 验证新格式**

Run: `head -20 subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md`
Expected: 看到新的 frontmatter 和 LLM 指南格式

- [ ] **Step 5: 提交修改**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md
git commit -m "refactor: rewrite anomaly-detection-core SKILL.md for LLM

- Clarify responsibility: anomaly detection only, not violation judgment
- Remove violation pattern detection (moved to rule-reasoning)
- Add LLM calling guide with prerequisite conditions
- Add operator selection strategy table
- Move detailed docs to references/ links

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 重写 rule-reasoning-core/SKILL.md

**Files:**
- Modify: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md`

- [ ] **Step 1: 读取当前的 SKILL.md 文件**

Run: `cat subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md`
Expected: 查看当前格式和内容

- [ ] **Step 2: 备份当前文件**

Run: `cp subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md.backup`
Expected: 创建备份文件

- [ ] **Step 3: 重写 SKILL.md 为 LLM 格式**

用以下内容完全替换 SKILL.md：

```markdown
---
name: rule-reasoning-core
description: 违规判定和规则推理，结合知识库验证。**触发条件**：当用户查询提到"违规"、"超标"、"违反标准"、"是否达标"、"瓶装"、"稀释"、"排放异常"时调用。流程：(1)规则引擎基于异常点初步判定违规模式→(2)检索工艺知识库验证是否为正常工艺→(3)检索专家经验库匹配历史案例→(4)综合生成违规结论（可疑度、证据点、法律依据）。需要异常点列表（来自 anomaly-detection）作为输入。
---

# 规则推理和违规判定

## 职责范围

- ✅ 基于异常点判定违规模式（规则引擎）
- ✅ 检索工艺知识库验证异常是否对应正常工艺
- ✅ 检索专家经验库匹配历史案例（相似度阈值0.8）
- ✅ 生成违规结论（可疑度、证据点、法律依据）

## 处理流程

```
1. 规则引擎
   └─ 基于异常特征初步判定违规模式
   
2. 知识检索
   ├─ 工艺知识库：验证"异常"是否对应正常工艺
   ├─ 专家经验库：匹配相似历史案例
   └─ 法规库：获取相关法律条文
   
3. 专家推理
   ├─ 解决知识冲突（规则判定 vs 工艺解释）
   ├─ 评估可疑度
   └─ 生成最终结论
```

## 知识验证示例

| 规则引擎判定 | 工艺知识库解释 | 最终结论 |
|-------------|---------------|---------|
| pH恒定→插瓶干扰 | 工艺调整期间pH稳定是正常 | 非违规 |
| pH恒定→插瓶干扰 | 无工艺调整记录 | 可疑 |
| 多指标同步下降→稀释排放 | 冲击负荷后浓度下降是正常 | 非违规 |

## 调用参数

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

## 输出格式

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
    "expert_cases": [
      {
        "case_id": "case_001",
        "similarity": 0.82,
        "conclusion": "插瓶干扰"
      }
    ]
  },
  "conclusion": {
    "suspicion_level": "low",
    "reasoning": "规则判定为插瓶干扰，但工艺知识库表明该时段有工艺调整，降低可疑度",
    "evidence_points": ["超标3次", "NH3-N/TN转化异常", "稀释排放模式"],
    "legal_references": ["GB 18918-2002 一级A标准: COD≤50mg/L"]
  }
}
```

## 可疑度等级

| 条件 | 等级 |
|------|------|
| 规则判定违规 AND 工艺知识库无解释 AND 专家案例匹配≥0.8 | 高 |
| 规则判定违规 AND 工艺知识库有解释 OR 专家案例匹配<0.8 | 中 |
| 规则判定违规但工艺知识库完全解释 | 低 |

## 知识库文件

- [法规库](../../shared/knowledge/regulations/)
- [工艺知识库](../../shared/knowledge/process_knowledge/)
- [违规模式库](../../shared/knowledge/violation_patterns/)
- [专家经验库](../../shared/knowledge/expert_experience/)
```

- [ ] **Step 4: 验证新格式**

Run: `head -20 subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md`
Expected: 看到新的 frontmatter 和 LLM 指南格式

- [ ] **Step 5: 提交修改**

```bash
git add subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md
git commit -m "refactor: rewrite rule-reasoning-core SKILL.md for LLM

- Add knowledge validation workflow (rule engine → knowledge retrieval → reasoning)
- Add knowledge validation examples table
- Add suspicion level criteria (high/medium/low)
- Link to knowledge base files (regulations, process, patterns, expert)
- Clarify that violation judgment combines rules + knowledge

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: 重写 disposition-execution-core/SKILL.md

**Files:**
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`

- [ ] **Step 1: 读取当前的 SKILL.md 文件**

Run: `cat subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`
Expected: 查看当前格式和内容

- [ ] **Step 2: 备份当前文件**

Run: `cp subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md.backup`
Expected: 创建备份文件

- [ ] **Step 3: 重写 SKILL.md 为 LLM 格式**

用以下内容完全替换 SKILL.md：

```markdown
---
name: disposition-execution-core
description: 预警分级和处置执行。**触发条件**：当用户查询提到"预警"、"工单"、"通知"、"处置"、"生成预警"、"创建工单"时调用。根据违规结论（来自 rule-reasoning）进行三级预警分级（一般、中度、严重），融合多源检测结果（动态权重适应），生成标准化工单（含证据、法律引用、检查要点），多渠道执行（监管平台推送、飞书通知、本地归档）。支持场景：default（平衡权重）、critical（违规权重高）、normal（异常权重高）。
---

# 预警分级和处置执行

## 职责范围

- ✅ 预警分级（一般/中度/严重）
- ✅ 多源结果融合（异常检测 + 规则推理）
- ✅ 标准化工单生成（证据、法律引用、检查要点）
- ✅ 多渠道执行（监管平台、飞书、本地归档）

## 前置条件

**建议先有违规结论**：此技能最好使用来自 rule-reasoning 的违规结论。
如果用户要求"预警"但尚未进行违规判定，**先调用 anomaly-detection 和 rule-reasoning**。

## 调用参数

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

**参数推断规则**:
- `alert_scene`: 可疑度"高"→"critical"，未指定→"default"
- `execution_channels`: 未指定则根据预警级别自动选择

## 输出格式

```json
{
  "status": "success|error",
  "alert": {
    "level": "serious|moderate|general",
    "reasoning": "高可疑度 + 多个违规模式"
  },
  "fused_result": {
    "conclusion": "综合判定：严重预警",
    "confidence": 0.88,
    "weights_used": {
      "anomaly_sources": 0.6,
      "violation_sources": 0.4
    }
  },
  "work_order": {
    "order_id": "WO_20260622_001",
    "alert_level": "serious",
    "violation_type": "dilution_discharge",
    "evidence": {...},
    "inspection_points": [...],
    "legal_references": [...],
    "timestamp": "2026-06-22 10:00:00"
  },
  "execution_status": {
    "FeishuPush": "success",
    "LocalArchive": "success"
  }
}
```

## 预警分级规则

| 输入条件 | 预警级别 |
|---------|---------|
| 高可疑度 + 多个违规模式 | 严重 |
| 中可疑度 + 单个违规模式 | 中度 |
| 低可疑度 + 无违规模式 | 一般 |

## 融合策略

| 场景 | 异常权重 | 违规权重 |
|------|---------|---------|
| default（默认） | 0.6 | 0.4 |
| critical（关键） | 0.4 | 0.6 |
| normal（正常） | 0.7 | 0.3 |

## 执行渠道选择

| 预警级别 | 执行渠道 |
|---------|---------|
| 严重 | 全部渠道 |
| 中度 | 飞书 + 本地归档 |
| 一般 | 本地归档 |

## 错误处理

| 错误情况 | LLM 处理方式 |
|---------|-------------|
| 缺少违规结论 | 提示需要先进行违规判定 |
| 融合失败 | 使用默认权重，记录警告 |
| 执行失败 | 记录失败渠道，继续其他渠道 |

## 详细文档

- [融合配置](../../shared/configs/consensus_config.yaml)
- [工单模板](references/work-order-template.md)
```

- [ ] **Step 4: 验证新格式**

Run: `head -20 subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`
Expected: 看到新的 frontmatter 和 LLM 指南格式

- [ ] **Step 5: 提交修改**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md
git commit -m "refactor: rewrite disposition-execution-core SKILL.md for LLM

- Add LLM calling guide with prerequisite conditions
- Add alert classification rules table
- Add fusion strategy table (scene-based weights)
- Add execution channel selection table
- Link to consensus config and work order template

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 验证所有修改

**Files:**
- All modified files

- [ ] **Step 1: 验证所有 SKILL.md 文件的格式一致性**

Run: 
```bash
for file in subagents/*/skills/*/SKILL.md; do
  echo "=== $file ==="
  head -5 "$file"
done
```
Expected: 所有文件都有正确的 YAML frontmatter 格式

- [ ] **Step 2: 验证 SOUL.md 和 AGENTS.md 的修改**

Run:
```bash
echo "=== SOUL.md ==="
grep -A 5 "决策树" workspace/SOUL.md
echo "=== AGENTS.md (should not contain orchestrator) ==="
grep -i "orchestrator" workspace/AGENTS.md || echo "No orchestrator found (expected)"
```
Expected: SOUL.md 包含决策树，AGENTS.md 不包含 orchestrator

- [ ] **Step 3: 创建验证摘要文档**

创建 `docs/superpowers/specs/2026-06-22-validation-summary.md`:

```markdown
# 验证摘要

## 修改的文件

1. ✅ workspace/SOUL.md - 增加子智能体调用决策树
2. ✅ workspace/AGENTS.md - 清理旧的固定编排描述
3. ✅ data-perception-core/SKILL.md - 改为 LLM 格式
4. ✅ anomaly-detection-core/SKILL.md - 改为 LLM 格式
5. ✅ rule-reasoning-core/SKILL.md - 改为 LLM 格式
6. ✅ disposition-execution-core/SKILL.md - 改为 LLM 格式

## 验证结果

- 所有 SKILL.md 都有正确的 YAML frontmatter
- 所有 SKILL.md 的 description 字段包含触发条件
- SOUL.md 包含完整的决策树和示例
- AGENTS.md 已清理旧的固定编排内容

## 下一步

- 测试 LLM 是否能正确调用子智能体
- 根据实际使用情况调整 SKILL.md 内容
```

- [ ] **Step 4: 提交验证摘要**

```bash
git add docs/superpowers/specs/2026-06-22-validation-summary.md
git commit -m "docs: add validation summary for Hermes skill design

- Document all modified files
- Verify format consistency
- Confirm orchestration cleanup complete

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: 清理备份文件

**Files:**
- All .backup files

- [ ] **Step 1: 列出所有备份文件**

Run:
```bash
find subagents -name "*.backup" -type f
```
Expected: 列出所有创建的备份文件

- [ ] **Step 2: 确认所有修改已提交后再删除备份**

Run:
```bash
git status
```
Expected: 确认所有修改都已提交，无未提交的更改

- [ ] **Step 3: 删除备份文件**

Run:
```bash
find subagents -name "*.backup" -type f -delete
```
Expected: 备份文件已删除

- [ ] **Step 4: 验证删除**

Run:
```bash
find subagents -name "*.backup" -type f
```
Expected: 没有输出（确认备份文件已删除）

---

## Task 9: 最终验证和文档更新

**Files:**
- README.md, CLAUDE.md

- [ ] **Step 1: 检查 README.md 是否需要更新**

Run: `grep -i "hermes\|orchestrat\|固定编排" README.md`
Expected: 检查是否有需要更新的架构描述

- [ ] **Step 2: 检查 CLAUDE.md 是否需要更新**

Run: `grep -i "hermes\|orchestrat\|固定编排" CLAUDE.md`
Expected: 检查是否有需要更新的架构描述

- [ ] **Step 3: 如果需要更新，添加架构说明**

在 README.md 或 CLAUDE.md 中添加以下说明（如果需要）：

```markdown
## 子智能体调用

主智能体使用 Hermes 框架的 `delegate_task` 工具调用子智能体，LLM 根据用户查询自主决定调用哪些子智能体。

详细的调用决策树请参阅 [workspace/SOUL.md](workspace/SOUL.md)。

## 子智能体列表

- **data-perception** - 多维数据感知
- **anomaly-detection** - 异常检测
- **rule-reasoning** - 规则推理和违规判定
- **disposition-execution** - 预警分级和处置执行
```

- [ ] **Step 4: 创建实施完成标记**

创建 `.hermes/skills-updated` 文件记录完成时间：

```bash
echo "$(date -Iseconds) - SKILL.md files updated to LLM format" > .hermes/skills-updated
```

- [ ] **Step 5: 提交最终更新**

```bash
git add README.md CLAUDE.md .hermes/skills-updated 2>/dev/null || true
git commit -m "docs: update architecture description and mark skills update complete

- Add subagent calling description to README/CLAUDE.md
- Create .hermes/skills-updated marker
- Complete Hermes skill design implementation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 测试指南

实施完成后，进行以下测试验证：

### 测试1: SKILL.md 格式验证

```bash
# 检查所有 SKILL.md 的 frontmatter
for file in subagents/*/skills/*/SKILL.md; do
  echo "=== $file ==="
  head -10 "$file" | grep -E "^name:|^description:"
done
```

**预期结果：** 所有文件都有 name 和 description 字段

### 测试2: 决策树验证

```bash
# 检查 SOUL.md 是否包含决策树
grep -A 30 "子智能体调用决策树" workspace/SOUL.md
```

**预期结果：** 显示完整的决策树和示例

### 测试3: 固定编排清理验证

```bash
# 确认 AGENTS.md 不包含固定编排内容
grep -i "task_structuring\|task_flow\|orchestrator-core" workspace/AGENTS.md
```

**预期结果：** 没有匹配结果

### 测试4: LLM 调用测试

使用 Hermes 框架测试查询：

```python
from run_agent import AIAgent

agent = AIAgent(
    base_url="http://172.16.12.41:30000/v1",
    model="ctgu-vlm",
    load_soul_identity=True
)

# 测试查询
response = agent.run_conversation([{
    "role": "user",
    "content": "最近24小时出水COD异常吗？"
}])
print(response)
```

**预期结果：** LLM 正确调用 data-perception 和 anomaly-detection

---

## 规格覆盖检查

### 设计文档规格 vs 实现计划

| 规格要求 | 实现任务 | 状态 |
|---------|---------|------|
| SOUL.md 增加决策树 | Task 1 | ✅ |
| AGENTS.md 清理固定编排 | Task 2 | ✅ |
| data-perception SKILL.md 重写 | Task 3 | ✅ |
| anomaly-detection SKILL.md 重写 | Task 4 | ✅ |
| rule-reasoning SKILL.md 重写 | Task 5 | ✅ |
| disposition-execution SKILL.md 重写 | Task 6 | ✅ |
| 验证和测试 | Task 7-9 | ✅ |

### 占位符扫描

✅ 无 TBD、TODO、占位符
✅ 所有步骤包含具体代码或命令
✅ 所有文件路径是绝对路径或相对项目根

### 类型一致性检查

✅ 文件名在整个计划中保持一致
✅ 数据结构字段名在各任务中一致
✅ 提交信息格式统一

---

## 总结

本实现计划将当前的固定编排架构改造为真正的 LLM 驱动的 Hermes 架构。关键变化：

1. **SKILL.md 格式** - 从 Python API 文档改为 LLM 调用指南
2. **SOUL.md 增强** - 添加子智能体调用决策树
3. **AGENTS.md 清理** - 移除旧的固定编排描述
4. **职责分离** - 每个子智能体职责明确，边界清晰

实施完成后，LLM 将通过 `delegate_task` 工具自主决定调用哪些子智能体，实现真正的 Hermes 驱动方式。

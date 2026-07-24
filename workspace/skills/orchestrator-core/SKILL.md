---
name: orchestrator-core
description: 主智能体编排技能——协调 4 个子智能体（多维数据感知 / 异常检测 / 规则推理 / 研判预警与处置）完成废水虚假排放研判。**触发条件**：主智能体收到任何涉及"数据 / 监测 / 进水 / 出水 / 指标 / 异常 / 违规 / 超标 / 研判 / 预警 / 工单 / 处置"的查询时，按本技能的决策树决定调用哪些子智能体及顺序，拿到真实结果后再作答。
---

# Orchestrator Core - 主智能体编排技能

## 技能概述

这个技能定义了主智能体如何协调4个专业子智能体来处理废水监测任务。

主智能体通过LLM理解用户意图，智能决定调用哪些子智能体，以什么顺序调用，并整合结果生成自然语言回答。

---

## 可用子智能体

### 1. 多维数据感知子智能体 (multi-dimensional-data-perception-agent) 📊

**位置**: `subagents/multi-dimensional-data-perception-agent/`

**职责**:
- 多源数据获取（CSV、API、数据库）
- 数据质量检查和清洗
- 时序数据对齐处理
- 字段标准化处理
- 特征提取和相关性分析

**使用场景**: 当用户查询涉及数据、指标、监测值时

**典型任务**:
- "获取最近24小时的监测数据"
- "检查数据质量并标记异常值"
- "对齐多个传感器的时间序列数据"

---

### 2. 异常检测子智能体 (anomaly-detection-agent) 🔍

**位置**: `subagents/anomaly-detection-agent/`

**入口脚本**: `run_anomaly_detection_simple.py`

**职责**:
- 5类异常识别：boundary、constant、spike、trend、point
- 多算子融合检测：Z-score、IQR、孤立森林
- 置信度评估和异常评分
- 异常统计摘要

**使用场景**: 当用户查询涉及异常、突变、不正常时

**典型任务**:
- "检测数据中的异常模式"
- "识别可能的插瓶干扰行为"
- "评估异常的置信度"

**输出**: `anomaly_result.json`

---

### 3. 规则推理子智能体 (rule-reasoning-agent) ⚖️

**位置**: `subagents/rule-reasoning-agent/`

**入口脚本**: `run_rule_reasoning.py`

**职责**:
- 法规规则匹配和验证（GB 18918-2002、水污染防治法等）
- 工艺机理校验（生化反应、物料平衡、相关性、氮转化规则）
- 专家经验推理（造假模式识别、案例匹配）
- 违规性质判定和嫌疑等级评估

**使用场景**: 当用户查询涉及违规、超标、判定标准时

**典型任务**:
- "验证检测结果是否符合排放标准"
- "根据工艺知识判断数据合理性"
- "判定违规类型和嫌疑等级"

**输出**: `rule_reasoning_result.json`

---

### 4. 研判预警与处置执行子智能体 (disposition-execution-agent) 🚨

**位置**: `subagents/disposition-execution-agent/`

**入口脚本**: `run_disposition.py`

**职责**:
- 融合共识算法（异常检测 + 规则推理）
- 三级预警分类（一般/较重/严重）
- 工单生成（包含数据溯源、核查要点、法规引用）
- 预警报告生成

**使用场景**: 当用户需要预警、工单、通知时

**典型任务**:
- "综合分析结果并生成预警"
- "创建处置工单"
- "生成处置建议方案"

**输出**: `disposition_result.json`

---

## 调用工具

主智能体通过以下工具调用子智能体：

### call_subagent(name, task, context?)

调用指定的子智能体执行任务。

**参数**:
- `name` (str): 子智能体名称，必须是以下之一：
  - "multi-dimensional-data-perception-agent"
  - "anomaly-detection-agent"
  - "rule-reasoning-agent"
  - "disposition-execution-agent"
- `task` (str): 任务描述
- `context` (dict, 可选): 前置结果，用于传递上下文

**返回**:
- `success` (bool): 是否成功
- `result` (str): 执行结果
- `error` (str): 错误信息（如果有）

### initialize_subagents()

初始化所有子智能体实例。通常在系统启动时自动调用。

### list_available_subagents()

列出所有可用的子智能体。

### cleanup_sessions(days)

清理指定天数之前的旧会话。

---

## 调用决策树

当收到用户查询时，按以下决策调用子智能体：

```
用户查询
    ↓
[1] 需要数据吗？
    ├─ 提到"数据"、"指标"、"监测"、"进水"、"出水"
    ├─ 提到"最近N小时"、"今天"、"昨天"
    └─ YES → 调用 multi-dimensional-data-perception-agent
    └─ NO → 跳过数据分析步骤
    ↓
[2] 需要异常检测吗？
    ├─ 提到"异常"、"不正常"、"突变"、"是否正常"
    └─ YES → 调用 anomaly-detection-agent
    └─ NO → 跳过异常检测
    ↓
[3] 需要违规判定吗？
    ├─ 提到"违规"、"超标"、"违反标准"、"是否达标"
    ├─ 提到"插瓶"、"稀释"、"排放异常"
    └─ YES → 调用 rule-reasoning-agent
    └─ NO → 跳过违规判定
    ↓
[4] 需要预警/工单吗？
    ├─ 提到"预警"、"工单"、"通知"、"处置"
    └─ YES → 调用 disposition-execution-agent
    └─ NO → 跳过处置执行
    ↓
[5] 整合结果，生成自然语言回答
```

---

## 示例分析

### 示例1: "最近24小时出水COD异常吗？"

- ✅ 需要数据 → multi-dimensional-data-perception-agent
- ✅ 需要异常检测 → anomaly-detection-agent
- ❌ 不需要违规判定 → 跳过 rule-reasoning-agent
- ❌ 不需要预警 → 跳过 disposition-execution-agent

**调用**: data-perception → anomaly-detection → 整合回答

---

### 示例2: "最近24小时出水是否超标？"

- ✅ 需要数据 → multi-dimensional-data-perception-agent
- ✅ 需要异常检测 → anomaly-detection-agent
- ✅ 需要违规判定 → rule-reasoning-agent
- ❌ 不需要预警 → 跳过 disposition-execution-agent

**调用**: data-perception → anomaly-detection → rule-reasoning → 整合回答

---

### 示例3: "生成今天的异常预警工单"

- ✅ 需要数据 → multi-dimensional-data-perception-agent
- ✅ 需要异常检测 → anomaly-detection-agent
- ✅ 需要违规判定 → rule-reasoning-agent
- ✅ 需要预警 → disposition-execution-agent

**调用**: data-perception → anomaly-detection → rule-reasoning → disposition-execution → 整合回答

---

## 子智能体协作关系

```
multi-dimensional-data-perception-agent (第一步)
    ↓ processed_data
anomaly-detection-agent (第二步)
    ↓ anomalies
rule-reasoning-agent (第三步)
    ↓ conclusion
disposition-execution-agent (第四步，可选)
    ↓ work_order
```

**重要原则**:
- 子智能体可以**并行调用**（当互不依赖时）
- 子智能体可以**串行调用**（当存在依赖时）
- 前一个子智能体的结果可以作为后一个子智能体的输入（通过`context`参数）

---

## 调用原则

### 1. 单一职责优先
- 优先调用最相关的子智能体，而非同时调用多个
- 每个子智能体专注于特定领域，避免职责重叠

### 2. 协作按需
- 当任务需要多领域协作时，可以按顺序调用多个子智能体
- 将前序子智能体的关键结果传递给后续子智能体

### 3. 避免重复
- 不要为同一任务重复调用同一个子智能体
- 已有结果可以直接使用时，避免重复计算

---

## 何时调用子智能体

**应该调用**:
- 需要专业领域知识（数据感知、异常检测、规则推理、处置执行）
- 需要执行复杂计算或分析
- 需要访问特定数据源或知识库

**不应该调用**:
- 简单的信息查询（可以直接回答）
- 已有结果的重复请求
- 超出子智能体职责范围的任务

---

## 错误处理

### 子智能体调用失败
如果子智能体调用失败（`success: false`），应该：
1. 检查错误信息
2. 如果是临时性问题，可以重试
3. 如果是配置问题，提示用户检查系统配置
4. 向用户清晰解释错误原因

### 子智能体不存在
如果调用的子智能体不存在：
1. 检查子智能体名称是否正确
2. 使用 `list_available_subagents()` 查看可用子智能体
3. 提示用户正确的子智能体名称

---

## 结果整合

### 整合原则

主智能体负责将各子智能体的结果整合成清晰、有用的回答。

**整合步骤**：
1. **提取关键信息**: 从每个子智能体的结果中提取核心发现
2. **逻辑关联**: 理解各子智能体结果之间的关系
3. **综合判断**: 结合多方信息形成最终结论
4. **用户适配**: 根据用户问题调整回答的重点和形式

### 回答结构

**标准回答格式**：
```
1. 直接回答：首先回答用户的问题（1-2句话）
2. 关键发现：列出重要的数据点和发现
3. 详细分析：提供必要的背景和解释
4. 可视化（可选）：如果数据适合，提供图表
5. 建议（可选）：如果有明确的行动建议
```

### 示例：综合违规检测

**用户问题**: "最近24小时是否有违规排放？"

**子智能体结果**:
- `data-perception`: "获取了24小时数据，共288条记录，数据完整率98%"
- `anomaly-detection`: "检测到1处异常：02:00-06:00 COD值恒定在95mg/L，std=0.08"
- `rule-reasoning`: "符合插瓶干扰特征：恒定值2小时以上，接近限值(95%)，标准差<0.1"

**主智能体整合回答**:
```
是的，最近24小时检测到1起疑似插瓶干扰违规。

【关键发现】
- 时间：02:00-06:00（持续4小时）
- 指标：COD恒定在95mg/L（限值100mg/L）
- 特征：标准差仅0.08，数值稳定在限值的95%

【判定】
符合插瓶干扰特征，置信度：高

【建议】
建议调取该时段的视频监控核实，并加强夜间巡查。
```

### 整合技巧

**突出重点**:
- 把最重要的发现放在前面
- 用数字和具体数据支撑结论
- 避免技术术语，用通俗语言解释

**保持准确**:
- 不夸大或缩小问题
- 明确区分"疑似"和"确认"
- 提供置信度评估

**用户导向**:
- 根据用户身份调整回答深度
- 运营人员→简明扼要，突出行动建议
- 技术人员→详细数据，支持深入分析

---

## 违规判定标准

详见 `workspace/MEMORY.md`

**4种违规类型**:
1. **插瓶干扰**: 恒定值（std<0.1）+ 接近限值（80-100%）
2. **稀释排放**: 多指标同步下降50% + 去除率>95%
3. **人工拟合**: 过度平滑（R²>0.99）
4. **恶意逃避**: 数据缺失率>20%

---

## 图表输出

对于数据可视化，在响应中包含 ECharts 配置：

```json
{
  "content": "数据说明...",
  "chart": {
    "title": {"text": "标题"},
    "xAxis": {"type": "category", "data": ["时间1", "时间2"]},
    "yAxis": {"type": "value"},
    "series": [{"name": "指标名", "data": [值1, 值2], "type": "line"}]
  }
}
```

当用户要求图表或可视化时，生成有效的 ECharts option JSON。

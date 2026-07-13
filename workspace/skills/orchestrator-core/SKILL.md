---
name: orchestrator-core
description: "Multi-agent orchestration for wastewater monitoring. Coordinates 4 sub-agents: data-perception, anomaly-detection, rule-reasoning, disposition-execution."
---

# 编排器核心技能

## 技能描述

本技能是主智能体的核心编排能力，负责管理和调用4个子智能体完成复杂的废水监测任务。通过LLM决策和自然语言描述引导，实现智能的任务分发和结果聚合。

## 子智能体职责

### multi-dimensional-data-perception-agent（多维数据感知子智能体）

**职责范围：**
- 多源数据获取（CSV、API、数据库）
- 数据质量检查和清洗
- 时序数据对齐处理
- 字段标准化处理
- 数据完整性验证

**典型任务：**
- "获取最近24小时的监测数据"
- "检查数据质量并标记异常值"
- "对齐多个传感器的时间序列数据"

### anomaly-detection-agent（异常检测子智能体）

**职责范围：**
- 5类异常识别：平稳、突变、趋势、周期、高频波动
- 4类违规检测：插瓶干扰、人工拟合、稀释排放、恶意逃避
- 置信度评估和异常评分
- 异常模式聚类分析

**典型任务：**
- "检测数据中的异常模式"
- "识别可能的插瓶干扰行为"
- "评估异常的置信度"

### rule-reasoning-agent（规则推理子智能体）

**职责范围：**
- 法规规则匹配和验证
- 工艺机理校验
- 专家推理和经验应用
- 违规性质判定

**典型任务：**
- "验证检测结果是否符合排放标准"
- "根据工艺知识判断数据合理性"
- "应用专家经验分析异常"

### disposition-execution-agent（研判预警与处置执行子智能体）

**职责范围：**
- 融合共识算法
- 三级预警分类（高、中、低）
- 工单生成和分发
- 处置建议生成

**典型任务：**
- "综合分析结果并生成预警"
- "创建处置工单"
- "生成处置建议方案"

## 调用原则

### 1. 单一职责优先
- 优先调用最相关的子智能体，而非同时调用多个
- 每个子智能体专注于特定领域，避免职责重叠

### 2. 协作按需
- 当任务需要多领域协作时，可以按顺序调用多个子智能体
- 前一个子智能体的结果可以作为后一个子智能体的输入

### 3. 结果传递
- 将前序子智能体的关键结果传递给后续子智能体
- 保持上下文的连贯性

### 4. 避免重复
- 不要为同一任务重复调用同一个子智能体
- 已有结果可以直接使用时，避免重复计算

## 典型工作流

### 数据异常检测完整流程

```
用户查询 → 主智能体分析 → 调用子智能体 → 结果聚合 → 响应用户

详细步骤：
1. 调用 multi-dimensional-data-perception-agent 获取数据
2. 调用 anomaly-detection-agent 检测异常
3. 调用 rule-reasoning-agent 进行规则验证
4. 调用 disposition-execution-agent 生成预警
5. 主智能体汇总结果并生成自然语言响应
```

### 简化数据查询流程

```
用户查询 → 主智能体分析 → 调用单个子智能体 → 响应用户

示例：
用户: "获取最新的监测数据"
1. 调用 multi-dimensional-data-perception-agent 获取数据
2. 直接响应用户
```

## 工具说明

### call_subagent

调用指定的子智能体执行任务。

**参数：**
- `subagent_name` (str): 子智能体名称，必须是以下之一：
  - "multi-dimensional-data-perception-agent"
  - "anomaly-detection-agent"
  - "rule-reasoning-agent"
  - "disposition-execution-agent"
- `task` (str): 需要子智能体执行的任务描述
- `context` (dict, 可选): 附加的上下文信息

**返回：**
- `success` (bool): 是否成功
- `result` (str): 执行结果
- `error` (str): 错误信息（如果有）

**使用示例：**
```
调用 anomaly-detection-agent 检测异常
subagent_name: "anomaly-detection-agent"
task: "检测以下数据中的异常模式：[数据]"
```

### initialize_subagents

初始化所有子智能体实例。

**参数：**
- `model` (str, 可选): LLM模型名称
- `base_url` (str, 可选): API基础URL
- `api_key` (str, 可选): API密钥

**返回：**
- `success` (bool): 是否成功
- `count` (int): 创建的子智能体数量
- `subagents` (list): 子智能体名称列表

**注意：** 通常在系统启动时自动调用，无需手动调用。

### list_available_subagents

列出所有可用的子智能体。

**返回：**
- `success` (bool): 是否成功
- `subagents` (list): 子智能体名称列表

## 决策指南

### 何时调用子智能体

**应该调用：**
- 需要专业领域知识（数据感知、异常检测、规则推理、处置执行）
- 需要执行复杂计算或分析
- 需要访问特定数据源或知识库

**不应该调用：**
- 简单的信息查询（可以直接回答）
- 已有结果的重复请求
- 超出子智能体职责范围的任务

### 选择哪个子智能体

| 用户需求 | 调用的子智能体 |
|---------|--------------|
| 获取/处理数据 | multi-dimensional-data-perception-agent |
| 检测异常/违规 | anomaly-detection-agent |
| 规则匹配/工艺校验 | rule-reasoning-agent |
| 生成预警/工单 | disposition-execution-agent |

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
2. 使用 `list_available_subagents` 查看可用子智能体
3. 提示用户正确的子智能体名称

## 技能约束

本技能有以下约束：
- 只能调用预定义的4个子智能体
- 子智能体之间不能直接通信，必须通过主智能体中转
- 子智能体的执行结果需要主智能体进行汇总和解释
- 一次只能调用一个子智能体（串行调用）

## 技能进化

本技能会根据使用情况不断优化：
- 记录常见的调用模式
- 优化工作流路径
- 改进错误处理
- 增强调试信息

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

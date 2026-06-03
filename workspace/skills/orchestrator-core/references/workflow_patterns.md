# 工作流模式库

## 版本信息

- **版本**: 2.1.0
- **更新日期**: 2026-05-15

## 工作流模式定义

### 1. 标准分析流程 (standard_analysis)

**适用场景**: 分析查询，需要完整的数据治理→特征分析→异常检测→规则推理流程

```yaml
workflow_id: standard_analysis
name: 标准分析流程
description: 完整的四层数据分析流程
steps:
  - name: 数据获取与治理
    agent: data-governance-agent
    operation: acquire_and_clean
    output: cleaned_data

  - name: 特征提取与分析
    agent: feature-analysis-agent
    operation: extract_and_analyze
    input: cleaned_data
    depends_on: [数据获取与治理]
    output: features

  - name: 异常检测
    agent: anomaly-detection-agent
    operation: detect_anomalies
    input: features
    depends_on: [特征提取与分析]
    output: anomalies

  - name: 规则推理
    agent: rule-reasoning-agent
    operation: reason_violations
    input: anomalies
    depends_on: [异常检测]
    output: violations
```

### 2. 双数据流对比 (dual_stream_comparison)

**适用场景**: 进出水对比分析，处理效率评估

```yaml
workflow_id: dual_stream_comparison
name: 双数据流对比
description: 进水和出水的联合分析
steps:
  - name: 进水数据处理
    agent: data-governance-agent
    operation: process_influent
    output: influent_data

  - name: 出水数据处理
    agent: data-governance-agent
    operation: process_effluent
    output: effluent_data

  - name: 跨数据流分析
    module: cross_domain_analyzer
    operation: analyze_dual_stream
    input: [influent_data, effluent_data]
    depends_on: [进水数据处理, 出水数据处理]
    output: dual_stream_result
```

### 3. 状态查询 (status_query)

**适用场景**: 查询系统当前运行状态

```yaml
workflow_id: status_query
name: 状态查询
description: 获取当前数据状态
steps:
  - name: 获取数据状态
    agent: data-governance-agent
    operation: get_status
    output: status_info
```

### 4. 历史查询 (history_query)

**适用场景**: 查询历史数据和案例

```yaml
workflow_id: history_query
name: 历史查询
description: 历史数据查询和案例匹配
steps:
  - name: 历史数据获取
    agent: data-governance-agent
    operation: query_history
    output: history_data

  - name: 案例匹配
    agent: rule-reasoning-agent
    operation: match_historical_cases
    depends_on: [历史数据获取]
    output: matched_cases
```

### 5. 报告生成 (report_generation)

**适用场景**: 生成监测分析报告

```yaml
workflow_id: report_generation
name: 报告生成
description: 完整分析流程+报告格式化
steps:
  - name: 完整分析
    workflow: standard_analysis
    output: analysis_result

  - name: 报告格式化
    agent: rule-reasoning-agent
    operation: generate_report
    input: analysis_result
    depends_on: [完整分析]
    output: report
```

## 执行策略

### 并行执行条件

以下任务组可以并行执行：
- 进水数据处理 和 出水数据处理
- 独立的历史查询（不同时间段）

### 串行执行条件

以下任务必须串行执行：
- 标准分析流程的4个步骤（依赖关系）
- 报告生成必须等待分析完成

## 工作流参数

### 通用参数

```yaml
parameters:
  monitoring_point: str  # 监测点位（进水/出水）
  indicators: list      # 监测指标列表
  time_range: dict      # 时间范围
  analysis_target: str  # 分析目标
  output_type: str      # 输出类型（json/report/alert）
```

### 默认值

```yaml
defaults:
  monitoring_point: "出水"
  indicators: ["pH", "COD", "NH3-N", "TN", "TP"]
  time_range:
    value: 1
    unit: "hours"
  output_type: "json"
```

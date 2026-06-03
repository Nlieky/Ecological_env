---
name: rule-reasoning-core
description: 环境监测数据违规判定技能。当需要基于法规、工艺机理和专家经验进行违规判定时使用此技能。支持法规规则匹配（《水污染防治法》、GB 18918-2002、HJ 915-2017）、工艺机理校验（pH-COD协同、氨氮-总氮转化、质量平衡）、专家经验推理（相似度匹配，阈值0.8）、违规结论生成（嫌疑等级判定、取证要点）。适用于污水处理、排污口监测等环境监测场景的违规判定。是异常检测后的必用技能，用于判定违规性质和嫌疑等级。
version: 1.0.0
---

# 环境监测数据违规判定

此技能提供基于法规、工艺机理和专家经验的违规判定能力，是异常检测结果的法律化、业务化解读。

## 为什么违规判定很重要

**异常≠违规**——异常检测只能发现数据异常，违规判定才能确定是否构成违规。

本技能完全符合专利要求（相似度阈值0.8、嫌疑等级判定规则），确保违规判定的准确性和可追溯性。

## 推荐使用方式

### 一键完成完整判定（推荐）

```python
from scripts import run_rule_reasoning

task = {
    "task_id": "violation_001",
    "data": feature_data,  # 来自data-governance-agent
    "anomalies": anomaly_list,  # 来自anomaly-detection-agent
    "correlation_results": correlation_data,  # 来自feature-analysis-agent
    "trend_results": trend_data,  # 来自feature-analysis-agent
    "config": {}
}

result = run_rule_reasoning(task)
```

**返回结果包含**：
- `regulation_check`: 法规合规性校验结果
- `process_validation`: 工艺机理违背判定
- `expert_reasoning`: 专家经验推理结果
- `violation_conclusion`: 违规结论（嫌疑等级、取证要点、处罚建议）

### 分步执行（仅特殊需求时）

```python
from scripts.regulation_matcher import RegulationMatcher
from scripts.process_validator import ProcessValidator
from scripts.expert_reasoner import ExpertReasoner
from scripts.violation_generator import ViolationGenerator

# 1. 法规规则匹配
matcher = RegulationMatcher()
regulation_result = matcher.match(anomalies, data)

# 2. 工艺机理校验
validator = ProcessValidator()
process_result = validator.validate(anomalies, correlation_results, trend_results, data)

# 3. 专家经验推理
reasoner = ExpertReasoner()
expert_result = reasoner.reason(anomalies, regulation_result, process_result)

# 4. 违规结论生成
generator = ViolationGenerator()
violation_result = generator.generate(anomalies, regulation_result, process_result, expert_result, data)
```

## 法规规则匹配

支持法规：
- 《水污染防治法》
- GB 18918-2002 城镇污水处理厂污染物排放标准
- HJ 915-2017 地表水自动监测技术规范

标准限值（一级A标）：
| 指标 | 限值 |
|------|------|
| COD | 50 mg/L |
| TN | 15 mg/L |
| NH3-N | 5 mg/L |
| TP | 0.5 mg/L |
| pH | 6-9 |

## 工艺机理校验

| 工艺规则 | 校验内容 | 违背判定 |
|----------|----------|----------|
| pH-COD协同 | 酸性条件下COD降解效率应更高 | pH稳定但COD波动大 |
| 氨氮-总氮转化 | NH3-N是TN的组成部分 | 氨氮与总氮相关性<0.3 |
| 溶解氧-污染物降解 | 好氧条件下有机物应被降解 | DO正常但污染物不降反升 |
| 质量平衡 | 物质守恒定律 | 去除率异常或违背理论值 |

## 专家经验推理

| 专利参数 | 要求值 | 说明 |
|----------|--------|------|
| 相似度阈值 | 0.8 | ≥0.8判定为同类违规 |

典型违规模式：
- **插瓶干扰**：使用标准溶液模拟达标（指标恒定且接近标准限值）
- **稀释排放**：加清水稀释降低浓度（多指标同步下降且低位）
- **人工拟合**：数据过度平滑（平滑度异常、R²过高）
- **恶意逃避**：设备异常或停运（数据缺失率异常、夜间空白）

## 嫌疑等级判定（专利要求）

| 条件 | 嫌疑等级 |
|------|----------|
| 异常模式匹配数量≥2 且 存在工艺机理违背 | 高风险 (critical/high) |
| 异常模式匹配数量=1 且 存在工艺机理违背 | 中风险 (medium) |
| 仅存在异常模式匹配但无机理违背 | 低风险 (low) |

## 配置参数说明

### 工艺机理校验
- `nh3_tn_correlation_min`: 氨氮-总氮最小相关系数（默认0.3）
- `nh3_tn_ratio_min`: 出水氨氮/总氮比值下限（默认0.2）
- `nh3_tn_ratio_max`: 出水氨氮/总氮比值上限（默认0.6）

### 专家经验推理
- `similarity_threshold`: 案例相似度阈值（默认0.8，专利要求值）

### 违规结论生成
- `high_risk_condition`: 高风险条件（默认"patterns>=2 AND process_violation"）
- `medium_risk_condition`: 中风险条件（默认"patterns==1 AND process_violation"）
- `low_risk_condition`: 低风险条件（默认"patterns>0 AND NOT process_violation"）

## 参考文档

需要详细配置或规范时，查阅以下文档：

- `references/regulations/` - 法规库
- `references/process_knowledge/` - 工艺知识库
- `references/expert_experience/` - 专家经验库
- 专利文档 - 规则推理子智能体规范

## 常见问题

**Q: 异常检测和违规判定的区别？**
A: 异常检测发现数据异常（如突变、恒定），违规判定确定是否构成违规（如插瓶干扰、稀释排放）。异常是数据层面，违规是业务层面。

**Q: 相似度阈值为什么是0.8？**
A: 这是专利要求的参数。当与历史案例相似度≥0.8时，判定为同类违规，提高判定准确性。

**Q: 嫌疑等级如何判定？**
A: 严格按照专利规则：模式数≥2且有机理违背→高风险；模式数=1且有机理违背→中风险；仅模式匹配无机理违背→低风险。

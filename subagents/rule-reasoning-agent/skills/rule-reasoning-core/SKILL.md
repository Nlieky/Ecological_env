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

# 处置执行子智能体优化设计

> 2026-07-28 · brainstorm 产出 · 子智能体优化系列(4/4,最后一个)

## 背景

处置执行子智能体(`disposition-execution`)框架完整(融合共识 + 预警分级 + 工单 + 报告),但:
1. **预警级别(一般/较重/严重)是旧设定,无依据**:规则推理已定义嫌疑等级(高/中/低/无,基于合规×工艺矩阵),处置执行不该另搞一套
2. **anomaly_confidence 对不上**:现状用 `max(score)/3.0`,但异常检测 redesign 后输出 `confidence`(0.6×分数+0.4×相似度)
3. **两套分级脱节**:预警 3 级 vs 嫌疑 4 档,逻辑上没关联
4. **AGENTS 过时**(预加载/skill_view,通病)

前两个子智能体(异常检测 + 规则推理)已经把判定做完,**处置执行应消费上游结论,不重复判定**。

## 设计原则

1. **消费上游结论**:读规则推理的 `suspicion_level` + `violation_types` + `evidence_points` + `confidence`,不自己再判定
2. **嫌疑等级 → 处置行动**:直接映射(高→立即调查,中→核查,低→监控,无→正常)
3. **废弃旧机制**:预警级别(一般/较重/严重)+ ConsensusEngine 融合共识(规则推理已综合 anomaly+violation,处置执行不重复)
4. **工单带证据**:法规引用来自规则推理的 evidence_points

## 嫌疑等级 → 处置行动映射

| 嫌疑等级(规则推理给) | 处置行动 | 工单 |
|---|---|---|
| **高**(违规 + 工艺违背) | 立即调查取证 | 出工单(核查要点 + 法规 + 取证建议) |
| **中**(未违规 + 工艺违背) | 现场核查 | 出工单(核查要点) |
| **低**(违规 + 无违背) | 持续监控 | 出监控建议 |
| **无**(未违规 + 无违背) | 无违规 | 正常报告(不出工单) |

## 工单 + 报告

- **工单**(`work_order`):核查要点 + 法规引用(带规则推理 evidence_points)+ 处置建议
- **报告**(`report`):报告编号 + 完整预警信息(嫌疑等级/违规类型/证据/处置行动)

## 输出契约(`disposition_result.json`)

```json
{
  "suspicion_level": "高",
  "suspicion_level_cn": "高风险",
  "violation_types": ["插瓶干扰"],
  "action": "立即调查取证",
  "confidence": 0.82,
  "work_order": {
    "id": "WO_20260728_...",
    "inspection_points": ["pH 连续 4 小时恒定(7-14 12:00~16:00)"],
    "legal_references": ["《水污染防治法》第二十三条"],
    "recommended_actions": ["现场核查探头", "调取监控"]
  },
  "report": {"report_id": "...", "content": "..."},
  "evidence_points": [...]
}
```

**废弃**:`alert.level`(旧预警级别 一般/较重/严重)、`fusion`(ConsensusEngine 融合共识)。

下游:主智能体汇总 disposition_result 生成最终报告(含预警 + 工单)。

## 改动清单

| 文件 | 改动 |
|---|---|
| `run_disposition.py` | 废弃 ConsensusEngine 融合 + 旧预警分级;直接读规则推理 `suspicion_level` → 处置行动映射;工单带 `evidence_points` |
| `alert_classifier.py` | 改成嫌疑等级 → 处置行动映射(或废弃,逻辑并入 run_disposition) |
| `consensus_engine.py` | 废弃(规则推理已综合) |
| `work_order_generator.py` | 工单带 evidence_points(法规引用、核查要点来自规则推理证据) |
| `report_generator.py` | 报告含嫌疑等级/违规类型/证据/处置行动 |
| `SOUL.md` / `AGENTS.md` | 废弃预警 3 级,改嫌疑等级 4 档→处置行动;skill_view 机制(去过时) |

## 测试

- 嫌疑等级 → 处置行动映射单元(4 档各测)
- 工单生成(带 evidence_points + 法规引用)
- 端到端:`smoke_test.py` 覆盖(处置执行产出 disposition_result,含 suspicion_level/action/work_order)

## 决策记录

- **废弃预警级别 + 融合共识**:前两个子智能体(异常检测 + 规则推理)已打好基础(嫌疑等级 + 证据),处置执行消费上游结论、不重复判定
- **嫌疑 → 处置映射**:高→立即调查取证,中→现场核查,低→持续监控,无→正常报告
- **工单带证据**:法规引用、核查要点来自规则推理 evidence_points(可追溯)
- **anomaly_confidence 不再用**:异常检测的 confidence 已在规则推理里综合成嫌疑等级,处置执行不直接用 anomaly

## 范围

本 spec 仅处置执行子智能体(4/4,最后一个)。数据感知(1/4)、异常检测(2/4)、规则推理(3/4)见各自 spec。**4 个子智能体 + 报告可视化 spec 全部完成**,可进入实现阶段(writing-plans)。

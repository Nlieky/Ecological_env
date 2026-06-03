# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your* specifics — the stuff that's unique to your setup.

## Knowledge Base Paths

| 知识库类型 | 路径 |
|-----------|------|
| 法规库 | shared/knowledge/regulations/ |
| 工艺知识库 | shared/knowledge/process_knowledge/ |
| 违规模式特征库 | shared/knowledge/violation_patterns/ |
| 专家经验库 | shared/knowledge/expert_experience/ |

## Regulation References

| 法规名称 | 关键条款 |
|---------|---------|
| 水污染防治法 | 第二十三条（禁止篡改、伪造监测数据） |
| HJ 915-2017 | 数据质量控制要求 |
| 城镇污水处理厂污染物排放标准 | 各污染物排放限值 |

## Process Mechanism Rules

### pH-COD协同规则

- 正常相关性：≥0.3
- 异常判定：相关性<0.3 且存在其他违规特征
- 物理意义：pH值影响COD去除效率

### 氨氮-总氮转化规则

- 正常相关性：≥0.3
- 出水氨氮/总氮比值：20-60%
- 异常判定：比值异常且去除率异常
- 物理意义：硝化反应将氨氮转化为硝酸盐氮

### 质量平衡规则

- 公式：C_in × (1 - η) ≈ C_out
- 允许误差：±20%
- 异常判定：误差超范围且其他指标异常
- 物理意义：污染物质量守恒

## Suspic ion Level Criteria

| 级别 | 置信度范围 | 处理建议 |
|------|-----------|----------|
| 高风险 | ≥0.9 | 立即上报，现场核查 |
| 中风险 | 0.7-0.9 | 进一步调查 |
| 低风险 | 0.5-0.7 | 持续观察，收集证据 |

## Investigation Points

| 违规类型 | 调查要点 |
|---------|---------|
| 插瓶干扰 | 检查采样探头位置、核查设备校准记录、调阅视频监控 |
| 稀释排放 | 检查进水水量、核查处理设施、检查排口清水接入 |
| 人工拟合 | 分析统计特征、检查校准记录、与相似企业对比 |
| 恶意逃避 | 检查传输日志、核查运行记录、调阅监控录像 |

## Related

- [Agent workspace](/concepts/agent-workspace)

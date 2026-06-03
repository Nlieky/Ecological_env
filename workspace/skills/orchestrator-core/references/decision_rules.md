# 决策规则库

## 版本信息

- **版本**: 2.1.0
- **更新日期**: 2026-05-15

## 路由决策规则

### 意图识别规则

| 意图类型 | 关键词 | 路由目标 | 执行模式 | 优先级 |
|---------|--------|---------|----------|--------|
| analysis_query | 分析、检测、判断、识别、诊断、异常、违规、偷排 | 全部4个子智能体（串行） | SEQUENTIAL | 1 |
| history_query | 历史、过去、之前、前几天、上个月、以前 | data-governance-agent + rule-reasoning-agent | PARALLEL | 2 |
| status_query | 状态、运行、当前、现在、怎么样 | data-governance-agent | SINGLE | 3 |
| report_generation | 报告、总结、汇总、导出 | 全部4个子智能体 | SEQUENTIAL | 1 |

### 路由决策伪代码

```python
def route_decision(intent):
    if intent.intent_type == "analysis_query":
        if "偷排" in intent.analysis_target or "稀释" in intent.analysis_target:
            priority = 1  # 高优先级
        else:
            priority = 2
        return RouteDecision(
            target_agents=["data-governance", "feature-analysis", "anomaly-detection", "rule-reasoning"],
            strategy=RouteStrategy.SEQUENTIAL,
            priority=priority
        )
    elif intent.intent_type == "status_query":
        return RouteDecision(
            target_agents=["data-governance"],
            strategy=RouteStrategy.SINGLE,
            priority=3
        )
    # ... 其他规则
```

## 违规判定规则

### 插瓶干扰判定

```yaml
规则名称: 插瓶干扰判定
触发条件:
  - 指标恒定时长 >= 2小时
  - 指标值在标准限值的80-100%范围内
  - 数据标准差 < 0.1
判定结果:
  - 置信度 >= 0.9: 高风险违规
  - 置信度 >= 0.7: 中等风险违规
处理建议:
  - 检查采样探头和采样管路
  - 核查在线监测设备校准记录
  - 调阅视频监控确认采样情况
```

### 稀释排放判定

```yaml
规则名称: 稀释排放判定
触发条件:
  - 多指标（COD、氨氮、总磷）同步下降 > 50%
  - 所有指标处于历史低位
  - 去除率异常高（> 95%）
判定结果:
  - 置信度 >= 0.8: 高风险违规
  - 置信度 >= 0.6: 中等风险违规
处理建议:
  - 检查进水水量记录
  - 核查处理设施运行状况
  - 检查排口附近是否有清水接入
```

### 人工拟合判定

```yaml
规则名称: 人工拟合判定
触发条件:
  - 数据过度平滑（标准差异常低）
  - 符合数学函数特征（线性、多项式）
  - 缺少自然波动
判定结果:
  - 置信度 >= 0.8: 高风险违规
  - 置信度 >= 0.6: 中等风险违规
处理建议:
  - 分析数据统计特征
  - 检查历史数据校准记录
  - 与相似企业数据对比
```

### 恶意逃避判定

```yaml
规则名称: 恶意逃避判定
触发条件:
  - 数据缺失率异常高（> 20%）
  - 夜间或特定时段空白模式
  - 设备故障时间与违规时间相关
判定结果:
  - 置信度 >= 0.7: 中等风险违规
处理建议:
  - 检查数据传输日志
  - 核查设备运行记录
  - 调阅监控录像
```

## 工艺机理校验规则

### pH-COD协同规则

```yaml
规则名称: pH-COD协同校验
条件: pH和COD相关性校验
判定:
  - 正常情况下: 相关性 >= 0.3
  - 异常情况: 相关性 < 0.3
违规: 相关性异常低且存在其他违规特征
```

### 氨氮-总氮转化规则

```yaml
规则名称: 氨氮-总氮转化校验
条件:
  - 氨氮与总氮相关性 >= 0.3
  - 出水氨氮/总氮比值: 20-60%
判定:
  - 比值异常: 可能存在数据问题或工艺异常
违规: 比值异常且去除率异常
```

### 质量平衡规则

```yaml
规则名称: 质量平衡校验
条件: 进水浓度 * (1 - 去除率) ≈ 出水浓度
判定:
  - 允许误差: ±20%
违规: 误差超过允许范围且其他指标异常
```

## 风险评估规则

### 风险等级计算

```python
def calculate_risk_level(anomalies, violations):
    # 有违规则至少中风险
    if violations:
        if any(v.suspect_level == "高风险" for v in violations):
            return RiskLevel.HIGH
        else:
            return RiskLevel.MEDIUM

    # 根据异常数量和严重程度
    if anomalies:
        high_score_count = sum(1 for a in anomalies if a.score >= 0.8)
        if high_score_count >= 3:
            return RiskLevel.HIGH
        elif high_score_count >= 1:
            return RiskLevel.MEDIUM

    return RiskLevel.LOW
```

## 降级决策规则

### 降级策略选择

| 子智能体 | 故障类型 | 降级策略 |
|---------|---------|----------|
| data-governance-agent | 轻微 | 使用缓存数据 |
| data-governance-agent | 严重 | 返回部分结果 |
| anomaly-detection-agent | 轻微 | 使用简化规则检测 |
| anomaly-detection-agent | 严重 | 跳过异常检测 |
| rule-reasoning-agent | 轻微 | 返回原始检测结果 |
| rule-reasoning-agent | 严重 | 跳过规则推理 |

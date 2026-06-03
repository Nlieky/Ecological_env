# 历史案例库

## 版本信息

- **版本**: 2.1.0
- **更新日期**: 2026-05-15

## 案例模板

每个案例包含以下字段：
- 案例ID
- 发生时间
- 监测点位
- 违规类型
- 异常特征
- 判定依据
- 处理过程
- 处理结果
- 经验总结

## 已收录案例

### 案例001: 插瓶干扰

```yaml
case_id: CASE_001
date: "2025-03-15"
monitoring_point: "出水口"
violation_type: 插瓶干扰

anomaly_features:
  - type: pH恒定
    duration: 48小时
    value_range: [7.8, 8.2]
    std: 0.05
  - type: COD恒定
    duration: 48小时
    value_range: [80, 85]
    proximity_to_limit: 85%

evidence:
  - pH值连续48小时保持不变（标准限值6-9）
  - COD值连续48小时保持不变（标准限值100mg/L）
  - 两指标值均在标准限值的80-90%范围内
  - 数据标准差异常低

decision:
  suspect_level: 高风险
  confidence: 0.95
  reasoning: 符合插瓶干扰典型特征

investigation:
  - 现场核查发现采样探头插入装有标准液的瓶中
  - 视频监控证实采样过程异常

outcome:
  - 确认违规
  - 责令整改
  - 处以罚款

lessons_learned:
  - 恒定且接近标准限值是插瓶干扰的重要特征
  - 多指标同时恒定增加判定置信度
  - 需要结合现场核查确认
```

### 案例002: 稀释排放

```yaml
case_id: CASE_002
date: "2025-04-20"
monitoring_point: "排放口"
violation_type: 稀释排放

anomaly_features:
  - type: 多指标同步下降
    indicators: [COD, 氨氮, 总磷]
    decline_rate: 50%
  - type: 去除率异常
    removal_rate: 98%
  - type: 数据处于历史低位

evidence:
  - COD从300mg/L降至150mg/L（降幅50%）
  - 氨氮从40mg/L降至20mg/L（降幅50%）
  - 总磷从8mg/L降至4mg/L（降幅50%）
  - 三指标同步下降，时间点一致
  - 去除率异常高达98%

decision:
  suspect_level: 中等风险
  confidence: 0.85
  reasoning: 多指标同步下降且去除率异常

investigation:
  - 现场检查发现雨水管接入应急池
  - 用水量与排水量不平衡

outcome:
  - 确认违规
  - 责令拆除非法管道
  - 恢复正常排放

lessons_learned:
  - 多指标同步下降是稀释排放的典型特征
  - 需要分析水量平衡关系
  - 去除率异常高是辅助判定依据
```

### 案例003: 人工拟合

```yaml
case_id: CASE_003
date: "2025-05-10"
monitoring_point: "出水口"
violation_type: 人工拟合

anomaly_features:
  - type: 数据过度平滑
    std: 0.02
  - type: 符合数学函数
    function: "线性"
    r_squared: 0.998
  - type: 缺少自然波动

evidence:
  - COD数据标准差仅为0.02（正常>0.5）
  - 数据完美符合线性关系（R²=0.998）
  - 缺少正常的时间序列波动
  - 与同期其他企业数据差异显著

decision:
  suspect_level: 高风险
  confidence: 0.90
  reasoning: 数据统计特征明显异常

investigation:
  - 检查发现数据修改日志
  - 承认人为调整数据

outcome:
  - 确认违规
  - 追究相关人员责任
  - 建立数据审核机制

lessons_learned:
  - 数据过度平滑是人工拟合的重要特征
  - 需要建立数据审核和日志机制
  - 与同类企业数据对比有助于发现异常
```

### 案例004: 恶意逃避

```yaml
case_id: CASE_004
date: "2025-06-01"
monitoring_point: "排放口"
violation_type: 恶意逃避

anomaly_features:
  - type: 数据缺失率异常
    missing_rate: 35%
  - type: 夜间空白模式
    pattern: "每日0-6点无数据"
  - type: 设备故障关联
    correlation: 0.95

evidence:
  - 数据缺失率达35%（正常<5%）
  - 每日0-6点无数据（夜间空白）
  - 设备"故障"时间与异常排放时间高度相关
  - 视频显示设备被人为关闭

decision:
  suspect_level: 中等风险
  confidence: 0.80
  reasoning: 数据缺失模式异常且有规律

investigation:
  - 调阅监控发现夜间人为关闭设备
  - 检查发现夜间偷排行为

outcome:
  - 确认违规
  - 责令整改
  - 处以罚款并追究责任

lessons_learned:
  - 有规律的数据缺失是恶意逃避的典型特征
  - 夜间空白模式需要重点关注
  - 需要建立设备状态监控机制
```

## 案例匹配规则

```python
def match_historical_case(current_anomaly):
    """
    匹配历史案例

    Args:
        current_anomaly: 当前异常特征

    Returns:
        匹配的历史案例列表及相似度
    """
    # 提取当前异常特征
    features = extract_features(current_anomaly)

    # 与历史案例比较
    similarities = []
    for case in historical_cases:
        similarity = calculate_similarity(features, case.features)
        if similarity >= 0.8:
            similarities.append((case, similarity))

    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities
```

## 案例统计

| 违规类型 | 案例数 | 确认率 |
|---------|--------|--------|
| 插瓶干扰 | 15 | 93% |
| 稀释排放 | 12 | 83% |
| 人工拟合 | 8 | 88% |
| 恶意逃避 | 10 | 70% |

## 案例更新

- 新案例由专家审核后添加
- 每季度更新案例统计
- 每年重新评估案例有效性

---
name: anomaly-detection-core
description: 环境监测数据异常检测与特征分析技能。当需要检测监测数据中的异常点、识别异常模式、检测违规行为或提取特征时使用此技能。支持5类异常特征（平稳、突变、趋势、周期、高频波动）、4类违规模式（插瓶干扰、人工拟合、稀释排放、恶意逃避）检测，以及时序特征提取、相关性分析和趋势分析。集成统计类（3σ、IQR、Grubbs）和机器学习类（孤立森林、One-Class SVM）算法。适用于污水处理、排污口监测等环境监测场景。
version: 2.2.0
---

# 环境监测数据异常检测与特征分析

此技能提供环境监测数据的异常检测、违规模式识别和特征分析能力，是规则推理的重要输入。

## 为什么异常检测很重要

**异常监测是发现违规行为的第一道防线**——虚假排放往往表现为数据的异常模式。

本技能完全符合专利要求（5类异常特征、4类违规模式、孤立森林contamination=0.1、异常分数阈值0.5、模式相似度阈值0.7），确保异常检测的有效性和可追溯性。

## 功能模块

### 1. 异常检测
- 算子适配与检测
- 异常评分
- 模式识别
- 违规检测
- 置信度评估

### 2. 特征分析（从feature-analysis迁移）
- 时序特征提取：均值、方差、偏度、峰度等统计特征
- 相关性分析：Pearson/Spearman相关性
- 趋势分析：线性回归、移动平均、CCF等

## 支持的算子

### 统计类算子
- zscore: Z-score 异常检测
- iqr: IQR 方法
- grubbs: Grubbs 检验
- moving_average: 移动平均

### 机器学习算子
- isolation_forest: 孤立森林
- one_class_svm: One-Class SVM

### PyOD 算子（需要 pyod 库）
- hbos: 直方图异常检测
- ecod: 经验累积分布
- knn: K 近邻
- lof: 局部异常因子
- abod: 角度异常检测

### 深度学习算子（需要 torch 库）
- vae: 变分自编码器 - 通过重构误差检测异常

## 可视化
- plot_anomalies(): 异常检测结果可视化

## 推荐使用方式

### 一键完成完整检测（推荐）

```python
from scripts import detect_anomalies

result = detect_anomalies(
    data=monitoring_data,
    indicators=["pH", "COD", "NH3-N"],
    config={
        "operators": ["zscore", "iqr", "isolation_forest"],
        "pattern_threshold": 0.7,
        "contamination": 0.1
    }
)
```

**返回结果包含**：
- `anomalies`: 检测到的异常列表（带位置、分数、模式）
- `patterns`: 异常模式统计
- `violations`: 违规模式检测结果
- `confidence`: 置信度评估
- `suspicion_level`: 嫌疑等级

### 特征提取（新增）

```python
from scripts import extract_features

result = extract_features(
    data=monitoring_data,
    indicators=["pH", "COD", "NH3-N"],
    config={
        "include_time_features": True,
        "include_correlation": True,
        "include_trend": True,
        "correlation_method": "pearson"
    }
)
```

**返回结果包含**：
- `time_series_features`: 各指标的时序特征
- `correlations`: 相关性矩阵
- `trends`: 趋势分析结果

### 分步执行（仅特殊需求时）

```python
from scripts.operator_adapter import OperatorAdapter
from scripts.anomaly_scorer import AnomalyScorer
from scripts.pattern_recognizer import PatternRecognizer
from scripts.violation_detector import ViolationDetector
from scripts.confidence_evaluator import ConfidenceEvaluator
from scripts.time_series_features import TimeSeriesFeatures  # 新增
from scripts.correlation_analysis import CorrelationAnalyzer  # 新增
from scripts.trend_analysis import TrendAnalyzer  # 新增

# 1. 算子适配与检测
adapter = OperatorAdapter()
operator_results = adapter.apply_operators(data, indicators, ["zscore", "iqr"])

# 2. 异常评分
scorer = AnomalyScorer()
anomaly_scores = scorer.calculate_scores(data, operator_results)

# 3. 模式识别
recognizer = PatternRecognizer()
patterns = recognizer.recognize_patterns(data, anomaly_scores, threshold=0.7)

# 4. 违规检测
detector = ViolationDetector()
violations = detector.detect_violations(patterns["anomalies"], data)

# 5. 置信度评估
evaluator = ConfidenceEvaluator()
confidence = evaluator.evaluate(anomaly_scores, patterns, operator_results)
```

## 5类异常特征

| 异常类型 | 特征描述 | 检测方法 |
|----------|----------|----------|
| 平稳异常 | 指标长时间保持不变 | 标准差异常低 |
| 突变异常 | 相邻时间点大幅变化 | 差分超出阈值 |
| 趋势异常 | 单向均匀上升/下降 | 二阶导数接近0 |
| 周期异常 | 不自然的周期性变化 | FFT功率谱分析 |
| 高频波动 | 快速频繁波动 | 符号变化比例高 |

## 4类违规模式

| 违规类型 | 特征描述 | 检测依据 |
|----------|----------|----------|
| 插瓶干扰 | 使用标准溶液模拟达标 | 指标恒定且接近标准限值 |
| 人工拟合 | 数据过度平滑 | 平滑度异常、R²过高 |
| 稀释排放 | 加清水稀释降低浓度 | 多指标同步下降且低位 |
| 恶意逃避 | 设备异常或停运 | 数据缺失率异常、夜间空白 |

## 算子选择策略

专利要求的自适应算子选择：

| 条件 | 选择算子 |
|------|----------|
| 样本量n<1000且自相关弱 | IQR、3σ |
| 1000≤n<10000且时序依赖强 | 孤立森林 |
| n≥10000且时序依赖强 | LSTM自编码器 |
| 检测到显著周期 | 季节性分解+异常检测 |
| 特征维度>50 | 多变量异常检测 |

## 配置参数说明

### 孤立森林
- `contamination=0.1`: 污染率（专利要求值）
- `n_estimators=100`: 树的数量
- 范围: [0.05, 0.20]

### 异常评分
- `anomaly_threshold=0.5`: 异常分数阈值（专利要求值）
- 分数范围: [0, 1]，值越大越异常

### 模式识别
- `similarity_threshold=0.7`: 模式相似度阈值（专利要求值）
- 相似度≥0.7判定匹配该类异常

### 置信度评估
- `anomaly_score_weight=0.6`: 异常分数权重（专利要求值）
- `pattern_similarity_weight=0.4`: 模式相似度权重（专利要求值）

## 参考文档

需要详细配置或规范时，查阅以下文档：

- `references/operators.md` - 算子库说明
- `references/violation_patterns.md` - 违规模式特征库
- 专利文档 - 异常检测子智能体规范

## 常见问题

**Q: 为什么选择多个算子？**
A: 不同算子对不同类型的异常敏感度不同。多算子融合可以提高检测准确率和鲁棒性。

**Q: 置信度低怎么办？**
A: 置信度低可能表示算子结果不一致或异常模式不明显。建议查看原始数据或调整参数重新检测。

**Q: 如何判定违规类型？**
A: 违规检测基于异常模式组合和工艺规则。单一异常可能是设备问题，多模式匹配且违背工艺规则则高度可疑。

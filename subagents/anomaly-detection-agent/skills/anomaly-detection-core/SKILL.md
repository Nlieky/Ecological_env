---
name: anomaly-detection-core
description: Environmental monitoring anomaly detection and violation pattern recognition. Use when detecting data anomalies, identifying abnormal patterns, detecting fraudulent behaviors, or extracting time-series features. Supports 5 anomaly types (constant, spike, trend, periodic, high-frequency fluctuation), 4 violation patterns (bottle interference, artificial fitting, dilution discharge, malicious evasion), statistical operators (3σ, IQR, Grubbs), ML operators (isolation forest, One-Class SVM), and time-series feature extraction. Required for environmental monitoring and wastewater treatment compliance scenarios.
---

# Anomaly Detection and Pattern Recognition

## Overview

Detects anomalies in monitoring data using statistical and machine learning methods, identifies violation patterns indicative of fraudulent discharge, and extracts time-series features for downstream analysis.

## Quick Start

```python
from scripts import detect_anomalies

result = detect_anomalies(
    data=monitoring_data,
    indicators=["pH", "COD", "NH3-N"],
    config={
        "operators": ["zscore", "iqr", "isolation_forest"],
        "pattern_threshold": 0.2,  # 降低阈值以提高模式识别覆盖率
        "contamination": 0.1
    }
)
# Returns: anomalies, patterns, violations, confidence, suspicion_level
```

## Core Modules

### operator_adapter.py
- `apply_operators(data, indicators, operator_list)`: Apply detection operators
- Operators: zscore, iqr, grubbs, moving_average, isolation_forest, one_class_svm

### anomaly_scorer.py
- `calculate_scores(data, operator_results)`: Aggregate anomaly scores (0-1 range)
- `anomaly_threshold=0.5`: Patent-required threshold

### pattern_recognizer.py
- `recognize_patterns(data, anomaly_scores, threshold=0.7)`: 5 pattern types
  - constant: Values unchanged over time
  - spike: Sudden large change between points
  - trend: Uniform rise/fall
  - periodic: Unnatural cyclical changes
  - high_frequency: Rapid fluctuations
- `similarity_threshold=0.7`: Patent-required pattern matching

### violation_detector.py
- `detect_violations(anomalies, data)`: 4 violation types
  - bottle_interference: Constant values near standard limits
  - artificial_fitting: Over-smoothed curves, high R²
  - dilution_discharge: Multi-indicator synchronized drop
  - malicious_evasion: Equipment anomalies, night-time gaps

### confidence_evaluator.py
- `evaluate(scores, patterns, operator_results)`: Confidence assessment
- Weights: `anomaly_score_weight=0.6`, `pattern_similarity_weight=0.4`

### Time-Series Features (Integrated)
- `extract_features(data, indicators, config)`: Feature extraction
  - Time-series features: mean, variance, skewness, kurtosis
  - Correlation analysis: Pearson/Spearman
  - Trend analysis: linear regression, moving average, CCF

## Configuration

### Isolation Forest
- `contamination=0.1`: Patent-required pollution rate
- `n_estimators=100`: Number of trees
- Range: [0.05, 0.20]

### Pattern Recognition
- `similarity_threshold=0.7`: Patent-required pattern similarity
- `anomaly_threshold=0.5`: Patent-required score threshold

### Confidence Evaluation
- `anomaly_score_weight=0.6`: Score contribution
- `pattern_similarity_weight=0.4`: Pattern contribution

## Operator Selection Strategy (Patent Requirements)

| Condition | Select Operator |
|-----------|----------------|
| n<1000, weak autocorrelation | IQR, 3σ |
| 1000≤n<10000, strong time dependence | Isolation Forest |
| n≥10000, strong time dependence | LSTM Autoencoder |
| Significant periodicity | Seasonal decomposition + anomaly |
| Features >50 dimensions | Multivariate anomaly detection |

## 5 Anomaly Types

| Type | Description | Detection |
|------|-------------|-----------|
| Constant | Values unchanged over time | Low variance |
| Spike | Large change between adjacent points | Difference exceeds threshold |
| Trend | Uniform rise/fall | Second derivative ~0 |
| Periodic | Unnatural cyclical changes | FFT power spectrum |
| High-frequency | Rapid frequent fluctuations | High sign-change rate |

## 4 Violation Patterns

| Type | Description | Detection Basis |
|------|-------------|-----------------|
| Bottle Interference | Standard solution simulation | Constant values near standard limits |
| Artificial Fitting | Data over-smoothed | Abnormal smoothness, high R² |
| Dilution Discharge | Water dilution | Multi-indicator synchronized drop, low levels |
| Malicious Evasion | Equipment anomaly/shutdown | Abnormal missing rate, night gaps |

## Suspicion Level Rules

| Condition | Level |
|-----------|-------|
| ≥2 patterns AND process violation | High (critical) |
| 1 pattern AND process violation | Medium |
| Patterns only, no process violation | Low |

## References

For detailed configuration: `references/operators.md`, `shared/knowledge/violation_patterns/violation_patterns.md`, patent documentation

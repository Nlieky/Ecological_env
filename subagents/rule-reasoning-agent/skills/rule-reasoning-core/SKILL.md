---
name: rule-reasoning-core
description: Regulatory compliance and process reasoning for environmental monitoring. Use when validating detected anomalies against regulations, process mechanisms, or expert experience. Supports regulation matching (Water Pollution Prevention Law, GB 18918-2002, HJ 915-2017), process mechanism validation (pH-COD synergy, NH3-N/TN conversion, mass balance), expert reasoning (similarity threshold 0.8), and violation conclusion generation (suspicion level, evidence points). Required after anomaly detection to determine violation nature and risk level.
---

# Rule Reasoning and Violation Determination

## Overview

Validates detected anomalies against regulatory standards, process mechanisms, and expert experience to determine violation nature and generate compliant conclusions.

## Quick Start

```python
from scripts import run_rule_reasoning

task = {
    "task_id": "violation_001",
    "data": feature_data,
    "anomalies": anomaly_list,
    "correlation_results": correlation_data,
    "trend_results": trend_data,
    "config": {}
}

result = run_rule_reasoning(task)
# Returns: regulation_check, process_validation, expert_reasoning, violation_conclusion
```

## Core Modules

### regulation_matcher.py
- `match(anomalies, data)`: Check against regulatory standards
- Supported regulations:
  - Water Pollution Prevention Law
  - GB 18918-2002 (Discharge Standard - Class 1A)
  - HJ 915-2017 (Surface Water Monitoring)

### process_validator.py
- `validate(anomalies, correlation_results, trend_results, data)`: Process mechanism check
- Rules:
  - pH-COD synergy: Acidic conditions → higher COD degradation
  - NH3-N/TN conversion: NH3-N is TN component
  - Mass balance: Conservation of matter

### expert_reasoner.py
- `reason(anomalies, regulation_result, process_result)`: Expert experience matching
- `similarity_threshold=0.8`: Patent-required case similarity

### violation_generator.py
- `generate(...)`: Generate violation conclusion
  - Suspicion level (high/medium/low)
  - Evidence points
  - Legal references
  - Penalty recommendations

## Regulatory Standards (Class 1A)

| Indicator | Limit | Unit |
|-----------|-------|------|
| COD | 50 | mg/L |
| TN | 15 | mg/L |
| NH3-N | 5 | mg/L |
| TP | 0.5 | mg/L |
| pH | 6-9 | - |

## Process Mechanism Rules

| Rule | Validation | Violation Indicator |
|------|------------|---------------------|
| pH-COD synergy | Acidic → higher COD efficiency | pH stable, COD fluctuates |
| NH3-N/TN conversion | NH3-N part of TN | Correlation <0.3 |
| DO-Pollutant degradation | Aerobic → organic degradation | DO normal, pollutants rise |
| Mass balance | Conservation of matter | Abnormal removal rate |

## Violation Patterns

- **Bottle Interference**: Constant values near standard limits
- **Dilution Discharge**: Multi-indicator synchronized drop at low levels
- **Artificial Fitting**: Over-smoothed data, high R²
- **Malicious Evasion**: Abnormal missing rate, night-time gaps

## Suspicion Level (Patent Requirements)

| Condition | Level |
|-----------|-------|
| ≥2 pattern matches AND process violation | High (critical) |
| 1 pattern match AND process violation | Medium |
| Pattern matches only, no process violation | Low |

## Configuration

### Process Validation
- `nh3_tn_correlation_min=0.3`: Min NH3-N/TN correlation
- `nh3_tn_ratio_min=0.2`: Min effluent NH3-N/TN ratio
- `nh3_tn_ratio_max=0.6`: Max effluent NH3-N/TN ratio

### Expert Reasoning
- `similarity_threshold=0.8`: Patent-required case similarity

### Violation Generation
- `high_risk_condition`: "patterns>=2 AND process_violation"
- `medium_risk_condition`: "patterns==1 AND process_violation"
- `low_risk_condition`: "patterns>0 AND NOT process_violation"

## References

For detailed configuration: `references/regulations/`, `references/process_knowledge/`, `references/expert_experience/`, patent documentation

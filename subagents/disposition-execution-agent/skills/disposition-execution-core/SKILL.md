---
name: disposition-execution-core
description: Alert classification, consensus fusion, and execution coordination for environmental monitoring. Use when classifying alerts, fusing multi-source results, generating work orders, or coordinating enforcement actions. Supports three-level alert classification (general/moderate/serious), consensus engine with dynamic weight adaptation, standardized work order generation with evidence and legal references, and multi-channel execution (RegulatoryPlatformPush, FeishuPush, LocalArchive). Required for violation response coordination and enforcement workflow.
---

# Disposition, Alert, and Execution

## Overview

Provides alert classification, consensus fusion of detection results, work order generation, and multi-channel execution coordination for environmental monitoring violations.

## Quick Start

```python
from scripts.alert_classifier import AlertClassifier
from scripts.consensus_engine import ConsensusEngine
from scripts.work_order_generator import WorkOrderGenerator
from scripts.action_executor import ActionExecutor

# Alert classification
classifier = AlertClassifier()
alert = classifier.classify_alert(anomaly_result, violation_result)

# Consensus fusion
engine = ConsensusEngine()
fused = engine.fuse_results(
    anomaly_results=[...],
    violation_results=[...],
    scene="default"
)

# Work order generation
generator = WorkOrderGenerator()
work_order = generator.generate_work_order(fused, raw_data)

# Multi-channel execution
executor = ActionExecutor()
executor.execute(work_order, channels=["FeishuPush", "LocalArchive"])
```

## Core Modules

### alert_classifier.py
- `classify_alert(anomaly_result, violation_result)`: Three-level classification
  - General (low risk)
  - Moderate (medium risk)
  - Serious (high/critical risk)

### consensus_engine.py
- `fuse_results(anomaly_results, violation_results, scene)`: Multi-source fusion
  - Scenes: default, critical, normal
  - Dynamic weight adaptation
  - Fusion metadata tracking
- `adapt_weights(scene, confidence)`: Adjust weights based on context
- Configuration: `shared/configs/consensus_config.yaml`

### work_order_generator.py
- `generate_work_order(fused_result, raw_data)`: Standardized work order
  - Data traceability
  - Inspection points
  - Legal references
  - Historical comparison

### action_executor.py
- `execute(work_order, channels)`: Multi-channel parallel execution
  - RegulatoryPlatformPush: Regulatory platform API
  - FeishuPush: Feishu notification
  - LocalArchive: Local file storage
- Abstract interface: PushChannel base class

### report_generator.py
- `generate_alert_report(fused_result)`: Alert report generation
- `generate_summary_report(results)`: Summary report
- `generate_trend_report(trend_data)`: Trend analysis report
- Formats: JSON, Markdown

## Consensus Engine Configuration

### Default Weights
```yaml
anomaly_sources:
  operator_result: 0.6
  pattern_recognizer: 0.4
violation_sources:
  regulation_matcher: 0.4
  process_validator: 0.3
  expert_reasoner: 0.3
```

### Scene-Based Strategies
- **default**: Balanced weights
- **critical**: Higher violation weight (0.6 anomaly, 0.4 violation)
- **normal**: Higher anomaly weight (0.7 anomaly, 0.3 violation)

## Alert Classification Rules

| Inputs | Alert Level |
|--------|-------------|
| High suspicion + multiple violations | Serious |
| Medium suspicion + single violation | Moderate |
| Low suspicion + no violations | General |

## Work Order Structure

```python
{
    "order_id": "...",
    "alert_level": "serious",
    "violation_type": "dilution_discharge",
    "evidence": {...},
    "inspection_points": [...],
    "legal_references": [...],
    "timestamp": "..."
}
```

## Execution Channels

### RegulatoryPlatformPush
- API endpoint integration
- Standard format submission
- Response tracking

### FeishuPush
- Webhook notification
- Rich text formatting
- Alert escalation

### LocalArchive
- JSON/Markdown storage
- Timestamped records
- Searchable archive

## LLM Decision Points

### Fusion Strategy
- High confidence → Use default weights
- Critical violations → Increase violation weight
- Normal operations → Increase anomaly weight

### Alert Classification
- Consider both anomaly severity and violation count
- Evaluate detection confidence
- Assess potential environmental impact

### Execution Selection
- Serious alerts → All channels
- Moderate alerts → FeishuPush + LocalArchive
- General alerts → LocalArchive only

## Output Format

```python
{
    "alert": {...},
    "fused_result": {
        "conclusion": "...",
        "confidence": 0.85,
        "weights_used": {...},
        "metadata": {...}
    },
    "work_order": {...},
    "execution_status": {...}
}
```

## References

For detailed configuration: `shared/configs/consensus_config.yaml`, patent documentation

---
name: anomaly-detection-core
description: 异常检测技能。**触发条件**：用户提到"异常"、"不正常"、"突变"、"趋势"、"检测异常"时调用。
---

# 异常检测技能

## 核心规则

**只做一件事：调用脚本，传递结果。不要解析，不要生成报告。**

## 执行流程

1. **调用脚本**
   ```bash
   python skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py
   ```

2. **确认执行完成**
   响应："✅ 脚本执行完成"

## 脚本输出

脚本自动保存结果到 `anomaly_result.json`，包含：
- anomalies: 异常点数组
- summary: 统计摘要（总数、类型分布）
- metadata: 元数据

**你不需要处理输出，系统会自动读取。**

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要做违规判定（由rule-reasoning负责）

---

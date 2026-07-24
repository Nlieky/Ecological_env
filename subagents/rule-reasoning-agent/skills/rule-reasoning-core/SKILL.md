---
name: rule-reasoning-core
description: 规则推理和违规判定。**触发条件**：当用户查询提到"违规"、"超标"、"违反标准"、"是否达标"、"插瓶"、"稀释"、"排放异常"时调用。基于异常检测结果进行法规匹配、工艺校验和专家推理，判定违规类型和嫌疑等级。需要异常检测结果作为输入。
---

# 规则推理和违规判定技能

## 核心规则

**只做一件事：调用脚本，传递结果。不要解析，不要生成报告。**

## ⚠️ 执行纪律（违反必失败）

**第一步就直接 `python` 运行下面的脚本。绝对禁止 `ls` / `head` / `grep` / `cat` 去读脚本源码、禁止探索目录。**
输入会自动从 SESSION_DIR 读取，不需要你研究脚本内部怎么读输入。之前有子智能体因为连着读源码、迭代用完没轮到运行而失败——别重蹈覆辙。

## 执行流程

1. **调用脚本**
   ```bash
   python "$HERMES_HOME/skills/rule-reasoning-core/scripts/run_rule_reasoning.py"
   ```

2. **确认执行完成**
   响应："✅ 脚本执行完成"

## 脚本输出

脚本自动保存结果到 `rule_reasoning_result.json`，包含：
- `has_violation` (bool): 是否存在违规
- `suspicion_level` (str): 嫌疑等级（low/medium/high/critical）
- `suspicion_level_cn` (str): 嫌疑等级中文
- `confidence` (float): 置信度
- `violation_types` (list): 违规类型列表
- `violation_type_names` (list): 违规类型中文名称
- `evidence_points` (list): 证据点
- `regulation_matches`: 法规匹配结果
- `process_validation`: 工艺机理校验结果
- `expert_reasoning`: 专家推理结果
- `conclusion` (str): 综合结论

**你不需要处理输出，系统会自动读取。**

## 输入要求

此技能需要以下输入（按优先级）：
1. **异常检测结果** - 必需，来自 anomaly-detection 子智能体
2. **原始数据** - 可选，用于工艺机理校验，来自 data-perception 子智能体

脚本会自动查找以下位置的输入文件：
- `SESSION_DIR/anomaly_result.json`
- `subagents/anomaly-detection-agent/anomaly_result.json`
- `SESSION_DIR/data_result.json`
- `subagents/multi-dimensional-data-perception-agent/data_result.json`

## 处理流程

```
异常检测结果 → 法规规则匹配 → 工艺机理校验 → 专家经验推理 → 违规判定结论
```

### 法规规则匹配
- 城镇污水处理厂污染物排放标准 (GB 18918-2002)
- 水污染源在线监测技术规范 (HJ 355-2019)
- 水污染防治法

### 工艺机理校验
- 生化反应联动规则
- 物料平衡规则
- 相关性规则
- 氨氮-总氮转化规则

### 专家经验推理
- 造假模式识别（插瓶干扰、稀释排放、暗管偷排等）
- 嫌疑等级判定
- 历史案例匹配（相似度≥0.8）

## 违规类型

| 类型 | 英文标识 | 特征 |
|------|---------|------|
| 插瓶干扰 | bottle_interference | 指标长时间恒定，接近限值 |
| 稀释排放 | data_dilution | 多指标同步下降，水量异常增加 |
| 暗管偷排 | secret_pipe | 进水正常，出水异常偏低 |
| 虚假停产 | false_shutdown | 上报停产但仍有数据 |
| 公式篡改 | formula_tampering | 数据呈人工拟合特征 |

## 嫌疑等级

| 等级 | 英文 | 中文 | 含义 |
|------|------|------|------|
| 低 | low | 低 | 存在轻微异常，需关注 |
| 中 | medium | 中 | 存在违规嫌疑，建议核查 |
| 高 | high | 高 | 高度疑似违规，强烈建议现场核查 |
| 严重 | critical | 严重 | 严重违规，应立即采取措施 |

## 命令行参数

```bash
# 使用默认路径
python "$HERMES_HOME/skills/rule-reasoning-core/scripts/run_rule_reasoning.py"

# 指定异常检测结果路径
python "$HERMES_HOME/skills/rule-reasoning-core/scripts/run_rule_reasoning.py" --anomaly-result <path>

# 指定会话目录
python "$HERMES_HOME/skills/rule-reasoning-core/scripts/run_rule_reasoning.py" --session-dir <path>
```

## 输出路径

```
SESSION_DIR/rule_reasoning_result.json  # 如果设置了 SESSION_DIR
subagents/rule-reasoning-agent/rule_reasoning_result.json  # 默认路径
```

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要做异常检测（由anomaly-detection负责）
- ❌ 不要生成预警（由disposition-execution负责）

---

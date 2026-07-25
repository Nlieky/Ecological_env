---
name: anomaly-detection-core
description: 异常检测和违规模式识别。**触发条件**：当用户提到"异常"、"不正常"、"突变"、"趋势"、"检测异常"、"异常检测"、"数据异常"、"波动"、"是否正常"时调用。使用多种算子检测时序数据中的异常模式和违规特征。
---

# 异常检测技能

## 核心规则

**只做一件事：调用脚本，传递结果。不要解析，不要生成报告。**

## ⚠️ 执行纪律（严格白名单，违反必失败）

**你只能执行下面"执行流程"里那一条 `python` 命令，敲完就停。严禁任何其他终端操作：**
- ❌ 禁止 `cat >` / `>>` / `echo >` 写入、修改、删除任何文件（结果只能由脚本产出，你一写就污染）
- ❌ 禁止 `python -c` / 内联代码 / 自己写脚本
- ❌ 禁止 `ls` / `find` / `head` / `tail` / `grep` / `cat` 读文件或探索目录
- ❌ 禁止 `cd` / `pwd` / `echo` 等闲逛
- ✅ **唯一允许**：直接 `python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py" [--hours N]`

之前有子智能体因 `cat >` 编造结果、`python -c`、`find` 乱翻，烧光迭代还污染数据——别重蹈覆辙。

## 执行流程

1. **调用脚本**
   ```bash
   python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py"
   ```

2. **确认执行完成**
   响应："✅ 脚本执行完成"

## 脚本输出

脚本自动保存结果到 `anomaly_result.json`，包含：
- `anomalies` (list): 异常点列表，每个异常点包含：
  - `data_type` (str): 数据类型（influent/effluent）
  - `indicator` (str): 指标名称
  - `timestamp` (str): 时间戳
  - `type` (str): 异常类型（boundary/constant/spike/trend/point）
  - `score` (float): 异常分数
  - `value` (float): 异常值
  - `votes` (int): 投票数（几个算子认为是异常）
  - `expected_range` (list): 期望范围 [Q1, Q3]
- `summary` (dict): 统计摘要
  - `total_anomalies` (int): 异常总数
  - `by_data_type` (dict): 按数据类型统计
  - `by_indicator` (dict): 按指标统计
  - `by_type` (dict): 按异常类型统计

**你不需要处理输出，系统会自动读取。**

## 异常类型

| 类型 | 英文 | 描述 | 检测方法 |
|------|------|------|---------|
| 边界异常 | boundary | 时间序列首尾的异常点 | 位置判定 |
| 恒定值异常 | constant | 数值长时间保持不变 | 标准差检测 |
| 突变异常 | spike | 数值突然升高或降低 | 局部变化率 |
| 趋势异常 | trend | 数值呈现持续上升或下降趋势 | 线性拟合 |
| 点异常 | point | 单个数据点偏离正常范围 | 多算子投票 |

## 检测算子

脚本使用多种算子进行异常检测：

1. **Z-score 算子**: 基于标准差的异常检测
2. **IQR 算子**: 基于四分位距的异常检测
3. **孤立森林算子**: 基于机器学习的异常检测

### 综合评分
- 多算子投票机制（至少2个算子认为是异常）
- 综合异常分数（各算子分数的平均值）

## 输入要求

脚本会自动从项目数据目录加载最近24小时的监测数据：
- `shared/data/pollution_water_in.csv` - 进水数据
- `shared/data/pollution_water_out.csv` - 出水数据

## 检测指标

默认检测以下指标：
- pH值
- 化学需氧量浓度（COD）
- 总氮浓度（TN）
- 氨氮浓度（NH3-N）
- 总磷浓度（TP）
- 悬浮物浓度（SS）

## 命令行参数

```bash
# 使用默认参数（最近24小时）
python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py"

# 指定时间范围（小时）
python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py" --hours 48

# 指定数据源
python "$HERMES_HOME/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py" --data-dir <path>
```

## 输出路径

```
SESSION_DIR/anomaly_result.json  # 如果设置了 SESSION_DIR
subagents/anomaly-detection-agent/anomaly_result.json  # 默认路径
```

## 违规模式识别

异常检测是违规判定的基础，检测结果会被传递给规则推理子智能体进行进一步分析：

1. **插瓶干扰**: 检测到恒定值异常 + 接近标准限值
2. **稀释排放**: 检测到多指标同步下降
3. **人工拟合**: 检测到数据过度平滑
4. **恶意逃避**: 检测到高频缺失或异常模式

## 典型使用场景

1. **日常监控**: "检查最近24小时数据是否正常"
2. **异常排查**: "检测最近48小时有哪些异常"
3. **指标分析**: "分析COD指标是否存在异常"
4. **趋势识别**: "识别最近一周的趋势异常"

## 数据质量控制

脚本会自动处理以下数据质量问题：
- 缺失值处理
- 异常值过滤
- 时间戳解析
- 数据类型转换

## 性能考虑

- 推荐检测范围：24-48小时
- 最大检测范围：7天
- 数据点数量：建议 < 1000条

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要做违规判定（由rule-reasoning负责）
- ❌ 不要生成预警（由disposition-execution负责）

---

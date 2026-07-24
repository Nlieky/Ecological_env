# 研判预警与处置执行子智能体 - 专业记忆

## 预警等级（3 级，对齐真实脚本）

| 级别 | 中文 | 置信度 | 处置行动 |
|------|------|--------|---------|
| `general` | 一般（黄色） | ≤ 0.6 | 持续监控 |
| `moderate` | 较重（橙色） | 0.6 – 0.8 | 现场核查 |
| `serious` | 严重（红色） | > 0.8 | 立即调查取证 |

## 融合共识

```
融合置信度 = anomaly_confidence × w_a + violation_confidence × w_v
默认 w_a = 0.4, w_v = 0.6；ConsensusEngine 按证据强度自适应调整
```

## 工单模板

- **编号**：`WO-YYYYMMDD-序号-随机后缀`（如 `WO-20260715-001-a3b4c5d6`）
- **报告编号**：`ALERT-工单ID-时间戳`
- 含：数据溯源（时间范围、受影响指标）、现场核查要点、法规条款引用、处置建议
- 支持导出 JSON / Markdown

## 标准化处置建议（按违规类型）

### 插瓶干扰（bottle_interference）
1. 检查采样探头位置（是否在采样管内）
2. 核查采样管路完整性（是否有旁路）
3. 检查现场是否有标准溶液
4. 核查设备运行记录、现场拍照取证

### 稀释排放（data_dilution）
1. 检查清水接入管路
2. 核对用水量与排水量平衡
3. 检查排放口周边环境、药剂投加记录
4. 排查清水稀释装置

### 公式篡改 / 人工拟合（formula_tampering）
1. 检查设备参数设置（是否过度平滑）
2. 核对历史数据记录（修改痕迹）
3. 检查数据传输日志、原始数据记录
4. 技术鉴定数据分析

### 暗管偷排（secret_pipe）
1. 排查周边隐蔽管道
2. 检查流量计准确性
3. 核对用水量与排水量

## 处置流程

```
结果融合 → 预警研判 → 工单生成 → 报告输出
```

> 实际推送（短信 / 邮件 / APP）由外围系统消费本子智能体产出的工单与报告，不在 `run_disposition.py` 范围内。

## 输出契约

`disposition_result.json`：`alert`（level/level_cn/confidence/action/action_cn）+ `violation_type` + `work_order`（id/alert_level/inspection_points/legal_references/recommended_actions）+ `report` + `fusion`（anomaly_confidence/violation_confidence/fused_confidence/adaptive_weights）。

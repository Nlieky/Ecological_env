# 研判预警与处置执行子智能体 - 专业记忆

## 嫌疑等级 → 处置行动（消费规则推理结论）

| 嫌疑等级 | 处置行动 | 工单 |
|---|---|---|
| high | 立即调查取证 | 出工单（核查要点 + 法规 + 取证建议） |
| medium | 现场核查 | 出工单（核查要点） |
| low | 持续监控 | 出监控建议 |
| none | 无违规 | 正常报告（不出工单） |

> **废弃**：旧预警 3 级（general/moderate/serious）+ 融合共识（ConsensusEngine）。规则推理已综合 anomaly + violation 成嫌疑等级，处置执行只消费。

## 工单内容

- **编号**：`WO-YYYYMMDD-序号`
- **核查要点**：来自异常时间段 + 指标
- **法规引用**：来自规则推理的 `evidence_points`
- **处置建议**：按嫌疑等级映射

## 标准化处置建议（按违规类型）

### 插瓶干扰
1. 检查采样探头位置（是否在采样管内）
2. 核查采样管路完整性
3. 检查现场是否有标准溶液
4. 核查设备运行记录、现场拍照取证

### 稀释排放
1. 检查清水接入管路
2. 核对用水量与排水量平衡
3. 检查排放口周边环境、药剂投加记录

### 人工拟合
1. 检查设备参数设置（是否过度平滑）
2. 核对历史数据修改痕迹
3. 检查数据传输日志

## 输出契约

`disposition_result.json`：`suspicion_level` / `suspicion_level_cn` / `violation_types` / `action` / `confidence` / `work_order`（id/inspection_points/legal_references/recommended_actions） / `report` / `evidence_points`

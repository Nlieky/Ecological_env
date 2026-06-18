# 子智能体通信协议

## 输入格式

所有子智能体接收统一的输入格式：

```json
{
  "task_id": "string",
  "task_type": "string",
  "params": {},
  "timestamp": "ISO8601"
}
```

## 输出格式

所有子智能体返回统一的输出格式：

```json
{
  "task_id": "string",
  "status": "success|failure",
  "result": {},
  "errors": [],
  "timestamp": "ISO8601"
}
```

## 数据接口

- **多维数据感知子智能体**：返回标准化时序数据
- **异常检测子智能体**：返回异常点位置和置信度
- **规则推理子智能体**：返回违规判定和法规条款
- **研判预警子智能体**：返回预警级别和处置工单

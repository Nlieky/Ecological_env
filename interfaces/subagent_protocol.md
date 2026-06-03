# 子智能体通信协议

## 协议概述

本协议定义了废水监测系统中各子智能体之间的标准化通信规范。
**版本**: 2.0 - 基于专利四层架构

## 1. 子智能体标准接口

### 1.1 基础接口

所有子智能体必须实现以下基础接口：

```python
class BaseSubagent:
    """子智能体基类"""

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准分析接口

        Args:
            input_data: 输入数据字典

        Returns:
            标准格式的分析结果字典
        """
        raise NotImplementedError

    def get_status(self) -> Dict[str, Any]:
        """
        获取子智能体状态

        Returns:
            状态信息字典
        """
        raise NotImplementedError
```

### 1.2 标准输入格式

```python
{
    "task_id": str,           # 任务ID
    "timestamp": str,         # 时间戳
    "data": Dict[str, Any],   # 业务数据
    "config": Dict[str, Any]  # 配置参数（可选）
}
```

### 1.3 标准输出格式

```python
{
    "task_id": str,           # 任务ID
    "agent": str,             # 子智能体标识
    "timestamp": str,         # 时间戳
    "status": str,            # 状态: success/error
    "result": Dict[str, Any], # 分析结果
    "metadata": Dict[str, Any] # 元数据
}
```

## 2. 四类子智能体专用接口

### 2.1 数据治理子智能体 (data-governance-agent)

```python
class DataGovernanceSubagent(BaseSubagent):
    """数据治理子智能体"""

    def acquire_data(self, source: str, time_range: TimeRange) -> Dict:
        """多源数据获取"""

    def align_time_series(self, data_streams: List[Dict]) -> Dict:
        """时序对齐与规整"""

    def clean_and_quality_control(self, data: Dict) -> Dict:
        """数据清洗与质控"""

    def normalize_and_standardize(self, data: Dict) -> Dict:
        """标准化与归一化"""
```

### 2.2 特征与关系分析子智能体 (feature-analysis-agent)

```python
class FeatureAnalysisSubagent(BaseSubagent):
    """特征与关系分析子智能体"""

    def extract_features(self, data: Dict) -> Dict:
        """时序特征提取"""

    def analyze_correlation(self, data: Dict) -> Dict:
        """指标相关性分析"""

    def analyze_trend(self, data: Dict) -> Dict:
        """趋势与滞后分析"""

    def fuse_features(self, features: List[Dict]) -> Dict:
        """特征融合与优化"""
```

### 2.3 异常检测子智能体 (anomaly-detection-agent)

```python
class AnomalyDetectionSubagent(BaseSubagent):
    """异常检测子智能体"""

    def call_operator(self, data: Dict, operator: str) -> Dict:
        """算子调用与适配"""

    def calculate_anomaly_score(self, data: Dict) -> Dict:
        """异常评分计算"""

    def recognize_pattern(self, data: Dict) -> Dict:
        """异常模式识别"""

    def assess_confidence(self, result: Dict) -> Dict:
        """可信度评估"""
```

### 2.4 规则推理子智能体 (rule-reasoning-agent)

```python
class RuleReasoningSubagent(BaseSubagent):
    """规则推理子智能体"""

    def match_regulation(self, anomaly: Dict) -> Dict:
        """法规规则匹配"""

    def verify_mechanism(self, anomaly: Dict) -> Dict:
        """工艺机理校验"""

    def reason_by_experience(self, anomaly: Dict) -> Dict:
        """专家经验推理"""

    def generate_conclusion(self, results: List[Dict]) -> Dict:
        """违规结论生成"""
```

## 3. 层间通信协议

### 3.1 主智能体 → 任务编排层

```python
{
    "message_type": "schedule_request",
    "task_id": str,
    "atomic_tasks": List[Dict],  # 原子任务列表
    "reuse_decision": str,       # 复用决策: reuse/recompute
    "constraints": Dict[str, Any]  # 执行约束
}
```

### 3.2 任务编排层 → 子智能体层

```python
{
    "message_type": "execute_request",
    "task_id": str,
    "agent_type": str,          # 子智能体类型
    "operation": str,           # 操作类型
    "input_data": Dict[str, Any],
    "timeout": int,             # 超时时间
    "constraints": Dict[str, Any]  # 执行约束
}
```

### 3.3 子智能体层 → 任务编排层

```python
{
    "message_type": "execute_response",
    "task_id": str,
    "agent_type": str,
    "status": str,              # success/error/timeout
    "result": Dict[str, Any],
    "execution_time": float
}
```

## 4. 错误处理协议

### 4.1 错误码定义

| 错误码 | 描述 | 处理方式 |
|--------|------|----------|
| E0001 | 输入数据格式错误 | 返回错误，不重试 |
| E0002 | 数据获取失败 | 重试3次 |
| E0003 | 算子调用失败 | 降级执行 |
| E0004 | 超时 | 返回部分结果 |
| E0005 | 知识库查询失败 | 使用默认规则 |

### 4.2 错误响应格式

```python
{
    "task_id": str,
    "status": "error",
    "error_code": str,
    "error_message": str,
    "retry_able": bool,
    "partial_result": Dict[str, Any]  # 可选
}
```

## 5. 数据流转规范

### 5.1 数据流标准

```
原始数据 → 数据治理子智能体 → 标准化数据
    ↓
特征与关系分析子智能体 → 特征数据集
    ↓
异常检测子智能体 → 异常检测结果
    ↓
规则推理子智能体 → 违规判定结论
```

### 5.2 数据格式转换

各层之间需要统一数据格式，使用JSON Schema定义的标准化格式。

## 6. 子智能体注册表

位置：`shared/configs/subagent_registry.json`

```json
{
  "agents": [
    {
      "id": "data-governance-agent",
      "name": "数据治理子智能体",
      "version": "2.0.0",
      "enabled": true,
      "description": "多源数据获取、时序对齐、数据清洗、标准化处理"
    },
    {
      "id": "feature-analysis-agent",
      "name": "特征与关系分析子智能体",
      "version": "2.0.0",
      "enabled": true,
      "description": "时序特征提取、指标相关性分析、趋势分析、特征融合"
    },
    {
      "id": "anomaly-detection-agent",
      "name": "异常检测子智能体",
      "version": "2.0.0",
      "enabled": true,
      "description": "算子调用、异常评分、模式识别、可信度评估"
    },
    {
      "id": "rule-reasoning-agent",
      "name": "规则推理子智能体",
      "version": "2.0.0",
      "enabled": true,
      "description": "法规规则匹配、工艺机理校验、专家经验推理、违规结论生成"
    }
  ],
  "version": "2.0.0",
  "last_updated": "2026-05-07T00:00:00Z"
}
```

## 7. 健康检查

### 健康检查端点
- **路径**：`/health`
- **方法**：GET
- **返回**：

```json
{
  "agent_id": "data-governance-agent",
  "status": "healthy",
  "uptime": "48h",
  "last_check": "2026-05-07T00:00:00Z",
  "metrics": {
    "total_requests": 1234,
    "success_rate": 0.99,
    "avg_response_time": "150ms"
  }
}
```

### 健康状态
- **healthy** - 正常运行
- **degraded** - 性能下降但可用
- **unhealthy** - 不可用

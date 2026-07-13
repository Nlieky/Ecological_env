---
name: 2026-07-07-llm-driven-subagent-fixes
description: Fixed critical bugs in anomaly detection script - path resolution and numeric column conversion
metadata:
  type: project
---

# 2026-07-07 LLM驱动子智能体修复

## 问题发现

异常检测子智能体测试返回0异常，但直接运行脚本时检测到14个异常。

## 根本原因

### 1. 路径解析错误
**位置**: `run_anomaly_detection_simple.py` line 31
```python
base_dir = Path(__file__).parent.parent.parent.parent  # 错误：指向 subagents/anomaly-detection-agent/
```
**问题**: 向上查找4层到达 `subagents/anomaly-detection-agent/` 而不是项目根目录
**修复**: 添加多层路径查找逻辑，优先查找包含 `data/pollution_water_in.csv` 的目录

### 2. 时间列名称获取错误
**位置**: `run_anomaly_detection_simple.py` line 220
```python
time_col = data.get(f"time_col_{data_type[-2:]}", "监测时间")  # data_type[-2:] = "nt"
```
**问题**: "influent"[-2:] = "nt"，应该是 "in"；"effluent"[-2:] = "nt"，应该是 "out"
**修复**: 改为条件判断
```python
if data_type == "influent":
    time_col = data.get("time_col_in", "监测时间")
else:
    time_col = data.get("time_col_out", "监测时间")
```

### 3. 数值列类型转换缺失
**问题**: CSV包含"/"值（如流量列），pandas读取时将整个列推断为object类型
**修复**: 读取CSV后显式转换非时间列为numeric类型
```python
for col in df_in.columns:
    if col != time_col_in:
        df_in[col] = pd.to_numeric(df_in[col], errors='coerce')
```

### 4. 测试脚本结果解析错误
**位置**: `scripts/test_end_to_end.py` line 188
**问题**: 查找 `anomalies` 在错误的嵌套层级
**修复**: 修改为 `result.result.summary.total_anomalies`

## 验证结果

直接运行脚本：
- 14个异常（2 boundary, 2 spike, 10 trend）
- 执行时间：~4秒

端到端测试：
- 数据感知：288条进水 + 288条出水记录
- 异常检测：14个异常
- 状态：✅ 通过

## 相关文件

- `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py`
- `scripts/test_end_to_end.py`

## 下一步

1. 同步修复到其他子智能体的类似脚本
2. 添加单元测试验证路径解析和数值转换
3. 优化LLM提示词减少执行时间（目前仍在30秒左右）

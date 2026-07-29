# 2026-07-06 会话错误分析 - 磁盘空间耗尽与上下文溢出

## 事件时间线

### 10:41:01 - 首次磁盘空间错误
```
[Errno 28] No space left on device
```
**子智能体**: `multi-dimensional-data-perception`
**任务**: 清理旧会话并检查磁盘空间
**结果**: 失败

### 10:36:10 - 异常检测子智能体失败
```
[Errno 28] No space left on device
```
**子智能体**: `anomaly-detection`
**结果**: 失败

### 10:41:27 - 尝试清理会话
**任务**: `rm -rf E:/project/Ecological_env/workspace/state/session_20260706_10*`
**结果**: 因磁盘空间不足，清理命令本身失败

### 10:41:44 - API 认证失败
```
Error code: 401 - {'error': 'Unauthorized'}
```
**原因**: 子智能体在传递大量上下文后，API 调用失败

### 10:42:06 及之后 - 响应截断
```
[Truncated: tool response was 196,748 chars. Full output could not be saved to sandbox.]
[Truncated: tool response was 649,139 chars. Full output could not be saved to sandbox.]
[Truncated: tool response was 2,313,954 chars. Full output could not be saved to sandbox.]
[Truncated: tool response was 8,682,543 chars. Full output could not be saved to sandbox.]
[Truncated: tool response was 33,583,854 chars. Full output could not be saved to sandbox.]
[Truncated: tool response was 132,012,398 chars. Full output could not be saved to sandbox.]
```
**原因**: 上下文累积导致响应呈指数级增长

### 10:43:40 至 10:45:51 - 连续失败
- `read_subagent_result()` 连续 5 次失败
- 触发 Hermes 循环警告：`same_tool_failure_warning; count=5`

## 根本原因分析

### 1. 磁盘空间管理不善
- 旧会话目录未及时清理
- `workspace/state/session_*` 累积占用大量空间
- 清理命令本身因空间不足而失败

### 2. 上下文传递模式问题
**错误模式**:
```python
# 每次调用都传递完整的 previous_results
result1 = call_subagent("data-perception", task1)
result2 = call_subagent("anomaly-detection", task2, context={"previous_results": result1})
result3 = call_subagent("rule-reasoning", task3, context={"previous_results": result2})
# ↑ 上下文呈指数级增长
```

**正确模式**:
```python
# 创建新会话，仅传递文件引用
session = create_session()
result1 = call_subagent("data-perception", task1, session_dir=session)
# 读取结果文件，只传递必要信息
result2 = call_subagent("anomaly-detection", task2, session_dir=session, 
                        context={"data_file": "data_result.json"})
```

### 3. 错误恢复策略缺失
- 首次磁盘错误后未立即清理
- 首次 API 认证失败后未检查凭证
- 首次响应截断后未切换策略
- `read_subagent_result()` 连续失败 5 次才停止

## 恢复措施

### 立即措施（已执行）
1. 清理旧会话目录：`rm -rf E:/project/Ecological_env/workspace/state/session_*`
2. 创建新会话：`create_orchestrator_session()`
3. 切换到直接 Python 分析（绕过子智能体系统）

### 长期预防措施
1. **定期清理**: 每天运行 `cleanup_sessions(days=3)`
2. **上下文限制**: 传递上下文时只包含必要字段
3. **错误阈值**: 同一错误出现 2 次后立即切换策略
4. **监控响应大小**: 出现截断警告时立即停止

## 关键教训

### 1. 磁盘空间是硬约束
- 必须在任务开始前检查可用空间
- 清理操作本身需要足够空间
- 预防优于恢复

### 2. 上下文累积是隐形杀手
- 每次子智能体调用都会增加上下文大小
- 3-4 次连续调用后可能触发截断
- 使用文件引用而非完整对象传递

### 3. 错误恢复需要果断
- 2 次失败后必须改变策略
- 不要重复调用相同的失败工具
- 直接分析是可靠的 fallback

### 4. 监控工具调用模式
- Hermes 的 `same_tool_failure_warning` 是重要信号
- 连续 3 次相同错误 = 系统性问题
- 需要立即诊断而非重试

## 推荐的故障排查流程

```
开始
  ↓
检查磁盘空间 (df -h E:)
  ↓
空间充足？
  ├─ NO → 清理会话 (cleanup_sessions(days=3))
  └─ YES → 继续
  ↓
检查 API 凭证 (cat .env | grep API_KEY)
  ↓
凭证有效？
  ├─ NO → 更新凭证或使用直接分析
  └─ YES → 继续
  ↓
创建新会话 (create_session())
  ↓
调用子智能体
  ↓
成功？
  ├─ YES → 读取结果
  └─ NO → 检查错误类型
      ↓
      [Errno 28] → 清理磁盘，重试 1 次，仍失败→直接分析
      401 Unauthorized → 检查凭证，使用直接分析
      Truncated → 立即使用直接分析
      Result file not found → 检查目录，使用直接分析
      ↓
      同一错误 2 次？
        ├─ YES → 切换策略（直接分析）
        └─ NO → 重试
```

## 直接分析脚本模板

当子智能体系统失败时，使用以下脚本直接分析：

```python
import pandas as pd
import numpy as np

# 读取数据
df = pd.read_csv('E:/project/Ecological_env/data/pollution_water_out.csv')
recent = df.tail(168)  # 最近 7 天

# 统计摘要
print("=== 统计摘要 ===")
for col in ['pH 值', '化学需氧量浓度（毫克/升）', '总氮浓度（毫克/升）']:
    if col in recent.columns:
        print(f"{col}: 均值={recent[col].mean():.2f}, 标准差={recent[col].std():.2f}")

# 异常检测
print("\n=== 异常检测 ===")
for col in ['pH 值', '化学需氧量浓度（毫克/升）']:
    if col in recent.columns:
        mean, std = recent[col].mean(), recent[col].std()
        outliers = recent[(recent[col] < mean - 3*std) | (recent[col] > mean + 3*std)]
        if len(outliers) > 0:
            print(f"{col}: {len(outliers)} 个异常值")

# 违规模式
print("\n=== 违规模式 ===")
for col in ['pH 值', '化学需氧量浓度（毫克/升）']:
    if col in recent.columns and recent[col].std() < 0.1:
        print(f"⚠️ 疑似插瓶干扰：{col} 标准差={recent[col].std():.4f}")
```

## 会话清理脚本

定期执行以下命令清理旧会话：

```bash
# Windows PowerShell
Get-ChildItem "E:\project\Ecological_env\workspace\state\" -Directory -Filter "session_*" | 
  Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-3) } | 
  Remove-Item -Recurse -Force

# Git Bash / MSYS
find /e/project/Ecological_env/workspace/state/ -name "session_*" -mtime +3 -exec rm -rf {} \;
```

## 监控指标

建议监控以下指标以预防类似问题：

| 指标 | 阈值 | 操作 |
|------|------|------|
| 磁盘可用空间 | <1 GB | 立即清理 |
| 会话目录数量 | >20 | 清理旧会话 |
| 响应截断次数 | ≥1 | 切换策略 |
| 同一工具失败次数 | ≥2 | 诊断并改变方法 |
| 上下文大小 | >10 MB | 使用文件引用 |

---

**文档版本**: 1.0  
**创建日期**: 2026-07-06  
**最后更新**: 2026-07-06  
**关联技能**: `orchestrator-core`, `wastewater-data-analysis`

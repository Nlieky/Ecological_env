# 编排工具链故障排查

## 症状：`call_subagent` 返回 "子智能体调用失败: 'NoneType' object has no attribute 'get'"

这是**被掩盖的错误**——真实的子智能体失败原因被一个代码 bug 吞掉了。分两层看：

### ① 表面 bug（掩盖真相的那一层）

`skills/orchestrator-core/scripts/tool_registration.py` → `_call_subagent_handler`：

```python
_cd = result.get("result", {}).get("chartData") if isinstance(result, dict) else None
```

当子智能体 subprocess 失败、返回 `result: None` 时，`result.get("result", {})` 返回的是 `None`（键存在、值为 null 时默认值 `{}` **不生效**），接着 `.get("chartData")` 就崩——抛出的正是那个没头没尾的错误。

修复（给 `.get()` 链加 None 保护）：

```python
_r = result.get("result") if isinstance(result, dict) else None
_cd = _r.get("chartData") if isinstance(_r, dict) else None
```

### ② 底层失败（真正要查的）

子智能体 subprocess 本身就失败了：返回码非 0 / 结果文件缺失 / 超时 / LLM_API_KEY 未设。真实原因写在：

`sessions/_subagent_traces/<task_id>_<subagent>.log`

`call_subagent.py` 无论成败都把子智能体 subprocess 的完整 stdout+stderr 落盘到这个固定目录（不依赖 session 路由，避免失败时 session 串了找不到）。看这个日志才能知道子智能体到底为什么崩。

常见根因：`LLM_API_KEY` 环境变量未设置（`call_subagent.py` 会显式返回 "LLM_API_KEY 环境变量未设置"，但被上面 ① 的 bug 吞掉后，主智能体只看到 None.get 错误）。

## Python 陷阱：`dict.get(key, default)` 在键存在但值为 None 时返回 None

```python
{"result": None}.get("result", {})  # -> None，不是 {}
```

默认值只在键**不存在**时生效；键存在但值为 `None` 时，`.get()` 返回 `None`。链式 `.get()` 之前先判 None，否则就是 `'NoneType' object has no attribute 'get'`。

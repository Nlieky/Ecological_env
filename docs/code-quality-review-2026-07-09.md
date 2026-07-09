# 代码质量审查报告

> **日期**: 2026-07-09
> **状态**: 🔴 发现严重问题

---

## 审查范围

核心调用链路代码质量审查：
- `workspace/skills/orchestrator-core/scripts/call_subagent.py`
- `subagents/*/run_agent.py`
- `subagents/*/run_agent_wrapper.py`

---

## 发现的问题

### 🔴 P0 - 严重问题（影响功能）

#### 1. 入口点不一致

**问题描述**：各子智能体使用不同的入口点模式

| 子智能体 | 入口点 | 模式 |
|---------|--------|------|
| anomaly-detection-agent | `run_agent.py` | 直接实现 |
| multi-dimensional-data-perception-agent | `run_agent.py` | 直接实现 |
| rule-reasoning-agent | `run_agent.py` → `run_agent_wrapper.py` | 间接调用 |
| disposition-execution-agent | `run_agent_wrapper.py` | ？ |

**影响**：
- 代码维护困难
- 行为不一致
- 难以追踪错误

#### 2. 循环导入问题

**位置**: `run_agent.py` 第 137 行
```python
from run_agent import AIAgent  # ❌ 错误！
```

**问题**：
- 文件名是 `run_agent.py`
- 导入语句是 `from run_agent import AIAgent`
- 这会导致循环导入或命名冲突

**正确做法**：
```python
from hermes_agent import AIAgent
# 或
from hermes.run_agent import AIAgent
```

#### 3. 结果文件名不一致

**期望** (在 `call_subagent.py` 中定义)：
```python
RESULT_FILE_NAMES = {
    "anomaly-detection": "anomaly_result.json",
    "multi-dimensional-data-perception": "data_result.json",
    "rule-reasoning": "rule_result.json",
    "disposition-execution": "disposition_result.json"
}
```

**实际** (在各个 `run_agent.py` 中)：
- `anomaly-detection-agent/run_agent.py` 优先检查 `anomaly_result.json`，但写入 `result.json` 或 `llm_result.json`
- `multi-dimensional-data-perception-agent/run_agent.py` 优先检查 `data_result.json`，但写入 `result.json` 或 `llm_result.json`

**影响**：
- 主智能体读取不到结果
- 调用链路中断

#### 4. 路径解析问题

**位置**: `call_subagent.py` 第 191-192 行
```python
current_dir = Path(__file__).parent.parent.parent.parent
subagent_path = (current_dir / subagent_rel_path).resolve()
```

**问题**：
- 使用相对路径 `../subagents/`
- `parent.parent.parent.parent` 容易出错
- 在不同调用深度下可能失败

**建议**：使用项目根目录的绝对路径

### 🟡 P1 - 重要问题（影响可维护性）

#### 5. 错误处理不一致

**模式 1** - 返回错误字典：
```python
return {"status": "failed", "error": str(e)}
```

**模式 2** - 直接退出：
```python
sys.exit(1)
```

**影响**：
- 调用方难以统一处理错误
- 错误信息丢失

#### 6. 日志级别不统一

有些使用 `logger.error`，有些使用 `logger.warning`，有些用 `print`。

#### 7. 缺少类型提示

许多函数缺少完整的类型注解。

#### 8. 重复代码

`run_agent.py` 在多个子智能体中几乎完全重复，应该提取为共享模块。

---

## 修复计划

### 阶段 1: 统一入口点

1. **决定统一模式**：
   - 选项 A：所有子智能体使用 `run_agent.py`（直接实现）
   - 选项 B：所有子智能体使用 `run_agent_wrapper.py`（间接调用）

2. **删除冗余文件**：
   - 删除所有 `run_agent_wrapper.py`
   - 或删除所有 `run_agent.py`，统一为 `run_agent_wrapper.py`

### 阶段 2: 修复导入问题

1. 修复 `from run_agent import AIAgent`
2. 确定正确的 Hermes AIAgent 导入路径

### 阶段 3: 统一结果文件名

1. 定义标准的结果文件名常量
2. 更新所有子智能体的写入逻辑
3. 更新主智能体的读取逻辑

### 阶段 4: 改进路径解析

1. 创建共享的路径工具模块
2. 使用绝对路径替代相对路径

### 阶段 5: 统一错误处理

1. 定义标准错误返回格式
2. 确保所有子智能体遵循相同模式

---

## 待修复文件清单

- [ ] `workspace/skills/orchestrator-core/scripts/call_subagent.py`
- [ ] `subagents/anomaly-detection-agent/run_agent.py`
- [ ] `subagents/multi-dimensional-data-perception-agent/run_agent.py`
- [ ] `subagents/rule-reasoning-agent/run_agent.py`
- [ ] `subagents/rule-reasoning-agent/run_agent_wrapper.py`（删除？）
- [ ] `subagents/disposition-execution-agent/run_agent.py`
- [ ] `subagents/disposition-execution-agent/run_agent_wrapper.py`（删除？）
- [ ] `subagents/anomaly-detection-agent/run_agent_wrapper.py`（删除？）

---

## 建议的优先级

1. **立即修复**：循环导入问题（P0-2）
2. **立即修复**：结果文件名不一致（P0-3）
3. **高优先级**：统一入口点（P0-1）
4. **中优先级**：路径解析改进（P1-4）
5. **低优先级**：错误处理统一（P1-5）

---

**下一步**: 询问用户希望采用哪种统一模式（选项 A 或 B），然后执行修复。

---

## 已完成的修复

### ✅ Hermes Agent 框架本地化 (2026-07-09)

**问题描述**:
- 项目依赖外部代码仓库 `D:\Hermes\hermes-agent`
- AIAgent 只读取 SOUL.md，项目需要 7 个身份文件
- 存在命名冲突和导入路径问题

**解决方案**:
- 复制 Hermes Agent 框架到 `shared/framework/hermes_agent/`
- 扩展身份文件读取支持（IDENTITY_FILES 常量和 load_identity_files() 函数）
- 更新所有子智能体导入路径
- 移除旧的 hermes_importer 工具

**实施内容**:
1. 创建框架目录结构
2. 复制核心常量文件并添加 IDENTITY_FILES 常量
3. 复制并修改提示构建器，添加 load_identity_files() 函数
4. 复制并修改系统提示组装器，使用扩展的身份文件加载
5. 复制 AIAgent 核心文件
6. 复制其他必要文件（session_db.py, agent_init.py, process_bootstrap.py 等）
7. 更新所有子智能体导入路径
8. 删除旧的 hermes_importer 工具
9. 更新 requirements.txt

**状态**: ✅ 完成

**验证**:
- ✅ 所有 7 个身份文件常量正确定义
- ✅ load_identity_files() 函数正确实现
- ✅ 所有子智能体导入路径已更新
- ✅ 代码质量审查通过

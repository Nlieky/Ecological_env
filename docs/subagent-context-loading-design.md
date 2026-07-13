# 子智能体上下文文件加载验证与修复设计

## 概述

本设计旨在验证并确保废水监测系统的 4 个子智能体能正确加载各自的上下文文件（SOUL.md、AGENTS.md、MEMORY.md、IDENTITY.md、USER.md、TOOLS.md）。

## 背景

### 当前状态

- **主智能体**：位于 `workspace/`，已验证可以加载上下文文件（通过 HERMES.md）
- **子智能体**：4 个子智能体位于 `subagents/*/`，每个都有完整的 6 个上下文文件
- **调用方式**：通过 `call_subagent.py` 使用 subprocess 调用

### 核心需求

1. 每个子智能体必须从自己的目录加载上下文文件
2. 保持现有的 subprocess 调用方式
3. 保持 6 个独立 md 文件的结构

### 已知约束

- Hermes 框架的 `delegate_task` 工具硬编码了 `skip_context_files=True`，不支持子智能体加载上下文
- 因此不使用 `delegate_task`，而是通过自定义的 `call_subagent.py` 调用

## Hermes 上下文文件加载机制

### 加载优先级（build_context_files_prompt）

Hermes 按以下优先级搜索并加载上下文文件：

1. `.hermes.md` 或 `HERMES.md` - 从 cwd 向上搜索到 git 根目录
2. `AGENTS.md` 或 `agents.md` - 仅在 cwd
3. `CLAUDE.md` 或 `claude.md` - 仅在 cwd
4. `.cursorrules` 或 `.cursor/rules/*.mdc` - 仅在 cwd
5. `SOUL.md` - 从 HERMES_HOME 加载（独立于项目上下文）

### 关键发现

- 现有的 `call_subagent.py` 已设置 `cwd=str(subagent_path)`
- 子智能体目录有 AGENTS.md，但没有 HERMES.md
- 理论上 Hermes 应该能找到并加载 AGENTS.md

## 验证方案

### 验证目标

确认当通过 `call_subagent.py` 调用子智能体时，子智能体的 AIAgent 确实加载了该子智能体目录下的上下文文件。

### 验证步骤

#### 步骤 1：添加调试输出

在子智能体的 `run_agent.py` 中添加调试代码，打印加载的上下文文件信息：

```python
# 在 AIAgent 初始化后添加
import sys
print(f"[DEBUG] Current working directory: {os.getcwd()}", file=sys.stderr, flush=True)
print(f"[DEBUG] HERMES_HOME: {os.environ.get('HERMES_HOME', 'not set')}", file=sys.stderr, flush=True)

# 在系统提示词构建后添加
system_prompt = agent._build_system_prompt()
print(f"[DEBUG] System prompt includes context files: {'AGENTS.md' in system_prompt or 'SOUL.md' in system_prompt}", file=sys.stderr, flush=True)
```

#### 步骤 2：运行测试调用

```python
from workspace.skills.orchestrator_core.scripts.call_subagent import call_subagent

result = call_subagent(
    "anomaly-detection",
    "简述你的身份和能力"
)
```

#### 步骤 3：检查输出

查看 stderr 输出，确认：
- cwd 是否正确设置为子智能体目录
- 系统提示词是否包含上下文文件内容

### 验证结果处理

#### 场景 A：验证成功

如果输出显示：
- cwd = `subagents/anomaly-detection-agent/`
- 系统提示词包含 AGENTS.md/SOUL.md 的内容

则现有方案已满足需求，无需修改。

#### 场景 B：验证失败

如果输出显示：
- cwd 不正确，或
- 系统提示词未包含上下文文件内容

则需要采用修复方案。

## 修复方案（仅在验证失败时执行）

### 方案 A：创建 HERMES.md 入口文件

**适用场景**：Hermes 无法识别 AGENTS.md 作为项目上下文

**做法**：为每个子智能体创建一个 HERMES.md，合并该子智能体的 6 个上下文文件内容。

**文件结构**：
```markdown
# 子智能体上下文 - 异常检测

> 此文件由 Hermes 框架自动加载，包含异常检测子智能体的完整上下文。

---

## 包含的上下文文件

本文件合并了以下所有上下文文件的内容：

1. SOUL.md - 子智能体身份
2. AGENTS.md - 工作区规范
3. MEMORY.md - 专业记忆
4. IDENTITY.md - 身份卡片
5. USER.md - 用户信息
6. TOOLS.md - 工具配置

---

[这里合并 6 个文件的完整内容]
```

**实现**：
- 创建脚本 `scripts/create_subagent_hermes_md.py`
- 扫描 `subagents/*/` 目录
- 为每个子智能体创建 HERMES.md

### 方案 B：修改 AIAgent 初始化（备选）

**适用场景**：方案 A 无法解决问题

**做法**：在子智能体的 `run_agent.py` 中，显式设置 `load_soul_identity=True` 和 `skip_context_files=False`。

## 实施计划

### 阶段 1：验证（必须执行）

1. 添加调试输出到 `subagents/anomaly-detection-agent/run_agent.py`
2. 运行测试调用
3. 分析输出结果

### 阶段 2：修复（条件执行）

仅在验证失败时执行：
1. 选择修复方案（方案 A 或 B）
2. 实施修复
3. 重新验证

### 阶段 3：清理

1. 移除调试代码（或改为可配置的日志级别）
2. 更新文档说明上下文加载机制

## 成功标准

- ✅ 验证输出显示子智能体正确加载了上下文文件
- ✅ 子智能体的响应体现了其专业身份（如异常检测子智能体表现出异常检测专业知识）
- ✅ 保持现有调用接口不变
- ✅ 保持 6 个独立 md 文件结构

## 风险与注意事项

1. **HERMES.md 与独立文件的维护**：如果采用方案 A 创建 HERMES.md，需要确保 HERMES.md 与 6 个独立文件保持同步。建议：
   - 将 HERMES.md 设为自动生成（不手动编辑）
   - 在 CI/CD 中验证同步性

2. **子智能体目录结构变化**：如果未来子智能体目录结构变化，需要更新验证和修复脚本

3. **Hermes 版本升级**：如果 Hermes 框架升级，上下文加载机制可能变化，需要重新验证

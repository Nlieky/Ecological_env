# Superpowers 技能使用指南

## 📖 目录

- [技能概览](#技能概览)
- [核心原则](#核心原则)
- [可用技能详解](#可用技能详解)
- [操作流程](#操作流程)
- [命令参考](#命令参考)
- [最佳实践](#最佳实践)
- [常见场景](#常见场景)

---

## 技能概览

Superpowers 是一组可重用的技能包，用于指导 AI 完成特定任务。每个技能都包含领域知识和最佳实践。

### 为什么使用技能？

- ✅ **一致性**: 每次都遵循相同的最佳实践
- ✅ **效率**: 不需要重复解释任务要求
- ✅ **质量**: 技能包含专家级的方法论
- ✅ **可追溯**: 明确知道使用了哪些流程

### 技能触发原则

**核心规则**: 只要技能有 1% 的适用可能性，就必须先调用技能。

```
┌─────────────────────┐
│  收到用户请求        │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ 技能可能适用？ │
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │           │
    是          否
     │           │
     ▼           ▼
  调用技能    直接响应
     │
     ▼
  按技能流程执行
```

---

## 核心原则

### 1. 优先级顺序

```
用户明确指令 > 技能规则 > 默认系统行为
```

如果 CLAUDE.md 说"不要用 TDD"，但 tdd 技能说"总是用 TDD"，**遵循用户指令**。

### 2. 技能优先级

当多个技能都可能适用时，按此顺序：

1. **流程技能** (brainstorming, debugging) - 确定如何处理任务
2. **实施技能** (frontend-design, mcp-builder) - 指导具体执行

### 3. 严格性分类

| 类型 | 说明 | 示例 |
|------|------|------|
| 刚性 | 必须严格遵循，不能变通 | TDD、systematic-debugging |
| 柔性 | 可根据上下文调整 | brainstorming、patterns |

---

## 可用技能详解

### 🎨 规划与设计类

#### brainstorming

**用途**: 在创建功能/组件/添加功能前，探索用户意图和设计选项

**何时使用**:
- 创建新功能
- 修改现有行为
- 添加新组件
- 架构设计

**触发词**:
- "设计一个..."
- "如何实现..."
- "重新规划..."
- "优化架构..."

**流程**:
1. 理解用户意图
2. 提出澄清问题
3. 探索多种方案
4. 讨论权衡
5. 确定方向

#### writing-plans

**用途**: 为多步骤任务创建结构化实施计划

**何时使用**:
- 有明确需求规格
- 需要实现复杂功能
- 多步骤任务
- 需要协作的开发工作

**输出**: 详细的实施计划文件

#### test-driven-development

**用途**: 测试驱动开发 - 先写测试，再写实现

**何时使用**:
- 实现任何新功能
- 修复 bug
- 重构代码

**刚性流程**: 必须严格遵循

---

### 🔍 调试与分析类

#### systematic-debugging

**用途**: 系统化调试 bug、测试失败、异常行为

**何时使用**:
- 遇到任何 bug
- 测试失败
- 意外行为
- 在提出修复方案之前

**刚性流程**: 必须严格遵循

#### code-review

**用途**: 审查代码正确性、bug、改进点

**何时使用**:
- 完成任务后
- 实现主要功能后
- 合并前
- 请求验证时

**参数**:
- `--effort low/medium/high`: 审查深度
- `--comment`: 发送 PR 评论
- `--fix`: 应用修复

#### simplify

**用途**: 审查并应用修复（等同 `/code-review --fix`）

---

### 🚀 执行与部署类

#### executing-plans

**用途**: 执行已有的实施计划

**何时使用**:
- 有书面实施计划
- 在单独会话中执行
- 需要审查检查点

#### verify

**用途**: 运行应用并观察行为，验证修改效果

**何时使用**:
- 要求验证 PR
- 确认修复有效
- 测试变更
- 验证本地修改

#### run

**用途**: 启动并驱动应用查看变更效果

**何时使用**:
- 要求运行/启动应用
- 确认修改在实际应用中有效
- 测试变更

---

### 🔄 流程与协作类

#### requesting-code-review

**用途**: 完成任务时请求代码审查

**何时使用**:
- 完成任务
- 实现主要功能
- 合并前

#### receiving-code-review

**用途**: 接收代码审查反馈

**何时使用**:
- 收到代码审查反馈
- 反馈似乎不清楚或技术上存疑

#### finishing-a-development-branch

**用途**: 开发完成、测试通过后决定如何集成

**何时使用**:
- 实现完成
- 所有测试通过
- 需要决定如何集成

---

### 📚 其他技能

| 技能 | 用途 |
|------|------|
| **init** | 初始化 CLAUDE.md |
| **loop** | 定期执行任务 |
| **fewer-permission-prompts** | 减少权限提示 |
| **keybindings-help** | 自定义快捷键 |
| **update-config** | 配置 settings.json |
| **claude-api** | 构建/调试 Claude API 应用 |
| **subagent-driven-development** | 使用独立任务执行实施计划 |
| **dispatching-parallel-agents** | 面向 2+ 个独立任务 |
| **using-git-worktrees** | 隔离工作空间 |
| **verification-before-completion** | 完成前验证 |

---

### 📦 文档与工具类

| 技能 | 用途 |
|------|------|
| **document-skills:docx** | Word 文档处理 |
| **document-skills:xlsx** | Excel 表格处理 |
| **document-skills:pdf** | PDF 文档处理 |
| **document-skills:pptx** | PowerPoint 演示文稿 |
| **document-skills:frontend-design** | 前端界面设计 |
| **document-skills:canvas-design** | 视觉艺术设计 |
| **document-skills:webapp-testing** | Web 应用测试 |
| **document-skills:skill-creator** | 创建/编辑技能 |

---

## 操作流程

### 流程 1: 开始新功能

```
用户请求
    ↓
[brainstorming] 探索需求和设计
    ↓
[writing-plans] 创建实施计划
    ↓
用户确认计划
    ↓
[tdd] 编写测试
    ↓
[executing-plans] 执行实施
    ↓
[verify] 验证效果
```

**示例命令**:
```bash
# 1. 开始设计
"我想添加一个新的异常检测算法"

# AI 自动调用 brainstorming 技能
# → 讨论算法选择、数据需求、集成方式

# 2. 创建计划
"帮我制定详细的实施计划"

# AI 自动调用 writing-plans 技能
# → 生成包含步骤、文件、验证的计划

# 3. 执行开发
"按照计划执行"

# AI 自动调用 tdd + executing-plans
# → 编写测试、实现功能、验证
```

---

### 流程 2: 修复 Bug

```
报告 Bug
    ↓
[systematic-debugging] 系统化调试
    ↓
定位根本原因
    ↓
[tdd] 编写失败测试
    ↓
修复问题
    ↓
[verify] 验证修复
    ↓
[code-review] 审查变更
```

**示例命令**:
```bash
# 报告问题
"数据注入功能不工作，feature-analysis-agent 收不到数据"

# AI 自动调用 systematic-debugging 技能
# → 收集症状、定位代码、分析原因
# → 提出修复方案

# 确认修复
"应用这个修复"

# AI 执行修复并验证
```

---

### 流程 3: 代码审查

```
选择审查范围
    ↓
[code-review] 分析代码
    ↓
获取发现的问题
    ↓
选择处理方式
    ↓
应用修复 / 手动修改
```

**命令选项**:
```bash
# 快速审查 (较少发现)
/code-review --effort low

# 中等审查 (推荐)
/code-review --effort medium

# 深度审查 (更全面)
/code-review --effort high

# 自动应用修复
/code-review --fix

# 发送 PR 评论
/code-review --comment

# 简化代码 (等同 --fix)
/simplify
```

---

### 流程 4: 完成开发分支

```
开发完成
    ↓
[verify] 验证功能
    ↓
[code-review] 审查代码
    ↓
[finishing-a-development-branch] 决定集成方式
    ↓
合并 / PR / 清理
```

---

## 命令参考

### 技能触发命令

```bash
# === 规划和设计 ===
/brainstorming          # 开始头脑风暴
/writing-plans          # 创建实施计划
/executing-plans        # 执行已有计划

# === 代码质量 ===
/code-review            # 审查代码
/simplify               # 简化代码
/tdd                    # 测试驱动开发
/systematic-debugging   # 系统化调试

# === 项目管理 ===
/requesting-code-review # 请求代码审查
/receiving-code-review  # 接收代码审查反馈
/finishing-a-development-branch  # 完成开发分支

# === 部署相关 ===
/run                    # 运行应用
/verify                 # 验证修改效果

# === 其他 ===
/init                   # 初始化 CLAUDE.md
/loop                   # 定期执行任务
```

### Claude Code 特有命令

```bash
# === 技能管理 ===
/skills                 # 列出可用技能
/skill <name>           # 调用特定技能

# === 测试 ===
/test                   # 运行测试
/test <file>            # 运行特定测试

# === Git ===
/git status             # Git 状态
/git diff               # 查看变更
/git commit             # 提交变更

# === 文件操作 ===
/edit                   # 编辑文件
/read                   # 读取文件
/search                 # 搜索代码
```

---

## 最佳实践

### 1. 不要跳过技能

❌ **错误做法**:
```
"这是一个简单的修改，直接改就行"
```

✅ **正确做法**:
```
"让我调用 brainstorming 确保理解需求"
```

### 2. 按顺序使用技能

```
规划阶段: brainstorming → writing-plans 
开发阶段: tdd → executing-plans
审查阶段: code-review → verify
```

### 3. 刚性技能严格遵循

- **TDD**: 必须先写测试
- **systematic-debugging**: 必须完成所有调试步骤
- **verification-before-completion**: 必须验证后才能声称完成

### 4. 利用 TodoWrite

技能包含检查清单时，使用 TodoWrite 跟踪进度:
```
[ ] 步骤 1
[ ] 步骤 2
[ ] 步骤 3
```

---

## 常见场景

### 场景 1: 重新规划数据治理流程

```bash
# 步骤 1: 头脑风暴
用户: "我想重新规划数据治理模块的架构"
AI: [调用 brainstorming]
    → 探讨各种架构方案
    → 分析优缺点
    → 确定最佳方向

# 步骤 2: 创建计划
用户: "好的，帮我制定详细计划"
AI: [调用 writing-plans]
    → 生成实施步骤
    → 列出需要修改的文件
    → 定义验证方法

# 步骤 3: 执行
用户: "开始执行"
AI: [调用 executing-plans]
    → 按计划实施
    → 更新进度
```

### 场景 2: 提升 Middleware 代码质量

```bash
# 步骤 1: 审查代码
用户: "审查 middleware 目录的代码质量"
AI: [调用 code-review --effort medium]
    → 分析代码问题
    → 提供改进建议

# 步骤 2: 应用修复
用户: "应用这些修复"
AI: [使用 Edit 工具]
    → 逐个应用修复
    → 解释变更原因

# 步骤 3: 验证
用户: "验证修复效果"
AI: [调用 verify]
    → 运行应用
    → 测试相关功能
```

### 场景 3: 修复数据注入 Bug

```bash
# 步骤 1: 系统化调试
用户: "数据注入不工作"
AI: [调用 systematic-debugging]
    → 收集症状和日志
    → 分析代码路径
    → 定位问题原因
    → 提出修复方案

# 步骤 2: TDD 修复
用户: "用 TDD 方式修复"
AI: [调用 tdd]
    → 编写失败测试
    → 实现修复
    → 确保测试通过
```

### 场景 4: 创建新技能

```bash
用户: "我想创建一个数据处理技能"
AI: [调用 brainstorming]
    → 讨论技能需求
    → 确定功能范围

用户: "开始创建"
AI: [调用 document-skills:skill-creator]
    → 编写技能内容
    → 创建测试用例
    → 评估技能效果
```

---

## 红旗警示

这些想法意味着**停止**，你在找借口：

| 想法 | 现实 |
|------|------|
| "这只是一个简单问题" | 问题 = 任务，需要检查技能 |
| "我需要更多上下文" | 技能检查在澄清问题之前 |
| "让我先探索代码库" | 技能告诉你如何探索 |
| "我可以快速检查 git/文件" | 文件缺少对话上下文 |
| "让我先收集信息" | 技能告诉你如何收集 |
| "这不需要正式技能" | 如果技能存在，就使用它 |
| "我记得这个技能" | 技能会演进，读取当前版本 |
| "这不算任务" | 行动 = 任务，检查技能 |
| "技能太复杂了" | 简单事会变复杂，技能防止这个 |
| "我觉得很有效率" | 无纪律行动浪费时间 |

---

## 快速参考卡

### 触发条件

```
有任何疑问 → 调用技能
开始新任务 → 调用技能
修改代码 → 调用技能
修复 Bug → 调用 systematic-debugging
创建功能 → 调用 brainstorming
审查代码 → 调用 code-review
```

### 技能选择树

```
开始
  │
  ├─ 需要规划/设计？
  │   └─ brainstorming → writing-plans
  │
  ├─ 遇到 Bug？
  │   └─ systematic-debugging
  │
  ├─ 需要审查代码？
  │   └─ code-review
  │
  ├─ 需要实现功能？
  │   └─ tdd → executing-plans
  │
  └─ 需要验证效果？
      └─ verify / run
```

---

## 附录

### 技能文件位置

```
~/.claude/skills/
├── using-superpowers/
├── brainstorming/
├── writing-plans/
├── systematic-debugging/
├── code-review/
├── test-driven-development/
├── document-skills/
│   ├── skill-creator/
│   ├── frontend-design/
│   └── ...
└── ...
```

### 创建自定义技能

```bash
# 调用 skill-creator 技能
/skill document-skills:skill-creator

# 按流程创建新技能
1. 定义技能用途
2. 编写技能内容
3. 创建测试用例
4. 评估技能效果
5. 迭代改进
```

---

## 总结

使用 Superpowers 技能的核心是：

1. **主动检查**: 任务开始前检查适用技能
2. **严格遵循**: 按技能流程执行
3. **持续改进**: 使用 code-review 不断提升

记住：**即使只有 1% 的可能性，也要调用技能**。

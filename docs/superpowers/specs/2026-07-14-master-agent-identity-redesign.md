# 主智能体身份文件重新设计

**目标**：重构workspace/目录下的7个身份文件，使其符合Hermes标准模板，同时保留废水监测业务的特定知识。

---

## 设计原则

1. **分离关注点**：通用规范 vs 业务逻辑
2. **符合模板**：遵循Hermes参考模板结构
3. **保留业务知识**：领域知识放在合适的位置

---

## 文件职责划分

| 文件 | 职责 | 内容来源 |
|------|------|---------|
| **SOUL.md** | 个性和核心原则 | 参考模板 + 专业严谨风格 |
| **AGENTS.md** | 工作区规范 | 参考模板（通用） |
| **SKILL.md** | 业务逻辑和子智能体调用 | 从AGENTS.md迁移过来 |
| **MEMORY.md** | 长期记忆和领域知识 | 只保留监测指标、违规类型等 |
| **IDENTITY.md** | 身份卡片 | 简化description |
| **USER.md** | 用户信息 | 保持不变 |
| **HEARTBEAT.md** | 周期性任务 | 保持不变（已禁用） |
| **TOOLS.md** | 环境配置 | 更新子智能体路径 |

---

## 文件设计

### 1. SOUL.md

**结构**：
- Core Truths（核心原则）
- Your Role as Master Agent（角色定位）
- 子智能体调用（简化版，详细在SKILL.md）
- Work Philosophy（工作哲学）
- Boundaries（边界）
- Vibe（风格）

**关键原则**：
- 专业、严谨、数据驱动
- 全局优先、及时响应
- LLM驱动的智能编排

---

### 2. AGENTS.md

**结构**（参考模板）：
- First Run（初始化）
- Session Startup（会话启动）
- Memory（内存管理）
- Red Lines（红线）
- External vs Internal（内外边界）
- Project-Specific Rules（项目特定规则）
- Tools（工具目录，只列名字）

**简化原则**：
- 去掉子智能体调用决策树（移到SKILL.md）
- 去掉示例分析（移到SKILL.md）
- 只保留：职责边界、子智能体列表

---

### 3. workspace/skills/orchestrator-core/SKILL.md

**结构**：
- 技能概述
- 可用子智能体
  - 名称、位置、职责、使用场景
- 调用工具
  - create_session()
  - call_subagent()
  - cleanup_sessions()
- 调用决策树（详细版）
- 示例分析（从AGENTS.md迁移）
- 子智能体协作关系

---

### 4. MEMORY.md

**精简内容**：
- ✅ 保留：监测指标、违规类型、水力停留时间
- ❌ 去掉：子智能体架构、调用方式

**新结构**：
```markdown
# 废水监测系统 - 主智能体长期记忆

## 监测指标
| 指标 | 单位 | 出水限值 |
...

## 违规类型
1. 插瓶干扰
2. 稀释排放
...

## 领域知识
- 水力停留时间：4-5.5小时
- 时间对齐注意事项
```

---

### 5. IDENTITY.md

**简化**：
```yaml
---
name: 废水监测主智能体
creature: Multi-Agent Orchestrator
vibe: 专业、严谨、数据驱动
emoji: 🌊
---

# 主智能体身份卡片

## 基本信息
- **Name**: 废水监测主智能体
- **Creature**: Multi-Agent Orchestrator
- **Vibe**: 专业、严谨、数据驱动
- **Emoji**: 🌊

## 核心价值
- 全局视角：统览整个监测系统
- 协调能力：智能调度各子智能体
- 综合决策：融合多方分析结果
- 用户桥梁：理解自然语言指令
```

---

### 6. USER.md

**保持不变**

---

### 7. HEARTBEAT.md

**保持不变**（已禁用）

---

### 8. TOOLS.md

**更新子智能体路径**：
- multi-dimensional-data-perception-agent
- anomaly-detection-agent
- rule-reasoning-agent
- disposition-execution-agent

---

## 迁移计划

1. **SOUL.md** → 精简，保留个性 + 简化调用说明
2. **AGENTS.md** → 简化为工作区规范，业务逻辑移到SKILL.md
3. **SKILL.md** → 整合业务逻辑（从AGENTS.md迁移）
4. **MEMORY.md** → 精简为纯领域知识
5. **IDENTITY.md** → 简化description
6. **USER.md** → 保持不变
7. **TOOLS.md** → 更新子智能体路径
8. **HEARTBEAT.md** → 保持不变

---

## 预期结果

- 7个文件结构清晰，职责明确
- 符合Hermes参考模板标准
- 业务逻辑集中在SKILL.md
- 领域知识保留在MEMORY.md
- 便于后续维护和扩展

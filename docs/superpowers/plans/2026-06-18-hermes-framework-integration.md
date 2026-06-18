# Hermes框架集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将废水监测系统从自定义orchestrator-core框架迁移到Hermes Agent框架，实现清晰的"LLM驱动主智能体 → 4个子智能体 → 三库支撑"架构

**Architecture:** 主智能体（Hermes AIAgent）通过delegate_tool.py并发调用4个子智能体（多维数据感知、异常检测、规则推理、研判处置），三库（operators、data、knowledge）统一在shared/目录提供支撑

**Tech Stack:** Hermes Agent框架（NousResearch/hermes-agent）、Python 3.13、YAML配置

---

## Phase 1: Hermes框架验证与准备

### Task 1: 验证Hermes框架安装

**Files:**
- Verify: `D:\Hermes\hermes-agent\`

- [ ] **Step 1: 检查Hermes框架路径**

```bash
ls -la "D:/Hermes/hermes-agent/"
```

Expected: 显示Hermes框架目录内容，包含run_agent.py、tools/等

- [ ] **Step 2: 验证delegate_tool.py存在**

```bash
ls -la "D:/Hermes/hermes-agent/tools/delegate_tool.py"
```

Expected: 文件存在

- [ ] **Step 3: 检查Hermes版本**

```bash
cd "D:/Hermes/hermes-agent" && git remote -v
```

Expected: 显示origin为https://github.com/NousResearch/hermes-agent.git

---

### Task 2: 备份现有orchestrator-core

**Files:**
- Backup: `workspace/skills/orchestrator-core/`
- Create: `workspace/skills/orchestrator-core-backup/`

- [ ] **Step 1: 创建备份目录**

```bash
mkdir -p "E:/project/Ecological_env/workspace/skills/orchestrator-core-backup"
```

Expected: 目录创建成功

- [ ] **Step 2: 复制orchestrator-core到备份目录**

```bash
cp -r "E:/project/Ecological_env/workspace/skills/orchestrator-core/"* "E:/project/Ecological_env/workspace/skills/orchestrator-core-backup/"
```

Expected: 所有文件复制成功

- [ ] **Step 3: 验证备份完整性**

```bash
ls -la "E:/project/Ecological_env/workspace/skills/orchestrator-core-backup/scripts/"
```

Expected: 显示所有备份的脚本文件

- [ ] **Step 4: 创建备份说明文件**

```bash
cat > "E:/project/Ecological_env/workspace/skills/orchestrator-core-backup/README.md" << 'EOF'
# Orchestrator-Core备份

备份日期: 2026-06-18
原因: 迁移到Hermes框架

此目录包含原有的orchestrator-core实现，作为参考保留。
EOF
```

Expected: README.md创建成功

---

### Task 3: 创建.hermes配置目录

**Files:**
- Create: `.hermes/`
- Create: `.hermes/config.yaml`

- [ ] **Step 1: 创建.hermes目录**

```bash
mkdir -p "E:/project/Ecological_env/.hermes"
```

Expected: 目录创建成功

- [ ] **Step 2: 创建Hermes主配置文件**

```bash
cat > "E:/project/Ecological_env/.hermes/config.yaml" << 'EOF'
hermes:
  version: "1.0"
  
model:
  provider: anthropic
  model: claude-sonnet-4-20250514
  
workspace:
  path: ./workspace
  
subagents:
  path: ./subagents
  auto_approve: false
  
memory:
  enabled: true
  provider: builtin
  path: ./workspace/MEMORY.md
  
tools:
  enabled:
    - multi_dimensional_data_perception
    - anomaly_detection
    - rule_reasoning
    - disposition_execution
    
delegation:
  max_concurrent_children: 4
  max_spawn_depth: 1
  
logging:
  level: INFO
  file: logs/hermes.log
EOF
```

Expected: config.yaml创建成功

- [ ] **Step 3: 验证配置文件语法**

```bash
cat "E:/project/Ecological_env/.hermes/config.yaml"
```

Expected: 显示完整的配置内容

- [ ] **Step 4: 添加.hermes到.gitignore**

```bash
if ! grep -q ".hermes/" "E:/project/Ecological_env/.gitignore"; then
  echo ".hermes/cache/" >> "E:/project/Ecological_env/.gitignore"
fi
```

Expected: .gitignore更新成功

---

## Phase 2: 目录结构重组

### Task 4: 移动knowledge目录到shared/knowledge

**Files:**
- Move: `knowledge/` → `shared/knowledge/`
- Update: Import statements in affected files

- [ ] **Step 1: 验证knowledge目录存在**

```bash
ls -la "E:/project/Ecological_env/knowledge/"
```

Expected: 显示regulations/、patterns/、expert/目录

- [ ] **Step 2: 验证shared/knowledge不存在**

```bash
if [ -d "E:/project/Ecological_env/shared/knowledge" ]; then
  echo "ERROR: shared/knowledge already exists"
  exit 1
fi
```

Expected: 无错误输出

- [ ] **Step 3: 移动knowledge到shared/knowledge**

```bash
mv "E:/project/Ecological_env/knowledge" "E:/project/Ecological_env/shared/knowledge"
```

Expected: 目录移动成功

- [ ] **Step 4: 验证新位置**

```bash
ls -la "E:/project/Ecological_env/shared/knowledge/"
```

Expected: 显示regulations/、process_knowledge/、violation_patterns/、expert_experience/目录

---

### Task 5: 创建子智能体memory目录

**Files:**
- Create: `subagents/*/memory/`

- [ ] **Step 1: 创建多维数据感知子智能体memory目录**

```bash
mkdir -p "E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/memory"
```

Expected: 目录创建成功

- [ ] **Step 2: 创建异常检测子智能体memory目录**

```bash
mkdir -p "E:/project/Ecological_env/subagents/anomaly-detection-agent/memory"
```

Expected: 目录创建成功

- [ ] **Step 3: 创建规则推理子智能体memory目录**

```bash
mkdir -p "E:/project/Ecological_env/subagents/rule-reasoning-agent/memory"
```

Expected: 目录创建成功

- [ ] **Step 4: 创建研判预警与处置执行子智能体memory目录**

```bash
mkdir -p "E:/project/Ecological_env/subagents/disposition-execution-agent/memory"
```

Expected: 目录创建成功

- [ ] **Step 5: 验证所有memory目录创建**

```bash
for agent in multi-dimensional-data-perception-agent anomaly-detection-agent rule-reasoning-agent disposition-execution-agent; do
  ls -d "E:/project/Ecological_env/subagents/$agent/memory"
done
```

Expected: 显示4个memory目录路径

---

### Task 6: 创建workspace/memory目录

**Files:**
- Create: `workspace/memory/`

- [ ] **Step 1: 创建主智能体memory目录**

```bash
mkdir -p "E:/project/Ecological_env/workspace/memory"
```

Expected: 目录创建成功

- [ ] **Step 2: 创建memory目录README**

```bash
cat > "E:/project/Ecological_env/workspace/memory/README.md" << 'EOF'
# 主智能体记忆目录

此目录存储主智能体的会话日志和记忆文件。
EOF
```

Expected: README.md创建成功

---

### Task 7: 创建interfaces和scripts目录

**Files:**
- Create: `interfaces/`
- Create: `scripts/`

- [ ] **Step 1: 创建interfaces目录**

```bash
mkdir -p "E:/project/Ecological_env/interfaces"
```

Expected: 目录创建成功

- [ ] **Step 2: 创建scripts目录**

```bash
mkdir -p "E:/project/Ecological_env/scripts"
```

Expected: 目录创建成功

- [ ] **Step 3: 创建interfaces目录README**

```bash
cat > "E:/project/Ecological_env/interfaces/README.md" << 'EOF'
# 接口标准化定义

此目录包含子智能体通信协议、输入输出schema、错误代码等标准化接口定义。
EOF
```

Expected: README.md创建成功

---

## Phase 3: 配置文件创建

### Task 8: 创建shared/configs/hermes_config.yaml

**Files:**
- Create: `shared/configs/hermes_config.yaml`

- [ ] **Step 1: 创建Hermes资源配置文件**

```bash
cat > "E:/project/Ecological_env/shared/configs/hermes_config.yaml" << 'EOF'
# Hermes资源配置文件

# 资源路径配置
resources:
  operators_path: ./shared/operators
  data_path: ./shared/data
  knowledge_path: ./shared/knowledge

# 子智能体访问控制
access_control:
  multi_dimensional_data_perception_agent:
    read:
      - shared/data/**
    write:
      - shared/data/processed/**
  
  anomaly_detection_agent:
    read:
      - shared/data/**
      - shared/operators/**
    write:
      - shared/cache/anomaly_results/**
  
  rule_reasoning_agent:
    read:
      - shared/knowledge/**
      - shared/cache/anomaly_results/**
    write:
      - shared/cache/rule_reasoning_results/**
  
  disposition_execution_agent:
    read:
      - shared/data/**
      - shared/knowledge/**
      - shared/cache/**
    write:
      - shared/outputs/alerts/**
      - shared/outputs/reports/**

# 子智能体配置映射
subagent_mapping:
  multi_dimensional_data_perception:
    path: ./subagents/multi-dimensional-data-perception-agent
    skills:
      - data-perception-core
  
  anomaly_detection:
    path: ./subagents/anomaly-detection-agent
    skills:
      - anomaly-detection-core
  
  rule_reasoning:
    path: ./subagents/rule-reasoning-agent
    skills:
      - rule-reasoning-core
  
  disposition_execution:
    path: ./subagents/disposition-execution-agent
    skills:
      - disposition-execution-core
EOF
```

Expected: hermes_config.yaml创建成功

- [ ] **Step 2: 验证配置文件语法**

```bash
cat "E:/project/Ecological_env/shared/configs/hermes_config.yaml" | head -20
```

Expected: 显示文件前20行内容

---

## Phase 4: 文件清理

### Task 9: 删除过时专利文档

**Files:**
- Delete: `docs/专利.txt`
- Delete: `docs/专利_实施例部分.txt`
- Delete: `docs/专利_方法步骤部分.txt`
- Delete: `docs/专利_系统架构部分_修正版.txt`
- Delete: `docs/参专利.txt`

- [ ] **Step 1: 验证专利文档存在**

```bash
ls -la "E:/project/Ecological_env/docs/" | grep "专利"
```

Expected: 显示专利相关文件

- [ ] **Step 2: 删除专利文档**

```bash
cd "E:/project/Ecological_env/docs"
rm -f 专利.txt 专利_实施例部分.txt 专利_方法步骤部分.txt 专利_系统架构部分_修正版.txt 参专利.txt
```

Expected: 文件删除成功

- [ ] **Step 3: 验证删除成功**

```bash
ls "E:/project/Ecological_env/docs/" | grep "专利" || echo "No patent files found (expected)"
```

Expected: 显示"No patent files found (expected)"

---

### Task 10: 删除临时垃圾文件

**Files:**
- Delete: `.understand-anything/.trash-1781689450/`
- Delete: `.understand-anything/tmp/`

- [ ] **Step 1: 检查临时文件大小**

```bash
du -sh "E:/project/Ecological_env/.understand-anything/.trash-1781689450/" 2>/dev/null || echo "Trash directory not found"
```

Expected: 显示目录大小或"not found"

- [ ] **Step 2: 删除临时文件**

```bash
rm -rf "E:/project/Ecological_env/.understand-anything/.trash-1781689450/"
rm -rf "E:/project/Ecological_env/.understand-anything/tmp/"
```

Expected: 删除成功

- [ ] **Step 3: 验证删除成功**

```bash
ls "E:/project/Ecological_env/.understand-anything/" | grep -E "trash|tmp" || echo "No temp directories found (expected)"
```

Expected: 显示"No temp directories found (expected)"

---

### Task 11: 归档过时计划文档

**Files:**
- Archive: `docs/superpowers/plans/2024-06-08-ui-redesign.md`
- Archive: `docs/任务目标.md`

- [ ] **Step 1: 创建归档目录**

```bash
mkdir -p "E:/project/Ecological_env/docs/archive"
```

Expected: 目录创建成功

- [ ] **Step 2: 移动过时计划到归档**

```bash
if [ -f "E:/project/Ecological_env/docs/superpowers/plans/2024-06-08-ui-redesign.md" ]; then
  mv "E:/project/Ecological_env/docs/superpowers/plans/2024-06-08-ui-redesign.md" "E:/project/Ecological_env/docs/archive/"
fi
```

Expected: 文件移动或不存在

- [ ] **Step 3: 移动任务目标文档**

```bash
if [ -f "E:/project/Ecological_env/docs/任务目标.md" ]; then
  mv "E:/project/Ecological_env/docs/任务目标.md" "E:/project/Ecological_env/docs/archive/"
fi
```

Expected: 文件移动或不存在

---

## Phase 5: 文档更新

### Task 12: 创建架构文档

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: 创建architecture.md**

```bash
cat > "E:/project/Ecological_env/docs/architecture.md" << 'EOF'
# 废水监测系统架构说明

## 核心框架

```
LLM驱动主智能体（Hermes框架）
    ├── 意图识别（理解用户查询/数据信号）
    ├── 逻辑推理（规划执行策略）
    └── 子智能体调度（按需选择4个子智能体）
            ↓
4个子智能体（专业执行）
├── 多维数据感知子智能体 → 接入 shared/data/
├── 异常检测子智能体 → 调用 shared/operators/
├── 规则推理子智能体 → 调用 shared/knowledge/
└── 研判预警与处置执行子智能体
            ↓
三库支撑（全局共享资源）
├── 数据库 (shared/data/)
├── 算子库 (shared/operators/)
└── 知识库 (shared/knowledge/)
```

## Hermes框架

主智能体基于Hermes框架实现：
- Agent抽象
- 工具集成
- 子智能体通信
- LLM协调

## 子智能体职责

### 1. 多维数据感知子智能体 📊

- 数据获取：接入 shared/data/historical/
- 数据预处理：清洗、对齐、标准化
- 输出：标准化时序数据

### 2. 异常检测子智能体 🔍

- 算子调用：从 shared/operators/ 调用检测算子
- 异常识别：5类异常模式
- 违规检测：4类违规模式
- 输出：异常检测结果

### 3. 规则推理子智能体 ⚖️

- 知识调用：从 shared/knowledge/ 调用法规/工艺/专家经验
- 规则推理：合规性校验、工艺机理校验
- 违规判定：语义层面违规结论
- 输出：违规判定结果

### 4. 研判预警与处置执行子智能体 🚨

- 融合共识：综合异常检测和规则推理
- 预警分级：一般/较重/严重
- 工单生成：包含核查要点、法规条款
- 输出：预警信息和处置工单
EOF
```

Expected: architecture.md创建成功

- [ ] **Step 2: 验证文档创建**

```bash
cat "E:/project/Ecological_env/docs/architecture.md"
```

Expected: 显示完整文档内容

---

### Task 13: 更新CLAUDE.md

**Files:**
- Update: `CLAUDE.md`

- [ ] **Step 1: 在CLAUDE.md开头添加架构说明**

```bash
# 创建临时文件包含新内容
cat > /tmp/claude_new_header.md << 'EOF'
# 废水监测系统 - Claude AI助手配置

> **重要架构更新（2026-06-18）**
> 
> 本项目已迁移到**Hermes Agent框架**作为底层智能体框架。

## 核心架构原则

### LLM驱动主智能体框架

本项目采用Hermes Agent框架（NousResearch/hermes-agent）实现LLM驱动的智能体架构：

- **主智能体**（workspace/）：使用Hermes AIAgent类，负责意图识别、任务编排、对话管理
- **4个子智能体**（subagents/）：每个都是独立的Hermes AIAgent实例，通过delegate_tool.py并发调用
- **三库一体**（shared/）：operators（算子库）、data（数据库）、knowledge（知识库）统一在shared/目录

### 子智能体调用规范

主智能体通过Hermes的delegate_task()函数调用子智能体：
- **调用方式**：阻塞式+并发（max_concurrent_children: 4）
- **上下文隔离**：每个子智能体获得独立的对话历史和task_id
- **结果整合**：主智能体阻塞等待所有子智能体完成后整合结果

### Hermes框架特性

- **记忆机制**：跨会话记忆，让项目越来越清晰
- **身份文件支持**：SOUL.md（个性）、AGENTS.md（规则）、MEMORY.md（记忆）、USER.md（用户配置）
- **桌面版支持**：未来可通过Hermes Desktop提供图形界面

---

EOF

# 读取原有内容并追加
cat "E:/project/Ecological_env/CLAUDE.md" >> /tmp/claude_new_header.md

# 替换原文件
mv /tmp/claude_new_header.md "E:/project/Ecological_env/CLAUDE.md"
```

Expected: CLAUDE.md更新成功

- [ ] **Step 2: 验证更新**

```bash
head -30 "E:/project/Ecological_env/CLAUDE.md"
```

Expected: 显示新的架构说明内容

---

### Task 14: 更新README.md目录结构

**Files:**
- Update: `README.md`

- [ ] **Step 1: 备份README.md**

```bash
cp "E:/project/Ecological_env/README.md" "E:/project/Ecological_env/README.md.backup"
```

Expected: 备份文件创建成功

- [ ] **Step 2: 更新README.md中的目录结构**

```bash
# 使用sed替换knowledge路径为shared/knowledge
sed -i 's|knowledge/|shared/knowledge/|g' "E:/project/Ecological_env/README.md"
```

Expected: 路径更新成功

- [ ] **Step 3: 在README.md中添加Hermes框架说明**

```bash
# 在适当位置添加Hermes说明
sed -i '/^## 技术栈/a\\n**底层框架**: [Hermes Agent](https://github.com/NousResearch/hermes-agent) - LLM驱动智能体框架\\n' "E:/project/Ecological_env/README.md"
```

Expected: README.md更新成功

---

### Task 15: 创建接口标准化文档

**Files:**
- Create: `interfaces/subagent_protocol.md`
- Create: `interfaces/input_schema.json`
- Create: `interfaces/output_schema.json`

- [ ] **Step 1: 创建子智能体通信协议文档**

```bash
cat > "E:/project/Ecological_env/interfaces/subagent_protocol.md" << 'EOF'
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
EOF
```

Expected: subagent_protocol.md创建成功

- [ ] **Step 2: 创建输入Schema**

```bash
cat > "E:/project/Ecological_env/interfaces/input_schema.json" << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SubagentInput",
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "description": "任务唯一标识符"
    },
    "task_type": {
      "type": "string",
      "enum": ["data_perception", "anomaly_detection", "rule_reasoning", "disposition_execution"],
      "description": "任务类型"
    },
    "params": {
      "type": "object",
      "description": "任务参数"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "任务时间戳"
    }
  },
  "required": ["task_id", "task_type"]
}
EOF
```

Expected: input_schema.json创建成功

- [ ] **Step 3: 创建输出Schema**

```bash
cat > "E:/project/Ecological_env/interfaces/output_schema.json" << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SubagentOutput",
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "description": "任务唯一标识符"
    },
    "status": {
      "type": "string",
      "enum": ["success", "failure"],
      "description": "执行状态"
    },
    "result": {
      "type": "object",
      "description": "执行结果"
    },
    "errors": {
      "type": "array",
      "items": {"type": "string"},
      "description": "错误信息列表"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "完成时间戳"
    }
  },
  "required": ["task_id", "status"]
}
EOF
```

Expected: output_schema.json创建成功

---

## Phase 6: 验收测试

### Task 16: 验证目录结构

**Files:**
- Verify: Directory structure

- [ ] **Step 1: 验证knowledge已移至shared/knowledge**

```bash
if [ ! -d "E:/project/Ecological_env/shared/knowledge" ]; then
  echo "FAIL: shared/knowledge not found"
  exit 1
fi
```

Expected: 无错误输出

- [ ] **Step 2: 验证每个子智能体都有memory目录**

```bash
for agent in multi-dimensional-data-perception-agent anomaly-detection-agent rule-reasoning-agent disposition-execution-agent; do
  if [ ! -d "E:/project/Ecological_env/subagents/$agent/memory" ]; then
    echo "FAIL: $agent/memory not found"
    exit 1
  fi
done
echo "All subagent memory directories verified"
```

Expected: 显示"All subagent memory directories verified"

- [ ] **Step 3: 验证.hermes配置存在**

```bash
if [ ! -f "E:/project/Ecological_env/.hermes/config.yaml" ]; then
  echo "FAIL: .hermes/config.yaml not found"
  exit 1
fi
```

Expected: 无错误输出

---

### Task 17: 验证三库可访问性

**Files:**
- Verify: shared/ structure

- [ ] **Step 1: 验证三库目录结构**

```bash
echo "=== 三库结构验证 ==="
echo "算子库:"
ls -la "E:/project/Ecological_env/shared/operators/" | head -5
echo ""
echo "数据库:"
ls -la "E:/project/Ecological_env/shared/data/" | head -5
echo ""
echo "知识库:"
ls -la "E:/project/Ecological_env/shared/knowledge/" | head -5
```

Expected: 显示三库目录内容

---

### Task 18: 验证配置文件完整性

**Files:**
- Verify: Configuration files

- [ ] **Step 1: 验证.hermes/config.yaml**

```bash
cat "E:/project/Ecological_env/.hermes/config.yaml"
```

Expected: 显示完整Hermes配置

- [ ] **Step 2: 验证shared/configs/hermes_config.yaml**

```bash
cat "E:/project/Ecological_env/shared/configs/hermes_config.yaml"
```

Expected: 显示Hermes资源配置

---

### Task 19: 验证文档更新

**Files:**
- Verify: Documentation

- [ ] **Step 1: 验证架构文档存在**

```bash
if [ ! -f "E:/project/Ecological_env/docs/architecture.md" ]; then
  echo "FAIL: architecture.md not found"
  exit 1
fi
```

Expected: 无错误输出

- [ ] **Step 2: 验证接口文档存在**

```bash
for file in subagent_protocol.md input_schema.json output_schema.json; do
  if [ ! -f "E:/project/Ecological_env/interfaces/$file" ]; then
    echo "FAIL: interfaces/$file not found"
    exit 1
  fi
done
echo "All interface documents verified"
```

Expected: 显示"All interface documents verified"

---

### Task 20: 创建验收检查清单

**Files:**
- Create: `HERMES_MIGRATION_CHECKLIST.md`

- [ ] **Step 1: 创建验收检查清单文档**

```bash
cat > "E:/project/Ecological_env/HERMES_MIGRATION_CHECKLIST.md" << 'EOF'
# Hermes框架迁移验收检查清单

## 目录结构验收
- [ ] knowledge/ 已移入 shared/knowledge/
- [ ] 每个子智能体都有 memory/ 目录
- [ ] .hermes/ 目录和配置文件已创建
- [ ] orchestrator-core 已备份到参考目录

## 三库访问验收
- [ ] shared/operators/ 目录结构完整
- [ ] shared/data/ 目录结构完整
- [ ] shared/knowledge/ 目录结构完整（从根目录移入）

## 配置文件验收
- [ ] .hermes/config.yaml 已创建并包含正确配置
- [ ] shared/configs/hermes_config.yaml 已创建
- [ ] 接口标准化文档已创建

## 文档更新验收
- [ ] docs/architecture.md 已创建并反映新架构
- [ ] CLAUDE.md 已更新说明Hermes框架
- [ ] README.md 已更新目录结构
- [ ] 接口标准化文档完整

## 文件清理验收
- [ ] 过时专利文档已删除
- [ ] 临时垃圾文件已删除
- [ ] 过时计划文档已归档

## 下一步：Hermes框架集成测试
- [ ] 验证Hermes框架可用性
- [ ] 测试delegate_tool.py调用机制
- [ ] 验证主智能体启动
- [ ] 验证子智能体调用
EOF
```

Expected: 检查清单文档创建成功

- [ ] **Step 2: 显示检查清单**

```bash
cat "E:/project/Ecological_env/HERMES_MIGRATION_CHECKLIST.md"
```

Expected: 显示完整检查清单

---

## Phase 7: 提交与总结

### Task 21: 提交目录结构重组更改

**Files:**
- Git: Commit changes

- [ ] **Step 1: 查看更改状态**

```bash
cd "E:/project/Ecological_env" && git status
```

Expected: 显示修改和新增的文件

- [ ] **Step 2: 添加所有更改到暂存区**

```bash
cd "E:/project/Ecological_env" && git add .
```

Expected: 文件添加到暂存区

- [ ] **Step 3: 提交目录结构重组**

```bash
cd "E:/project/Ecological_env" && git commit -m "refactor: 目录结构重组 - Hermes框架集成准备

- 移动 knowledge/ 到 shared/knowledge/ (三库统一)
- 创建子智能体 memory/ 目录
- 创建 .hermes/ 配置目录
- 创建 interfaces/ 和 scripts/ 目录
- 删除过时专利文档和临时文件
- 创建架构文档和接口标准化文档
- 更新 CLAUDE.md 和 README.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

Expected: Git提交成功

---

### Task 22: 创建迁移总结文档

**Files:**
- Create: `HERMES_MIGRATION_SUMMARY.md`

- [ ] **Step 1: 创建迁移总结**

```bash
cat > "E:/project/Ecological_env/HERMES_MIGRATION_SUMMARY.md" << 'EOF'
# Hermes框架迁移总结

## 迁移日期
2026-06-18

## 主要变更

### 1. 目录结构重组
- knowledge/ → shared/knowledge/（三库统一）
- 每个子智能体添加 memory/ 目录
- 创建 .hermes/ 配置目录
- 创建 interfaces/ 和 scripts/ 目录

### 2. 配置文件
- .hermes/config.yaml（Hermes主配置）
- shared/configs/hermes_config.yaml（资源配置）

### 3. 文档更新
- docs/architecture.md（新建）
- interfaces/subagent_protocol.md（新建）
- interfaces/input_schema.json（新建）
- interfaces/output_schema.json（新建）
- CLAUDE.md（更新）
- README.md（更新）

### 4. 文件清理
- 删除5个过时专利文档
- 删除临时垃圾文件（.understand-anything/.trash-*）
- 归档过时计划文档

## 下一步

1. 验证Hermes框架可用性
2. 实现Hermes集成代码
3. 测试子智能体调用机制
4. 验证记忆系统

## 参考
- 设计文档: docs/superpowers/specs/2026-06-18-hermes-framework-integration-design.md
- Hermes框架: https://github.com/NousResearch/hermes-agent
EOF
```

Expected: 迁移总结创建成功

- [ ] **Step 2: 显示迁移总结**

```bash
cat "E:/project/Ecological_env/HERMES_MIGRATION_SUMMARY.md"
```

Expected: 显示完整迁移总结

---

## 总结

本实施计划包含22个详细任务，涵盖：

1. **Hermes框架验证与准备**（3个任务）
2. **目录结构重组**（4个任务）
3. **配置文件创建**（1个任务）
4. **文件清理**（3个任务）
5. **文档更新**（4个任务）
6. **验收测试**（5个任务）
7. **提交与总结**（2个任务）

每个任务都是bite-sized，包含具体的文件路径、命令和预期输出，确保工程师可以按照计划逐步执行。

**预计完成时间**：约4-5天

**验收标准**：所有检查清单项目通过

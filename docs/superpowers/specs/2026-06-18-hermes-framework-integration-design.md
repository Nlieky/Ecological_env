# 废水监测系统Hermes框架集成架构设计

> **创建日期**：2026-06-18
> **状态**：待审批
> **优先级**：高

## 背景

当前项目架构存在以下问题：
1. 知识图谱识别的11个架构层没有清晰反映核心框架逻辑
2. 智能体底层框架不明确（使用orchestrator-core自定义实现）
3. knowledge/目录在项目根目录，未与三库统一
4. 项目状态"严重混乱"，需要重新梳理架构

**核心需求**：
- 采用Hermes Agent框架（NousResearch/hermes-agent）作为底层框架
- 清晰体现"LLM驱动主智能体 → 意图识别 → 4个子智能体 → 三库支撑"的逻辑
- 保持现有workspace/和subagents/目录结构
- 三库统一在shared/下

## 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Agent 框架                          │
│                  (NousResearch/hermes-agent)                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼──────────┐                    ┌───────────▼─────────┐
│  主智能体        │                    │   Hermes Desktop   │
│  (workspace/)    │◄── 未来可扩展 ──│   (可选)          │
│                 │                    │                   │
│ • SOUL.md       │                    │ • 图形界面        │
│ • AGENTS.md     │                    │ • 文件浏览器      │
│ • MEMORY.md     │                    │ • 语音交互        │
│ • IDENTITY.md   │                    │ • 设置管理        │
│ • USER.md       │                    └───────────────────┘
└────────┬────────┘
         │ delegate_tool.py (阻塞式+并发)
         │
    ┌────┴─────┬──────────┬──────────┐
    │          │          │          │
┌───▼───┐ ┌──▼──┐ ┌────▼───┐ ┌────▼───┐
│多维   │ │异常 │ │ 规则   │ │ 研判   │
│数据   │ │检测 │ │ 推理   │ │ 处置   │
│感知   │ │     │ │         │ │         │
└───┬───┘ └──┬──┘ └────┬───┘ └────┬───┘
    │        │         │          │
    └────────┴─────────┴──────────┘
                    │
         ┌──────────▼──────────┐
         │    三库支撑          │
         │  (shared/)          │
         ├─────────────────────┤
         │ • operators/        │
         │ • data/             │
         │ • knowledge/        │
         └─────────────────────┘
```

## 技术决策

### 1. 底层框架选择

**决策**：使用Hermes Agent框架（https://github.com/NousResearch/hermes-agent）

**理由**：
- ✅ 已验证支持子智能体生成（delegate_tool.py）
- ✅ 支持身份文件（SOUL.md、AGENTS.md、MEMORY.md、USER.md）
- ✅ 优秀的记忆机制，让项目越来越清晰
- ✅ 支持桌面版（Hermes Desktop），未来可扩展
- ✅ 阻塞式+并发调用模式符合需求

### 2. 主智能体职责

**决策**：主智能体承担三项核心职责

- **任务编排** - 接收用户查询，分解任务，协调4个子智能体执行
- **对话管理** - 与用户对话，理解意图，调用子智能体获取答案
- **工作流引擎** - 执行预定义的工作流，子智能体作为工作流节点

### 3. 子智能体调用方式

**决策**：采用Hermes模式（阻塞式+并发）

**特点**：
- 主智能体等待所有子智能体完成
- 子智能体之间并发执行（max_concurrent_children: 4）
- 每个子智能体获得独立的对话上下文
- 扁平结构（max_depth: 1）

### 4. 目录结构策略

**决策**：保持现有workspace/和subagents/结构，集成Hermes配置

**理由**：
- 保持现有项目结构不变
- 主智能体和子智能体都是完整的智能体实体
- 清晰体现主从关系

### 5. 三库组织

**决策**：将knowledge/移入shared/knowledge/，三库统一

**变更**：
- `knowledge/` → `shared/knowledge/`
- `shared/operators/` 保持不变
- `shared/data/` 保持不变

### 6. orchestrator-core处理

**决策**：完全替换为Hermes的delegate_tool.py

**理由**：
- 用户明确要求"完全替换"
- 避免维护两套代码
- 充分利用Hermes的能力

## 目录结构

**重组后的完整目录结构**：

```
Ecological_env/
├── workspace/                    📁【主智能体配置区】
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── MEMORY.md
│   ├── IDENTITY.md
│   ├── USER.md
│   ├── TOOLS.md
│   ├── HEARTBEAT.md
│   ├── memory/                   📁 主智能体会话日志
│   └── skills/                   📁 主智能体技能包
│       └── orchestrator-core/    📦 保留用于迁移参考
│           ├── SKILL.md
│           └── scripts/
│
├── subagents/                    📁【子智能体独立工作区】
│   ├── multi-dimensional-data-perception-agent/  # 📦 多维数据感知 📊
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── MEMORY.md
│   │   ├── memory/               📁 子智能体会话日志
│   │   └── skills/
│   │       └── data-perception-core/
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               ├── data_acquisition.py
│   │               ├── data_cleaning.py
│   │               ├── time_alignment.py
│   │               ├── standardization.py
│   │               └── data_decomposition.py
│   │
│   ├── anomaly-detection-agent/    # 📦 异常检测 🔍
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── MEMORY.md
│   │   ├── memory/
│   │   └── skills/
│   │       └── anomaly-detection-core/
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               ├── operator_adapter.py
│   │               ├── anomaly_scorer.py
│   │               ├── pattern_recognizer.py
│   │               ├── violation_detector.py
│   │               └── confidence_evaluator.py
│   │
│   ├── rule-reasoning-agent/       # 📦 规则推理 ⚖️
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── MEMORY.md
│   │   ├── memory/
│   │   └── skills/
│   │       └── rule-reasoning-core/
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               ├── regulation_matcher.py
│   │               ├── process_validator.py
│   │               └── expert_reasoner.py
│   │
│   └── disposition-execution-agent/  # 📦 研判预警与处置 🚨
│       ├── AGENTS.md
│       ├── SOUL.md
│       ├── MEMORY.md
│       ├── memory/
│       └── skills/
│           └── disposition-execution-core/
│               ├── SKILL.md
│               └── scripts/
│                   ├── alert_classifier.py
│                   ├── consensus_engine.py
│                   └── work_order_generator.py
│
├── shared/                       📁【全局共享资源 - 三库一体】
│   ├── operators/                🔧 算子库
│   │   ├── statistical/
│   │   ├── ml/
│   │   ├── deep_learning/
│   │   └── specialized/
│   │
│   ├── data/                     📊 数据库
│   │   ├── real-time/
│   │   ├── historical/
│   │   ├── processed/
│   │   └── static/
│   │
│   ├── knowledge/                📚 知识库（从根目录移入）
│   │   ├── regulations/
│   │   ├── process_knowledge/
│   │   ├── violation_patterns/
│   │   └── expert_experience/
│   │
│   ├── configs/                  ⚙️ 配置层
│   │   ├── hermes_config.yaml
│   │   ├── llm_config.yaml
│   │   ├── subagent_registry.json
│   │   └── system_params.yaml
│   │
│   ├── models/                   🤖 模型层
│   ├── cache/                    💾 缓存层
│   └── outputs/                  📄 输出层
│
├── middleware/                   🌐 Flask中间件
├── stream/                       🌊 数据流模拟器
├── interfaces/                   🔌 标准化接口定义
├── scripts/                      🛠️ 全局工具脚本
├── logs/                         📝 日志系统
├── tests/                        🧪 测试目录
├── docs/                         📖 项目文档
├── .hermes/                      🆕 Hermes配置目录
│   └── config.yaml               Hermes主配置
│
├── CHANGELOG.md
├── CLAUDE.md
├── README.md
└── requirements.txt
```

## Hermes集成方式

### 配置文件

**.hermes/config.yaml（项目根目录）**：

```yaml
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
```

### 子智能体调用

```python
from hermes.tools import delegate_task

results = delegate_task(
    tasks=[
        {
            "agent": "multi-dimensional-data-perception-agent",
            "goal": "获取并预处理数据",
            "context": {...}
        },
        {
            "agent": "anomaly-detection-agent",
            "goal": "检测异常模式",
            "context": {...}
        },
        {
            "agent": "rule-reasoning-agent",
            "goal": "推理违规判定",
            "context": {...}
        },
        {
            "agent": "disposition-execution-agent",
            "goal": "生成预警和处置建议",
            "context": {...}
        }
    ],
    mode="parallel"
)
```

## 主智能体与子智能体交互

### 交互流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 用户查询 → 主智能体（workspace/）                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 主智能体意图识别（LLM驱动）                             │
│     • 理解用户需求                                           │
│     • 决定需要调用哪些子智能体                               │
│     • 分解任务                                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. delegate_task() - 并发调用4个子智能体                  │
│     • max_concurrent_children: 4                            │
│     • mode: parallel                                        │
│     • 每个子智能体获得独立上下文                              │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │多维数据 │    │异常检测 │    │规则推理 │    │研判处置 │
    │感知     │    │         │    │         │    │         │
    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 主智能体阻塞等待所有子智能体完成                         │
│     • 收集所有子智能体结果                                    │
│     • 整合结果                                               │
│     • 生成最终响应                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 返回结果给用户                                          │
└─────────────────────────────────────────────────────────────┘
```

### 子智能体独立上下文

每个子智能体获得：
- 独立的对话历史（无父智能体历史污染）
- 自己的task_id
- 受限的工具集
- 专注的系统提示
- 独立的记忆系统（MEMORY.md）

## 三库支撑机制

### 三库结构

```
┌─────────────────────────────────────────────────────────────┐
│                      shared/ 三库支撑                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  1. 算子库              │
│  │     └── specialized/         │
│  │         ├── constant_detector.py      (插瓶干扰)    │
│  │         ├── change_point_detector.py  (数据突变)    │
│  │         ├── smoothness_detector.py    (人工拟合)    │
│  │         └── forgery_detector.py       (恶意逃避)    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  2. 数据库                       │
│  │     ├── real-time/        (实时数据)                 │
│  │     ├── historical/       (历史数据)                 │
│  │     ├── processed/        (处理后数据)               │
│  │     └── static/           (静态参考数据)             │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  3. 知识库                     │
│  │     ├── regulations/            (法规库)             │
│  │     │   ├── 排放标准.md                              │
│  │     │   └── 水污染防治法.md                          │
│  │     ├── process_knowledge/      (工艺知识库)         │
│  │     │   └── 生化处理工艺.md                          │
│  │     ├── violation_patterns/     (违规模式库)         │
│  │     │   └── 典型违规模式.md                          │
│  │     └── expert_experience/      (专家经验库)         │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 访问模式

- **多维数据感知子智能体** → 访问 shared/data/
- **异常检测子智能体** → 访问 shared/operators/
- **规则推理子智能体** → 访问 shared/knowledge/
- **研判预警与处置执行子智能体** → 访问所有三库

## 记忆系统

### Hermes记忆机制

Hermes提供优秀的记忆机制：

- **MemoryManager** - 统一管理所有记忆提供者
- **跨会话记忆** - 持久化召回，让智能体"越来越清晰"
- **上下文隔离** - 通过`<memory-context>`标签隔离记忆内容
- **预取机制** - 每轮对话前自动召回相关记忆
- **同步写入** - 每轮对话后异步写入记忆

### 记忆文件

- **主智能体**：写入 `workspace/MEMORY.md`
- **子智能体**：写入 `subagents/*/MEMORY.md`
- **Hermes MemoryManager**：自动管理跨会话记忆

## 实施步骤

### 阶段1：Hermes框架集成（1-2天）

```
1. 创建 .hermes/ 目录和配置
   - 创建 .hermes/config.yaml
   - 配置模型、工具、记忆

2. 验证Hermes安装
   - 确认 D:\Hermes\hermes-agent\ 可用
   - 测试 delegate_tool.py 机制

3. 删除 orchestrator-core
   - 备份 workspace/skills/orchestrator-core/ 到参考目录
   - 移除旧的编排脚本
```

### 阶段2：目录结构重组（1天）

```
1. 移动 knowledge/ → shared/knowledge/
   - mv knowledge/ shared/knowledge/

2. 创建子智能体 memory/ 目录
   - mkdir subagents/*/memory/

3. 创建 interfaces/ 和 scripts/ 目录
   - mkdir interfaces/
   - mkdir scripts/
```

### 阶段3：文件清理（0.5天）

```
1. 删除过时专利文档
   - docs/专利.txt
   - docs/专利_实施例部分.txt
   - docs/专利_方法步骤部分.txt
   - docs/专利_系统架构部分_修正版.txt
   - docs/参专利.txt

2. 删除临时垃圾文件
   - .understand-anything/.trash-1781689450/
   - .understand-anything/tmp/

3. 归档过时计划文档
   - docs/superpowers/plans/2024-06-08-ui-redesign.md
   - docs/任务目标.md
```

### 阶段4：配置文件创建（0.5天）

```
1. 创建 .hermes/config.yaml
2. 创建 shared/configs/hermes_config.yaml
3. 更新子智能体配置
```

### 阶段5：测试验证（1天）

```
1. 验证主智能体启动
2. 验证子智能体调用
3. 验证三库访问
4. 验证记忆系统
```

### 阶段6：文档更新（0.5天）

```
1. 创建 docs/architecture.md
2. 更新 CLAUDE.md
3. 更新 README.md
4. 创建接口标准化文档
```

**总计**：约4-5天

## 验收标准

### 目录结构验收
- [ ] knowledge/ 已移入 shared/knowledge/
- [ ] 每个子智能体都有 memory/ 目录
- [ ] .hermes/ 目录和配置文件已创建
- [ ] orchestrator-core 已从主流程移除

### Hermes框架集成验收
- [ ] 主智能体可以启动并响应用户查询
- [ ] delegate_tool.py 可以成功调用4个子智能体
- [ ] 子智能体并发执行正常
- [ ] 主智能体阻塞等待所有子智能体完成

### 三库访问验收
- [ ] 多维数据感知子智能体可以访问 shared/data/
- [ ] 异常检测子智能体可以调用 shared/operators/
- [ ] 规则推理子智能体可以访问 shared/knowledge/
- [ ] 研判预警与处置执行子智能体可以访问所有三库

### 记忆系统验收
- [ ] 主智能体写入 workspace/MEMORY.md
- [ ] 子智能体写入各自的 subagents/*/MEMORY.md
- [ ] 跨会话记忆正常工作
- [ ] Hermes MemoryManager 正常运行

### 文档更新验收
- [ ] docs/architecture.md 已创建并反映新架构
- [ ] CLAUDE.md 已更新说明Hermes框架
- [ ] README.md 已更新目录结构
- [ ] 接口标准化文档完整

### 功能验收
- [ ] 用户查询可以正常处理
- [ ] 4个子智能体协调工作正常
- [ ] 三库支撑正常
- [ ] 预警和处置工单生成正常

## 风险与注意事项

### 风险

1. **Hermes依赖** - 项目将依赖外部Hermes框架
2. **学习曲线** - 团队需要熟悉Hermes的使用方式
3. **迁移风险** - orchestrator-core移除可能影响现有功能

### 注意事项

1. **备份重要** - 在删除orchestrator-core前做好备份
2. **渐进测试** - 每个阶段完成后进行充分测试
3. **文档同步** - 及时更新文档，保持与代码同步

## 未来扩展

### Hermes Desktop集成

未来可以通过Hermes Desktop提供图形界面：

```
Hermes Desktop
    └── 加载项目配置
        └── 主智能体（workspace/）
            └── 调用4个子智能体（subagents/）
                └── 访问三库（shared/）
```

### 功能扩展

1. **语音交互** - 通过Hermes Desktop的语音功能
2. **文件浏览器** - 直接在桌面端浏览项目文件
3. **实时监控** - 集成Grafana仪表板到桌面端

# Hermes 多智能体系统实现方案

## 目标

在 Hermes 框架中实现废水监测系统的多智能体架构：
```
用户 → FastAPI → Hermes API → 主智能体 → 4个子智能体 → 响应
```

## 当前状态

- ✓ Hermes API Server 运行正常 (8642)
- ✓ FastAPI 后端运行正常 (8000)
- ✓ LLM 连接正常 (ctgu-vlm)
- ✓ 基础对话功能正常
- ✗ 子智能体未集成

---

## 架构设计

### Hermes 中的多智能体实现方式

Hermes 框架支持通过 **Skills** 作为入口调用子智能体：

```
Hermes AIAgent (主)
    │
    ├─ Skill: data-perception       → 调用子智能体1
    ├─ Skill: anomaly-detection      → 调用子智能体2
    ├─ Skill: rule-reasoning         → 调用子智能体3
    └─ Skill: disposition-execution  → 调用子智能体4
```

### 两种子智能体调用方式

#### 方式 A：直接调用 Python 代码（快速，推荐）
- Skill 的 scripts 直接调用子智能体的 Python 函数
- 响应快，适合生产环境

#### 方式 B：子 AIAgent 实例（完整，复杂）
- 每个子智能体是完整的 AIAgent
- 有独立的 SOUL/AGENTS/MEMORY
- 需要 Hermeshome 配置

**建议：先用方式 A 快速验证，后续可升级到方式 B**

---

## 实现步骤

### 第一步：设置主智能体 HERMES_HOME

告诉 Hermes 你的主智能体配置在哪里：

**当前状态：** Hermes 使用 `D:/Hermes` 作为 HERMES_HOME

**需要改为：** `E:\project\Ecological_env\workspace`

### 第二步：创建技能目录结构

为每个子智能体创建 Hermes Skill 入口：

```
workspace/
├── config.yaml                      # Hermes 配置
├── SOUL.md                          # 主智能体身份
├── AGENTS.md                        # 主智能体规范
├── MEMORY.md                        # 主智能体记忆
└── skills/
    ├── data-perception/             # 多维数据感知技能
    │   ├── SKILL.md
    │   └── scripts/
    │       └── call_agent.py       # 调用子智能体1
    │
    ├── anomaly-detection/           # 异常检测技能
    │   ├── SKILL.md
    │   └── scripts/
    │       └── call_agent.py       # 调用子智能体2
    │
    ├── rule-reasoning/              # 规则推理技能
    │   ├── SKILL.md
    │   └── scripts/
    │       └── call_agent.py       # 调用子智能体3
    │
    └── disposition-execution/       # 研判处置技能
        ├── SKILL.md
        └── scripts/
            └── call_agent.py       # 调用子智能体4
```

### 第三步：编写 SKILL.md 文件

每个 SKILL.md 定义技能的接口和功能：

```markdown
# 多维数据感知

负责获取和预处理废水监测的多维时序数据。

## 功能

- 获取进水、出水数据
- 数据清洗和标准化
- 时序对齐
- 数据分解

## 输入

- time_range: 时间范围
- data_sources: 数据源列表

## 输出

- processed_data: 处理后的数据
- quality_metrics: 数据质量指标
```

### 第四步：编写调用脚本

```python
# skills/data-perception/scripts/call_agent.py
import sys
sys.path.append('../../subagents/multi-dimensional-data-perception-agent')

from scripts.data_acquisition import acquire_data
from scripts.data_cleaning import clean_data

def skill_function(time_range=None, data_sources=None):
    """调用多维数据感知子智能体"""
    data = acquire_data(time_range, data_sources)
    cleaned = clean_data(data)
    return {
        "processed_data": cleaned,
        "quality_metrics": {...}
    }
```

---

## 配置文件更新

### workspace/config.yaml

```yaml
# LLM 配置
model:
  base_url: "http://172.16.12.41:30000/v1"
  default: "ctgu-vlm"
  provider: "openai-api"

providers:
  openai-api:
    api_key: "sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f"
    base_url: "http://172.16.12.41:30000/v1"

# 技能配置（指向 workspace 内的 skills）
skills:
  external_dirs:
    - skills/data-perception
    - skills/anomaly-detection
    - skills/rule-reasoning
    - skills/disposition-execution

# 主智能体配置
agent:
  max_turns: 60
```

---

## Hermes API Server 配置更新

### 启动脚本更新

需要将 HERMES_HOME 指向 workspace：

```cmd
@echo off
set HERMES_HOME=E:\project\Ecological_env\workspace
set API_SERVER_KEY=admin123456
cd /d D:\Hermes\hermes-agent
python -m gateway.run
```

---

## 工作流程

### 用户查询的完整流程

```
1. 用户发送查询
   ↓
2. FastAPI 接收请求
   ↓
3. 调用 Hermes API Server (/v1/chat/completions)
   ↓
4. Hermes AIAgent 加载主智能体配置
   ├─ 读取 workspace/SOUL.md
   ├─ 读取 workspace/AGENTS.md
   └─ 加载 workspace/skills/ 中的技能
   ↓
5. LLM 决策需要哪些功能
   ↓
6. 调用相应技能（如 data-perception）
   ↓
7. Skill 调用子智能体代码
   ↓
8. 子智能体返回结果
   ↓
9. LLM 整合结果，生成响应
   ↓
10. 返回给 FastAPI
   ↓
11. 返回给用户
```

---

## 下一步行动

### 立即执行

1. **创建技能目录结构**
   - 在 workspace/ 下创建 skills/ 目录
   - 创建 4 个技能子目录

2. **编写 SKILL.md 模板**
   - 为每个技能创建 SKILL.md
   - 定义输入输出

3. **编写调用脚本**
   - 创建 call_agent.py 桥接脚本
   - 连接到子智能体代码

4. **更新配置**
   - 修改 workspace/config.yaml
   - 更新启动脚本

5. **测试**
   - 重启 Hermes API Server
   - 测试技能调用
   - 验证完整流程

---

## 预期效果

完成后，用户的查询会触发：

```json
{
  "content": "根据分析，进水 COD 浓度为 120 mg/L...",
  "decision_path": [...],
  "sub_agent_calls": [
    {"agent": "data-perception", "status": "success"},
    {"agent": "anomaly-detection", "status": "success"},
    {"agent": "rule-reasoning", "status": "success"}
  ],
  "data_sources": ["influent", "effluent"]
}
```

---

## 优势

- ✓ 保持原有子智能体架构
- ✓ 符合 Hermes 框架设计
- ✓ 清晰的职责分离
- ✓ 易于扩展和维护

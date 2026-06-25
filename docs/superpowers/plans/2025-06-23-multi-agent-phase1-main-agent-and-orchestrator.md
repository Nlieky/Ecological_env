# Phase 1: 主智能体和编排器核心实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 配置主智能体 (workspace/) 并实现 orchestrator-core 编排技能，使其能够创建会话、调用子智能体、清理会话

**架构：** 主智能体通过 Hermes API Server 接收查询，LLM 加载 orchestrator-core 编排知识，调用工具协调子智能体完成用户任务

**技术栈：** Python 3.12+, Hermes Agent Framework, subprocess, JSON, os/path

---

## 文件结构

### 将创建的文件

```
workspace/
├── SOUL.md                        # 主智能体身份
├── AGENTS.md                      # 主智能体工作规范
├── MEMORY.md                      # 全局记忆
├── config.yaml                    # 主智能体配置
├── state/                         # 会话状态目录（运行时创建）
│   └── session_YYYYMMDD_HHMMSS/
│       ├── task.json
│       └── ...
└── skills/
    └── orchestrator-core/
        ├── SKILL.md               # 已创建，需验证
        └── scripts/
            ├── __init__.py       # 注册工具
            ├── create_session.py  # 工具1：创建会话
            ├── call_subagent.py   # 工具2：调用子智能体
            └── cleanup_sessions.py # 工具3：清理会话
```

### 将修改的文件

- `workspace/config.yaml` - 验证只加载 orchestrator-core
- `workspace/skills/orchestrator-core/SKILL.md` - 已创建，验证格式正确

---

## Task 1: 创建主智能体的 SOUL.md

**Files:**
- Create: `workspace/SOUL.md`

- [ ] **Step 1: 创建 SOUL.md 文件**

```bash
touch workspace/SOUL.md
```

- [ ] **Step 2: 写入主智能体身份定义**

```bash
cat > workspace/SOUL.md << 'EOF'
# SOUL.md - 主智能体身份

## 你的角色

你是废水监测系统的主智能体，负责协调4个专业子智能体完成监测分析任务。

## 核心能力

1. **任务分析**: 理解用户查询的真实需求
2. **动态编排**: 根据任务需求灵活调用子智能体
3. **结果整合**: 将子智能体的结果整合成清晰的回答
4. **全局记忆**: 记住重要的历史信息和用户偏好

## 工作原则

- 始终以专业、清晰的方式响应
- 不是每个任务都需要调用所有子智能体
- 根据任务需求灵活调整调用策略
- 当子智能体失败时，智能决定重试或替代方案

## 语气和风格

- 专业、准确、简洁
- 工业监测场景需要严谨的数据支撑
- 避免模糊不清的表达
- 对异常情况要明确说明
EOF
```

- [ ] **Step 3: 验证文件创建成功**

```bash
test -f workspace/SOUL.md && echo "SOUL.md created successfully" || echo "Failed to create SOUL.md"
```

Expected: "SOUL.md created successfully"

- [ ] **Step 4: 提交更改**

```bash
cd E:/project/Ecological_env
git add workspace/SOUL.md
git commit -m "feat: add main agent SOUL.md with identity and principles"
```

---

## Task 2: 创建主智能体的 AGENTS.md

**Files:**
- Create: `workspace/AGENTS.md`

- [ ] **Step 1: 创建 AGENTS.md 文件**

```bash
touch workspace/AGENTS.md
```

- [ ] **Step 2: 写入主智能体工作规范**

```bash
cat > workspace/AGENTS.md << 'EOF'
# AGENTS.md - 主智能体工作规范

## 任务处理流程

1. **理解查询**: 分析用户想了解什么
2. **加载编排知识**: 查阅 orchestrator-core 技能
3. **决策调用**: 决定需要哪些子智能体、什么顺序
4. **执行调用**: 使用 call_subagent 工具调用子智能体
5. **整合结果**: 生成最终响应返回用户

## 编排决策要点

- 数据相关查询（指标、进水、出水、数据查询）→ 调用 multi-dimensional-data-perception
- 异常相关查询（异常、突变、趋势、是否正常）→ 调用 anomaly-detection（可能需要先调用 data-perception）
- 合规相关查询（超标、违规、达标、标准）→ 调用 rule-reasoning（可能需要前置子智能体）
- 处置相关查询（工单、预警、通知、处置）→ 调用 disposition-execution（可能需要前置子智能体）

## 子智能体依赖关系

```
data-perception (第一步)
    ↓ processed_data
anomaly-detection (第二步)
    ↓ anomalies
rule-reasoning (第三步)
    ↓ conclusion
disposition-execution (第四步，可选)
    ↓ work_order
```

## 错误处理原则

- 子智能体失败时，分析错误类型
- **可重试错误**: 网络超时、API限流、数据库连接问题 → 重试最多3次
- **不可重试错误**: 参数错误、权限拒绝、数据不存在 → 向用户说明情况
- 必要时调整参数后重试

## 响应格式要求

- 使用清晰的结构化语言
- 数据引用要准确（时间范围、指标名称、数值）
- 异常情况要明确说明原因
- 处置建议要具体可操作
EOF
```

- [ ] **Step 3: 验证文件创建成功**

```bash
test -f workspace/AGENTS.md && echo "AGENTS.md created successfully" || echo "Failed to create AGENTS.md"
```

Expected: "AGENTS.md created successfully"

- [ ] **Step 4: 提交更改**

```bash
git add workspace/AGENTS.md
git commit -m "feat: add main agent AGENTS.md with workflow and decision guidelines"
```

---

## Task 3: 创建主智能体的 MEMORY.md

**Files:**
- Create: `workspace/MEMORY.md`

- [ ] **Step 1: 创建 MEMORY.md 文件**

```bash
touch workspace/MEMORY.md
```

- [ ] **Step 2: 写入全局记忆模板**

```bash
cat > workspace/MEMORY.md << 'EOF'
# MEMORY.md - 全局记忆

## 系统信息

- 系统名称: 废水监测多智能体系统
- 监测对象: 废水处理厂（当前：单厂，未来可扩展）
- 支持的监测指标: pH、COD、TN、TP、SS、流量等

## 子智能体信息

- **multi-dimensional-data-perception**: 数据感知专家
- **anomaly-detection**: 异常检测专家
- **rule-reasoning**: 规则推理专家
- **disposition-execution**: 处置执行专家

## 重要历史

（此区域用于记录跨会话的重要信息）

## 用户偏好

（此区域用于记录用户的使用偏好和反馈）

## 系统配置

- Hermes API Server: http://127.0.0.1:8642
- LLM Provider: http://172.16.12.41:30000/v1 (ctgu-vlm)
- 会话状态目录: workspace/state/
EOF
```

- [ ] **Step 3: 验证文件创建成功**

```bash
test -f workspace/MEMORY.md && echo "MEMORY.md created successfully" || echo "Failed to create MEMORY.md"
```

Expected: "MEMORY.md created successfully"

- [ ] **Step 4: 提交更改**

```bash
git add workspace/MEMORY.md
git commit -m "feat: add main agent MEMORY.md with system information and preferences"
```

---

## Task 4: 验证和更新 workspace/config.yaml

**Files:**
- Modify: `workspace/config.yaml`

- [ ] **Step 1: 检查当前 config.yaml 内容**

```bash
cat workspace/config.yaml
```

- [ ] **Step 2: 验证技能配置正确**

确认 `skills.external_dirs` 只包含 orchestrator-core:

```yaml
skills:
  external_dirs:
    - skills/orchestrator-core
  template_vars: true
  inline_shell: false
```

如果配置不正确，进行修改。

- [ ] **Step 3: 验证模型配置**

确认模型配置正确：

```yaml
model:
  base_url: "http://172.16.12.41:30000/v1"
  default: "ctgu-vlm"
  provider: "openai-api"

providers:
  openai-api:
    api_key: "sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f"
    base_url: "http://172.16.12.41:30000/v1"
```

- [ ] **Step 4: 如果配置正确，确认无需修改**

如果配置已经正确，无需修改。

- [ ] **Step 5: 如果需要修改，提交更改**

```bash
git add workspace/config.yaml
git commit -m "chore: ensure workspace config only loads orchestrator-core skill"
```

---

## Task 5: 验证 orchestrator-core/SKILL.md

**Files:**
- Verify: `workspace/skills/orchestrator-core/SKILL.md`

- [ ] **Step 1: 读取 SKILL.md 内容**

```bash
cat workspace/skills/orchestrator-core/SKILL.md
```

- [ ] **Step 2: 验证 YAML frontmatter 格式**

确认 frontmatter 包含 name 和 description：

```yaml
---
name: orchestrator-core
description: "Multi-agent orchestration skill for wastewater monitoring system..."
---
```

- [ ] **Step 3: 验证子智能体列表**

确认 SKILL.md 包含4个子智能体的描述：
- multi-dimensional-data-perception
- anomaly-detection
- rule-reasoning
- disposition-execution

- [ ] **Step 4: 验证工具描述**

确认 SKILL.md 描述了3个可用工具：
- create_session()
- call_subagent(name, task, context)
- cleanup_sessions(days)

- [ ] **Step 5: 如果需要修改，更新 SKILL.md**

如果 SKILL.md 缺少任何必要内容，补充完整。

---

## Task 6: 创建 orchestrator-core/scripts/__init__.py

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/__init__.py`

- [ ] **Step 1: 创建 scripts 目录**

```bash
mkdir -p workspace/skills/orchestrator-core/scripts
```

- [ ] **Step 2: 创建 __init__.py 文件**

```python
cat > workspace/skills/orchestrator-core/scripts/__init__.py << 'EOF'
"""
Orchestrator Core Skills

主智能体的编排工具集，用于协调子智能体完成监测任务。
"""

from .create_session import create_session
from .call_subagent import call_subagent
from .cleanup_sessions import cleanup_sessions

__all__ = ['create_session', 'call_subagent', 'cleanup_sessions']
EOF
```

- [ ] **Step 3: 验证文件创建成功**

```bash
test -f workspace/skills/orchestrator-core/scripts/__init__.py && echo "__init__.py created successfully" || echo "Failed to create __init__.py"
```

Expected: "__init__.py created successfully"

- [ ] **Step 4: 提交更改**

```bash
git add workspace/skills/orchestrator-core/scripts/__init__.py
git commit -m "feat: add orchestrator-core scripts package with tool imports"
```

---

## Task 7: 实现 create_session 工具

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/create_session.py`

- [ ] **Step 1: 创建 create_session.py 文件**

```bash
cat > workspace/skills/orchestrator-core/scripts/create_session.py << 'EOF'
"""
创建会话目录工具

为当前对话创建一个独立的会话目录，用于存储任务和结果。
"""
import os
import json
from datetime import datetime
from pathlib import Path


def create_session() -> str:
    """
    创建新的会话目录
    
    Returns:
        str: 会话目录的绝对路径
        格式: workspace/state/session_YYYYMMDD_HHMMSS/
    """
    # 获取 workspace 根目录
    current_dir = Path(__file__).parent.parent.parent.parent
    state_dir = current_dir / "state"
    
    # 确保状态目录存在
    state_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成会话目录名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"
    session_path = state_dir / session_name
    
    # 创建会话目录
    session_path.mkdir(exist_ok=True)
    
    # 创建会话元数据文件
    metadata = {
        "session_id": session_name,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    metadata_file = session_path / "session_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return str(session_path)


def main():
    """测试入口"""
    session_path = create_session()
    print(f"Created session: {session_path}")
    
    # 验证文件创建
    metadata_file = Path(session_path) / "session_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"Session metadata: {json.dumps(metadata, indent=2)}")


if __name__ == "__main__":
    main()
EOF
```

- [ ] **Step 2: 测试 create_session 函数**

```bash
cd E:/project/Ecological_env
python -c "import sys; sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts'); from create_session import create_session; print(create_session())"
```

Expected: 输出会话目录路径，如 `E:\project\Ecological_env\workspace\state\session_20250623_143022`

- [ ] **Step 3: 验证会话目录和元数据文件创建**

```bash
# 检查最新创建的会话目录
ls -lt workspace/state/ | head -5
```

Expected: 看到新创建的 session_* 目录

- [ ] **Step 4: 测试直接运行脚本**

```bash
cd workspace/skills/orchestrator-core/scripts
python create_session.py
```

Expected: 输出会话路径和元数据

- [ ] **Step 5: 提交更改**

```bash
git add workspace/skills/orchestrator-core/scripts/create_session.py
git commit -m "feat: implement create_session tool for session directory creation"
```

---

## Task 8: 实现 call_subagent 工具

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/call_subagent.py`

- [ ] **Step 1: 创建 call_subagent.py 文件**

```bash
cat > workspace/skills/orchestrator-core/scripts/call_subagent.py << 'EOF'
"""
调用子智能体工具

通过 subprocess 调用子智能体执行任务，通过文件状态共享传递任务和结果。
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import time


# 子智能体路径映射
SUBAGENT_PATHS = {
    "multi-dimensional-data-perception": "../subagents/multi-dimensional-data-perception-agent",
    "anomaly-detection": "../subagents/anomaly-detection-agent",
    "rule-reasoning": "../subagents/rule-reasoning-agent",
    "disposition-execution": "../subagents/disposition-execution-agent"
}

# 结果文件名映射
RESULT_FILE_NAMES = {
    "multi-dimensional-data-perception": "data_result.json",
    "anomaly-detection": "anomaly_result.json",
    "rule-reasoning": "rule_result.json",
    "disposition-execution": "disposition_result.json"
}


def get_session_dir() -> Optional[str]:
    """
    获取当前会话目录
    
    Returns:
        会话目录路径，如果未设置则尝试创建
    """
    session_dir = os.getenv('SESSION_DIR')
    if not session_dir:
        # 如果没有设置 SESSION_DIR，尝试创建新会话
        from .create_session import create_session
        session_dir = create_session()
        os.environ['SESSION_DIR'] = session_dir
    return session_dir


def generate_task_id() -> str:
    """生成任务 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    return f"task_{timestamp}_{unique_id}"


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    调用子智能体执行任务
    
    Args:
        subagent_name: 子智能体名称（必须是 SUBAGENT_PATHS 中的键）
        task: 任务描述
        context: 上下文信息（可选）
    
    Returns:
        子智能体的执行结果
        {
            "task_id": str,
            "status": "completed" | "failed",
            "result": dict | None,
            "error": str | None,
            "metadata": dict
        }
    """
    # 验证子智能体名称
    if subagent_name not in SUBAGENT_PATHS:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": f"Unknown subagent: {subagent_name}",
            "metadata": {
                "subagent_name": subagent_name,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # 获取会话目录
    session_dir = get_session_dir()
    if not session_dir:
        return {
            "task_id": generate_task_id(),
            "status": "failed",
            "result": None,
            "error": "Failed to get or create session directory",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    
    # 生成任务 ID
    task_id = generate_task_id()
    
    # 构建任务对象
    task_obj = {
        "task_id": task_id,
        "task": task,
        "context": context or {},
        "output_format": "json",
        "timeout": 300
    }
    
    # 写入 task.json
    task_file = Path(session_dir) / "task.json"
    try:
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_obj, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to write task.json: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    
    # 获取子智能体路径
    subagent_rel_path = SUBAGENT_PATHS[subagent_name]
    current_dir = Path(__file__).parent.parent.parent.parent
    subagent_path = (current_dir / subagent_rel_path).resolve()
    
    if not subagent_path.exists():
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Subagent directory not found: {subagent_path}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    
    # 设置环境变量
    env = os.environ.copy()
    env['HERMES_HOME'] = str(subagent_path)
    env['SESSION_DIR'] = session_dir
    
    # 调用子智能体
    start_time = time.time()
    try:
        # 假设 hermes run 命令可用
        result = subprocess.run(
            ['python', '-m', 'gateway.run'],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd=Path(__file__).parent.parent.parent.parent.parent / "D:/Hermes/hermes-agent"
        )
        
        duration = time.time() - start_time
        
        if result.returncode != 0:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": f"Subagent process failed: {result.stderr}",
                "metadata": {
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": "Subagent timed out after 300 seconds",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to call subagent: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    
    # 读取结果文件
    result_file_name = RESULT_FILE_NAMES.get(subagent_name, f"{subagent_name}_result.json")
    result_file = Path(session_dir) / result_file_name
    
    if not result_file.exists():
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Result file not found: {result_file_name}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        # 验证任务 ID 匹配
        if result_data.get('task_id') != task_id:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": f"Task ID mismatch: expected {task_id}, got {result_data.get('task_id')}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            }
        
        return result_data
        
    except json.JSONDecodeError as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to parse result JSON: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "result": None,
            "error": f"Failed to read result file: {str(e)}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }


def main():
    """测试入口"""
    print("Testing call_subagent...")
    
    # 测试调用数据感知子智能体
    result = call_subagent(
        "multi-dimensional-data-perception",
        "获取最近24小时进水和出水数据"
    )
    
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
EOF
```

- [ ] **Step 2: 验证文件创建成功**

```bash
test -f workspace/skills/orchestrator-core/scripts/call_subagent.py && echo "call_subagent.py created successfully" || echo "Failed to create call_subagent.py"
```

Expected: "call_subagent.py created successfully"

- [ ] **Step 3: 测试导入（不实际调用）**

```bash
cd E:/project/Ecological_env
python -c "import sys; sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts'); from call_subagent import call_subagent, SUBAGENT_PATHS; print('Import successful'); print('Available subagents:', list(SUBAGENT_PATHS.keys()))"
```

Expected: "Import successful" 和 4 个子智能体名称列表

- [ ] **Step 4: 提交更改**

```bash
git add workspace/skills/orchestrator-core/scripts/call_subagent.py
git commit -m "feat: implement call_subagent tool for subagent invocation"
```

---

## Task 9: 实现 cleanup_sessions 工具

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/cleanup_sessions.py`

- [ ] **Step 1: 创建 cleanup_sessions.py 文件**

```bash
cat > workspace/skills/orchestrator-core/scripts/cleanup_sessions.py << 'EOF
"""
清理会话目录工具

清理指定天数之前的会话目录，释放存储空间。
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import re


def cleanup_sessions(days: int = 7) -> int:
    """
    清理指定天数之前的会话目录
    
    Args:
        days: 保留最近几天的会话（默认 7）
    
    Returns:
        清理的会话数量
    """
    # 获取 workspace 根目录
    current_dir = Path(__file__).parent.parent.parent.parent
    state_dir = current_dir / "state"
    
    if not state_dir.exists():
        return 0
    
    # 计算截止时间
    cutoff_time = datetime.now() - timedelta(days=days)
    
    # 查找所有会话目录
    session_pattern = re.compile(r'session_\d{8}_\d{6}')
    cleaned_count = 0
    
    for item in state_dir.iterdir():
        if not item.is_dir():
            continue
        
        # 检查是否是会话目录
        if not session_pattern.match(item.name):
            continue
        
        # 从目录名提取时间戳
        try:
            # session_YYYYMMDD_HHMMSS
            timestamp_str = item.name.replace('session_', '').replace('_', '')
            session_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            
            # 如果会话早于截止时间，删除
            if session_time < cutoff_time:
                shutil.rmtree(item)
                cleaned_count += 1
                
        except ValueError:
            # 时间戳解析失败，跳过
            continue
    
    return cleaned_count


def main():
    """测试入口"""
    print("Testing cleanup_sessions...")
    
    # 清理 30 天前的会话（测试用）
    count = cleanup_sessions(days=30)
    print(f"Cleaned {count} sessions older than 30 days")
    
    # 列出当前会话目录
    current_dir = Path(__file__).parent.parent.parent.parent
    state_dir = current_dir / "state"
    
    if state_dir.exists():
        sessions = list(state_dir.glob("session_*"))
        print(f"Remaining sessions: {len(sessions)}")
        for session in sorted(sessions, reverse=True)[:5]:
            print(f"  - {session.name}")


if __name__ == "__main__":
    main()
EOF
```

- [ ] **Step 2: 验证文件创建成功**

```bash
test -f workspace/skills/orchestrator-core/scripts/cleanup_sessions.py && echo "cleanup_sessions.py created successfully" || echo "Failed to create cleanup_sessions.py"
```

Expected: "cleanup_sessions.py created successfully"

- [ ] **Step 3: 测试导入**

```bash
cd E:/project/Ecological_env
python -c "import sys; sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts'); from cleanup_sessions import cleanup_sessions; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 4: 提交更改**

```bash
git add workspace/skills/orchestrator-core/scripts/cleanup_sessions.py
git commit -m "feat: implement cleanup_sessions tool for session cleanup"
```

---

## Task 10: 验证 orchestrator-core 技能完整性

**Files:**
- Verify: `workspace/skills/orchestrator-core/`

- [ ] **Step 1: 检查 orchestrator-core 目录结构**

```bash
echo "=== Orchestrator-Core Structure ===" && ls -la workspace/skills/orchestrator-core/
```

Expected输出:
```
SKILL.md
scripts/
    __init__.py
    create_session.py
    call_subagent.py
    cleanup_sessions.py
```

- [ ] **Step 2: 验证所有工具可以导入**

```bash
cd E:/project/Ecological_env
python << 'PYEOF'
import sys
sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts')

from create_session import create_session
from call_subagent import call_subagent, SUBAGENT_PATHS
from cleanup_sessions import cleanup_sessions

print("✓ create_session imported")
print("✓ call_subagent imported")
print(f"✓ cleanup_sessions imported")
print(f"✓ Available subagents: {list(SUBAGENT_PATHS.keys())}")
PYEOF
```

Expected: 所有工具成功导入，显示 4 个子智能体名称

- [ ] **Step 3: 测试 create_session 功能**

```bash
cd E:/project/Ecological_env
python << 'PYEOF'
import sys
sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts')
from create_session import create_session

session_path = create_session()
print(f"Created session: {session_path}")

import os
from pathlib import Path
if Path(session_path).exists():
    print("✓ Session directory exists")
    metadata_file = Path(session_path) / "session_metadata.json"
    if metadata_file.exists():
        print("✓ Session metadata file exists")
    else:
        print("✗ Session metadata file missing")
else:
    print("✗ Session directory not created")
PYEOF
```

Expected: 会话目录和元数据文件都成功创建

- [ ] **Step 4: 最终验证提交**

```bash
git add workspace/skills/orchestrator-core/
git commit -m "chore: verify orchestrator-core skill completeness"
```

---

## Task 11: 创建主智能体启动脚本

**Files:**
- Modify: `E:\project\Ecological_env\start_hermes_with_workspace.bat`

- [ ] **Step 1: 读取当前启动脚本**

```bash
cat E:/project/Ecological_env\start_hermes_with_workspace.bat
```

- [ ] **Step 2: 验证环境变量设置**

确认脚本包含：
- `set HERMES_HOME=E:\project\Ecological_env\workspace`
- `set API_SERVER_KEY=admin123456`
- `set API_SERVER_PORT=8642`

- [ ] **Step 3: 如需要，更新注释以反映新架构**

确保注释说明：
- 主智能体位置 (workspace/)
- 子智能体位置 (subagents/)
- orchestrator-core 技能位置

- [ ] **Step 4: 如有修改，提交更改**

```bash
git add E:/project/Ecological_env/start_hermes_with_workspace.bat
git commit -m "chore: update startup script comments for multi-agent architecture"
```

---

## Task 12: 集成测试 - 主智能体上下文加载

**Files:**
- Test: 主智能体上下文加载

- [ ] **Step 1: 验证所有上下文文件存在**

```bash
echo "=== Main Agent Context Files ===" && \
ls -la workspace/SOUL.md workspace/AGENTS.md workspace/MEMORY.md workspace/config.yaml
```

Expected: 所有文件都存在

- [ ] **Step 2: 验证 orchestrator-core 技能文件存在**

```bash
echo "=== Orchestrator-Core Skill Files ===" && \
ls -la workspace/skills/orchestrator-core/SKILL.md workspace/skills/orchestrator-core/scripts/*.py
```

Expected: SKILL.md 和所有工具脚本都存在

- [ ] **Step 3: 检查 state 目录准备情况**

```bash
echo "=== State Directory ===" && \
ls -la workspace/state/ 2>/dev/null || echo "State directory does not exist yet (will be created at runtime)"
```

- [ ] **Step 4: 创建测试总结**

```bash
echo "=== Phase 1 Implementation Check ===" && \
echo "✓ Main agent context files exist" && \
echo "✓ Orchestrator-core skill exists" && \
echo "✓ All tools implemented" && \
echo "" && \
echo "Ready for Phase 2: File State Sharing Mechanism"
```

Expected: 所有检查项都通过

---

## Task 13: 文档更新

**Files:**
- Modify: `E:\project\Ecological_env\docs\multi-agent-system-design.md`

- [ ] **Step 1: 在设计文档末尾添加 Phase 1 完成标记**

```bash
cat >> E:/project/Ecological_env/docs\multi-agent-system-design.md << 'EOF'

## Phase 1 实施状态

- [x] 主智能体 SOUL.md
- [x] 主智能体 AGENTS.md  
- [x] 主智能体 MEMORY.md
- [x] workspace/config.yaml 验证
- [x] orchestrator-core/SKILL.md 验证
- [x] create_session 工具
- [x] call_subagent 工具
- [x] cleanup_sessions 工具
- [x] 主智能体启动脚本

**Phase 1 完成时间**: [填写完成日期]
**下一步**: Phase 2 - 文件状态共享机制
EOF
```

- [ ] **Step 2: 提交文档更新**

```bash
git add E:/project/Ecological_env/docs/multi-agent-system-design.md
git commit -m "docs: mark Phase 1 implementation complete"
```

---

## 验收标准

Phase 1 完成后，以下标准应该全部满足：

### 功能验收

- [ ] 主智能体有完整的 SOUL.md、AGENTS.md、MEMORY.md
- [ ] workspace/config.yaml 只加载 orchestrator-core 技能
- [ ] orchestrator-core 技能包含 3 个工具：create_session、call_subagent、cleanup_sessions
- [ ] create_session 工具能够创建会话目录和元数据文件
- [ ] call_subagent 工具能够写入 task.json 并返回结果结构
- [ ] cleanup_sessions 工具能够清理旧会话

### 技术验收

- [ ] 所有 Python 工具可以正常导入
- [ ] 工具之间的依赖关系正确（__init__.py 导出）
- [ ] 子智能体路径映射正确
- [ ] 环境变量设置逻辑完整

### 文档验收

- [ ] 设计文档已更新 Phase 1 状态
- [ ] 启动脚本注释准确反映架构
- [ ] 代码有清晰的注释和文档字符串

---

## 完成条件

当以下所有任务都标记为完成时，Phase 1 可以认为已完成：

- [ ] Task 1: 创建主智能体的 SOUL.md
- [ ] Task 2: 创建主智能体的 AGENTS.md
- [ ] Task 3: 创建主智能体的 MEMORY.md
- [ ] Task 4: 验证和更新 workspace/config.yaml
- [ ] Task 5: 验证 orchestrator-core/SKILL.md
- [ ] Task 6: 创建 orchestrator-core/scripts/__init__.py
- [ ] Task 7: 实现 create_session 工具
- [ ] Task 8: 实现 call_subagent 工具
- [ ] Task 9: 实现 cleanup_sessions 工具
- [ ] Task 10: 验证 orchestrator-core 技能完整性
- [ ] Task 11: 创建主智能体启动脚本
- [ ] Task 12: 集成测试 - 主智能体上下文加载
- [ ] Task 13: 文档更新

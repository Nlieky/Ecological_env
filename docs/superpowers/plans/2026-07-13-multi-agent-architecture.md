# 多智能体底层架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于Hermes Agent框架实现废水监测系统的多智能体底层架构，支持主智能体通过skill调用子智能体

**Architecture:** 同进程+逻辑隔离架构，主智能体和子智能体都是AIAgent实例，通过orchestrator-core的call_subagent工具进行通信

**Tech Stack:** Python 3.12, Hermes Agent框架, FastAPI

---

## 文件结构

本计划将创建和修改以下文件：

### 创建的新文件：
1. `shared/framework/hermes_agent/agent/identity_loader.py` - 身份文件加载器（支持自定义路径）
2. `workspace/skills/orchestrator-core/SKILL.md` - 编排器核心技能定义
3. `workspace/skills/orchestrator-core/scripts/subagent_tools.py` - 子智能体调用工具
4. `workspace/skills/orchestrator-core/scripts/subagent_manager.py` - 子智能体实例管理器
5. `tests/unit/test_subagent_manager.py` - 子智能体管理器测试
6. `tests/unit/test_subagent_tools.py` - 子智能体工具测试

### 修改的现有文件：
1. `shared/framework/hermes_agent/run_agent.py` - 添加identity_path参数支持
2. `shared/framework/hermes_agent/agent/agent_init.py` - 处理identity_path参数
3. `shared/framework/hermes_agent/agent/prompt_builder.py` - 修改身份文件加载逻辑
4. `shared/framework/hermes_agent/agent/system_prompt.py` - 使用自定义身份路径

---

## Task 1: 创建身份文件加载器（支持自定义路径）

**Files:**
- Create: `shared/framework/hermes_agent/agent/identity_loader.py`
- Test: `tests/unit/test_identity_loader.py`

- [ ] **Step 1: 创建身份文件加载器模块**

```python
# shared/framework/hermes_agent/agent/identity_loader.py
"""身份文件加载器 - 支持从自定义路径加载身份文件"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 身份文件列表（与hermes_constants保持一致）
IDENTITY_FILES = [
    "IDENTITY.md",    # 身份卡片
    "SOUL.md",        # 身份和个性
    "AGENTS.md",      # 工作区规范
    "MEMORY.md",      # 长期记忆
    "USER.md",        # 用户信息
    "TOOLS.md",       # 工具配置
    "HEARTBEAT.md"    # 周期性任务
]


def load_identity_files_from_path(identity_path: Path) -> Optional[str]:
    """从指定路径加载所有身份文件并组合成提示

    Args:
        identity_path: 身份文件所在目录路径

    Returns:
        组合后的身份文件内容，如果没有找到任何文件则返回 None
    """
    if not identity_path.exists():
        logger.debug(f"Identity path does not exist: {identity_path}")
        return None

    parts = []
    for filename in IDENTITY_FILES:
        file_path = identity_path / filename
        if not file_path.exists():
            logger.debug(f"Identity file not found: {file_path}")
            continue

        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            parts.append(f"## {filename}\n\n{content}")
        except Exception as e:
            logger.debug(f"Could not read identity file {file_path}: {e}")

    if not parts:
        return None

    return "\n\n".join(parts)


def load_single_identity_file(identity_path: Path, filename: str) -> Optional[str]:
    """从指定路径加载单个身份文件

    Args:
        identity_path: 身份文件所在目录路径
        filename: 要加载的文件名

    Returns:
        文件内容，如果文件不存在则返回 None
    """
    file_path = identity_path / filename
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8").strip()
        return content if content else None
    except Exception as e:
        logger.debug(f"Could not read identity file {file_path}: {e}")
        return None


def resolve_identity_path(identity_path: str | Path | None, project_root: Path) -> Path:
    """解析身份文件路径

    Args:
        identity_path: 身份文件路径（相对或绝对）
        project_root: 项目根目录

    Returns:
        解析后的绝对路径
    """
    if not identity_path:
        return project_root / "workspace"

    identity_path = Path(identity_path)
    if identity_path.is_absolute():
        return identity_path

    # 相对路径：相对于项目根目录
    return project_root / identity_path
```

- [ ] **Step 2: 创建身份文件加载器测试**

```python
# tests/unit/test_identity_loader.py
"""测试身份文件加载器"""

import pytest
from pathlib import Path
from agent.identity_loader import (
    load_identity_files_from_path,
    load_single_identity_file,
    resolve_identity_path,
    IDENTITY_FILES
)


def test_resolve_identity_path_absolute():
    """测试解析绝对路径"""
    path = resolve_identity_path("/absolute/path/to/workspace", Path("/project"))
    assert path == Path("/absolute/path/to/workspace")


def test_resolve_identity_path_relative():
    """测试解析相对路径"""
    path = resolve_identity_path("workspace", Path("/project"))
    assert path == Path("/project/workspace")


def test_resolve_identity_path_none():
    """测试解析空路径（默认workspace）"""
    path = resolve_identity_path(None, Path("/project"))
    assert path == Path("/project/workspace")


def test_load_identity_files_from_nonexistent_path():
    """测试从不存在的路径加载身份文件"""
    result = load_identity_files_from_path(Path("/nonexistent/path"))
    assert result is None


def test_load_single_identity_file(tmp_path):
    """测试加载单个身份文件"""
    # 创建测试文件
    test_file = tmp_path / "SOUL.md"
    test_file.write_text("# Test SOUL Content")

    content = load_single_identity_file(tmp_path, "SOUL.md")
    assert content == "# Test SOUL Content"


def test_load_single_identity_file_nonexistent(tmp_path):
    """测试加载不存在的身份文件"""
    content = load_single_identity_file(tmp_path, "NONEXISTENT.md")
    assert content is None


def test_load_identity_files_from_path_multiple_files(tmp_path):
    """测试从路径加载多个身份文件"""
    # 创建测试文件
    (tmp_path / "SOUL.md").write_text("# SOUL Content")
    (tmp_path / "AGENTS.md").write_text("# AGENTS Content")
    (tmp_path / "MEMORY.md").write_text("# MEMORY Content")

    result = load_identity_files_from_path(tmp_path)

    assert result is not None
    assert "## SOUL.md" in result
    assert "# SOUL Content" in result
    assert "## AGENTS.md" in result
    assert "# AGENTS Content" in result
    assert "## MEMORY.md" in result
    assert "# MEMORY Content" in result
```

- [ ] **Step 3: 运行测试验证功能**

```bash
cd E:/project/Ecological_env
python -m pytest tests/unit/test_identity_loader.py -v
```

预期输出：
```
collected 8 items

tests/unit/test_identity_loader.py::test_resolve_identity_path_absolute PASSED
tests/unit/test_identity_loader.py::test_resolve_identity_path_relative PASSED
tests/unit/test_identity_loader.py::test_resolve_identity_path_none PASSED
tests/unit/test_identity_loader.py::test_load_identity_files_from_nonexistent_path PASSED
tests/unit/test_identity_loader.py::test_load_single_identity_file PASSED
tests/unit/test_identity_loader.py::test_load_single_identity_file_nonexistent PASSED
tests/unit/test_identity_loader.py::test_load_identity_files_from_path_multiple_files PASSED

8 passed in 0.15s
```

- [ ] **Step 4: 提交代码**

```bash
git add shared/framework/hermes_agent/agent/identity_loader.py tests/unit/test_identity_loader.py
git commit -m "feat: add identity file loader with custom path support"
```

---

## Task 2: 修改AIAgent支持identity_path参数

**Files:**
- Modify: `shared/framework/hermes_agent/run_agent.py:343-413`
- Modify: `shared/framework/hermes_agent/agent/agent_init.py:23-200`
- Test: `tests/unit/test_ai_agent_identity_path.py`

- [ ] **Step 1: 修改run_agent.py添加identity_path参数**

找到 `class AIAgent` 的 `__init__` 方法（约343行），添加identity_path参数：

```python
# 在 run_agent.py 的 __init__ 方法中添加 identity_path 参数
def __init__(
    self,
    base_url: str = None,
    api_key: str = None,
    provider: str = None,
    api_mode: str = None,
    acp_command: str = None,
    acp_args: list[str] | None = None,
    command: str = None,
    args: list[str] | None = None,
    model: str = "",
    max_iterations: int = 90,
    tool_delay: float = 1.0,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    save_trajectories: bool = False,
    verbose_logging: bool = False,
    quiet_mode: bool = False,
    tool_progress_mode: str = "all",
    ephemeral_system_prompt: str = None,
    log_prefix_chars: int = 100,
    log_prefix: str = "",
    providers_allowed: List[str] = None,
    providers_ignored: List[str] = None,
    providers_order: List[str] = None,
    provider_sort: str = None,
    provider_require_parameters: bool = False,
    provider_data_collection: str = None,
    openrouter_min_coding_score: Optional[float] = None,
    session_id: str = None,
    tool_progress_callback: callable = None,
    tool_start_callback: callable = None,
    tool_complete_callback: callable = None,
    thinking_callback: callable = None,
    reasoning_callback: callable = None,
    clarify_callback: callable = None,
    step_callback: callable = None,
    stream_delta_callback: callable = None,
    interim_assistant_callback: callable = None,
    tool_gen_callback: callable = None,
    status_callback: callable = None,
    notice_callback: callable = None,
    notice_clear_callback: callable = None,
    max_tokens: int = None,
    reasoning_config: Dict[str, Any] = None,
    service_tier: str = None,
    request_overrides: Dict[str, Any] = None,
    prefill_messages: List[Dict[str, Any]] = None,
    platform: str = None,
    user_id: str = None,
    user_id_alt: str = None,
    user_name: str = None,
    chat_id: str = None,
    chat_name: str = None,
    chat_type: str = None,
    thread_id: str = None,
    gateway_session_key: str = None,
    skip_context_files: bool = False,
    load_soul_identity: bool = False,
    skip_memory: bool = False,
    session_db=None,
    parent_session_id: str = None,
    iteration_budget: "IterationBudget" = None,
    fallback_model: Dict[str, Any] = None,
    credential_pool=None,
    checkpoints_enabled: bool = False,
    checkpoint_max_snapshots: int = 20,
    checkpoint_max_total_size_mb: int = 500,
    checkpoint_max_file_size_mb: int = 10,
    pass_session_id: bool = False,
    identity_path: str | Path = None,  # 新增：身份文件路径
):
```

- [ ] **Step 2: 修改agent_init.py处理identity_path参数**

```python
# 在 agent_init.py 的 init_agent 函数中添加 identity_path 参数
def init_agent(
    agent: "AIAgent",
    base_url: str = None,
    api_key: str = None,
    provider: str = None,
    api_mode: str = None,
    acp_command: str = None,
    acp_args: list[str] | None = None,
    command: str = None,
    args: list[str] | None = None,
    model: str = "",
    max_iterations: int = 90,
    tool_delay: float = 1.0,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    save_trajectories: bool = False,
    verbose_logging: bool = False,
    quiet_mode: bool = False,
    tool_progress_mode: str = "all",
    ephemeral_system_prompt: str = None,
    log_prefix_chars: int = 100,
    log_prefix: str = "",
    session_id: str = None,
    tool_progress_callback: callable = None,
    tool_start_callback: callable = None,
    tool_complete_callback: callable = None,
    thinking_callback: callable = None,
    reasoning_callback: callable = None,
    clarify_callback: callable = None,
    step_callback: callable = None,
    stream_delta_callback: callable = None,
    interim_assistant_callback: callable = None,
    tool_gen_callback: callable = None,
    status_callback: callable = None,
    notice_callback: callable = None,
    notice_clear_callback: callable = None,
    max_tokens: int = None,
    reasoning_config: Dict[str, Any] = None,
    service_tier: str = None,
    request_overrides: Dict[str, Any] = None,
    prefill_messages: List[Dict[str, Any]] = None,
    platform: str = None,
    user_id: str = None,
    user_id_alt: str = None,
    user_name: str = None,
    chat_id: str = None,
    chat_name: str = None,
    chat_type: str = None,
    thread_id: str = None,
    gateway_session_key: str = None,
    skip_context_files: bool = False,
    load_soul_identity: bool = False,
    skip_memory: bool = False,
    session_db=None,
    parent_session_id: str = None,
    iteration_budget: "IterationBudget" = None,
    fallback_model: Dict[str, Any] = None,
    credential_pool=None,
    checkpoints_enabled: bool = False,
    checkpoint_max_snapshots: int = 20,
    checkpoint_max_total_size_mb: int = 500,
    checkpoint_max_file_size_mb: int = 10,
    pass_session_id: bool = False,
    identity_path: str | Path = None,  # 新增：身份文件路径
):
    # ... 现有代码 ...

    # 处理identity_path参数
    from pathlib import Path
    import sys

    # 确定项目根目录
    if hasattr(agent, '_project_root'):
        project_root = Path(agent._project_root)
    else:
        # 默认使用当前工作目录的父目录
        project_root = Path.cwd()

    # 解析identity_path为绝对路径
    if identity_path:
        from agent.identity_loader import resolve_identity_path
        agent._identity_path = resolve_identity_path(identity_path, project_root)
    else:
        agent._identity_path = None

    # ... 继续现有代码 ...
```

- [ ] **Step 3: 修改run_agent.py的__init__方法转发参数**

在run_agent.py的__init__方法中，将identity_path参数传递给init_agent：

```python
# 在 run_agent.py 的 __init__ 方法末尾，调用 init_agent 的地方
from agent.agent_init import init_agent
init_agent(
    self,
    base_url=base_url,
    api_key=api_key,
    provider=provider,
    # ... 其他现有参数 ...
    pass_session_id=pass_session_id,
    identity_path=identity_path,  # 新增：传递identity_path参数
)
```

- [ ] **Step 4: 修改system_prompt.py使用自定义identity_path**

```python
# 在 agent/system_prompt.py 中，修改 _identity_loaded 部分
# 在 build_system_prompt_parts 函数中添加对identity_path的支持

def build_system_prompt_parts(agent: Any, system_message: Optional[str] = None) -> Dict[str, str]:
    """Assemble the system prompt as three ordered parts."""
    _r = _ra()
    stable_parts: List[str] = []

    # Try SOUL.md as primary identity unless the caller explicitly skipped it.
    _soul_loaded = False
    if agent.load_soul_identity or not agent.skip_context_files:
        # 优先加载完整的身份文件集合
        if hasattr(agent, '_identity_path') and agent._identity_path:
            # 使用自定义identity_path
            from agent.identity_loader import load_identity_files_from_path
            _identity_content = load_identity_files_from_path(agent._identity_path)
            if _identity_content:
                stable_parts.append(_identity_content)
                _soul_loaded = True

        # 回退到仅 SOUL.md
        if not _soul_loaded:
            _soul_content = _r.load_soul_md()
            if _soul_content:
                stable_parts.append(_soul_content)
                _soul_loaded = True

    # ... 继续现有代码 ...
```

- [ ] **Step 5: 创建AIAgent identity_path测试**

```python
# tests/unit/test_ai_agent_identity_path.py
"""测试AIAgent的identity_path参数"""

import pytest
from pathlib import Path
from run_agent import AIAgent
import tempfile
import shutil


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = Path(tempfile.mkdtemp())
    # 创建测试身份文件
    (temp_dir / "IDENTITY.md").write_text("# Test Identity")
    (temp_dir / "SOUL.md").write_text("# Test SOUL")
    (temp_dir / "AGENTS.md").write_text("# Test AGENTS")
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_ai_agent_with_identity_path(temp_workspace, monkeypatch):
    """测试AIAgent使用identity_path参数"""
    # 设置必要的环境变量
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    # 创建使用identity_path的AIAgent
    agent = AIAgent(
        model="gpt-4",
        identity_path=str(temp_workspace),
        load_soul_identity=True,
        skip_context_files=True,  # 跳过其他上下文文件
    )

    # 验证identity_path被正确设置
    assert agent._identity_path == temp_workspace


def test_ai_agent_without_identity_path(monkeypatch):
    """测试AIAgent不使用identity_path参数"""
    # 设置必要的环境变量
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    # 创建不使用identity_path的AIAgent
    agent = AIAgent(
        model="gpt-4",
        load_soul_identity=False,
        skip_context_files=True,
    )

    # 验证identity_path为None
    assert agent._identity_path is None


def test_ai_agent_identity_path_relative(monkeypatch, temp_workspace):
    """测试AIAgent使用相对路径"""
    # 设置必要的环境变量
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    # 创建使用相对路径的AIAgent
    agent = AIAgent(
        model="gpt-4",
        identity_path=temp_workspace.name,  # 相对路径
        load_soul_identity=True,
        skip_context_files=True,
    )

    # 验证identity_path被解析为绝对路径
    assert agent._identity_path.is_absolute()
```

- [ ] **Step 6: 运行测试验证功能**

```bash
cd E:/project/Ecological_env
python -m pytest tests/unit/test_ai_agent_identity_path.py -v
```

预期输出：
```
collected 3 items

tests/unit/test_ai_agent_identity_path.py::test_ai_agent_with_identity_path PASSED
tests/unit/test_ai_agent_identity_path.py::test_ai_agent_without_identity_path PASSED
tests/unit/test_ai_agent_identity_path.py::test_ai_agent_identity_path_relative PASSED

3 passed in 2.5s
```

- [ ] **Step 7: 提交代码**

```bash
git add shared/framework/hermes_agent/run_agent.py shared/framework/hermes_agent/agent/agent_init.py shared/framework/hermes_agent/agent/system_prompt.py tests/unit/test_ai_agent_identity_path.py
git commit -m "feat: add identity_path parameter support to AIAgent"
```

---

## Task 3: 实现子智能体管理器

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/subagent_manager.py`
- Test: `tests/unit/test_subagent_manager.py`

- [ ] **Step 1: 创建子智能体管理器**

```python
# workspace/skills/orchestrator-core/scripts/subagent_manager.py
"""子智能体实例管理器

负责创建、管理和销毁子智能体实例
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SubagentManager:
    """子智能体实例管理器

    管理所有子智能体的生命周期，包括创建、获取和销毁
    """

    # 子智能体配置
    SUBAGENT_CONFIGS = {
        "multi-dimensional-data-perception-agent": {
            "path": "subagents/multi-dimensional-data-perception-agent",
            "description": "多维数据感知子智能体"
        },
        "anomaly-detection-agent": {
            "path": "subagents/anomaly-detection-agent",
            "description": "异常检测子智能体"
        },
        "rule-reasoning-agent": {
            "path": "subagents/rule-reasoning-agent",
            "description": "规则推理子智能体"
        },
        "disposition-execution-agent": {
            "path": "subagents/disposition-execution-agent",
            "description": "研判预警与处置执行子智能体"
        }
    }

    def __init__(self, project_root: Path | str = None):
        """初始化子智能体管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.subagents: Dict[str, object] = {}
        self._initialized = False

    def create_subagents(self, model: str = None, base_url: str = None, api_key: str = None):
        """创建所有子智能体实例

        Args:
            model: LLM模型名称
            base_url: API基础URL
            api_key: API密钥
        """
        if self._initialized:
            logger.warning("Subagents already initialized, skipping")
            return

        try:
            from run_agent import AIAgent

            for name, config in self.SUBAGENT_CONFIGS.items():
                try:
                    identity_path = self.project_root / config["path"]

                    # 验证identity_path是否存在
                    if not identity_path.exists():
                        logger.warning(f"Identity path not found: {identity_path}")
                        continue

                    # 创建子智能体实例
                    subagent = AIAgent(
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        identity_path=identity_path,
                        load_soul_identity=True,
                        skip_context_files=True,  # 子智能体只加载身份文件
                        skip_memory=True,  # 子智能体有自己的记忆
                        quiet_mode=True,  # 子智能体静默模式
                    )

                    self.subagents[name] = subagent
                    logger.info(f"Created subagent: {name}")

                except Exception as e:
                    logger.error(f"Failed to create subagent {name}: {e}")

            self._initialized = True
            logger.info(f"Initialized {len(self.subagents)} subagents")

        except ImportError as e:
            logger.error(f"Failed to import AIAgent: {e}")
            raise

    def get_subagent(self, name: str) -> Optional[object]:
        """获取子智能体实例

        Args:
            name: 子智能体名称

        Returns:
            子智能体实例，如果不存在则返回None
        """
        if not self._initialized:
            logger.warning("Subagents not initialized, call create_subagents() first")
            return None

        return self.subagents.get(name)

    def get_all_subagents(self) -> Dict[str, object]:
        """获取所有子智能体实例

        Returns:
            所有子智能体实例的字典
        """
        return self.subagents.copy()

    def list_subagents(self) -> list[str]:
        """列出所有已创建的子智能体名称

        Returns:
            子智能体名称列表
        """
        return list(self.subagents.keys())

    def is_subagent_available(self, name: str) -> bool:
        """检查子智能体是否可用

        Args:
            name: 子智能体名称

        Returns:
            子智能体是否可用
        """
        return name in self.subagents

    def shutdown(self):
        """关闭所有子智能体实例

        清理资源，释放连接
        """
        for name, subagent in self.subagents.items():
            try:
                # 如果子智能体有shutdown方法，调用它
                if hasattr(subagent, 'shutdown'):
                    subagent.shutdown()
                logger.info(f"Shutdown subagent: {name}")
            except Exception as e:
                logger.error(f"Error shutting down subagent {name}: {e}")

        self.subagents.clear()
        self._initialized = False
```

- [ ] **Step 2: 创建子智能体管理器测试**

```python
# tests/unit/test_subagent_manager.py
"""测试子智能体管理器"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from scripts.subagent_manager import SubagentManager


@pytest.fixture
def mock_ai_agent():
    """模拟AIAgent类"""
    mock_agent = MagicMock()
    mock_agent.shutdown = MagicMock()
    return mock_agent


@pytest.fixture
def temp_project_root(tmp_path):
    """创建临时项目根目录"""
    # 创建子智能体目录
    for subagent in ["multi-dimensional-data-perception-agent", "anomaly-detection-agent",
                     "rule-reasoning-agent", "disposition-execution-agent"]:
        subagent_path = tmp_path / "subagents" / subagent
        subagent_path.mkdir(parents=True)
        (subagent_path / "SOUL.md").write_text(f"# {subagent} SOUL")
    return tmp_path


def test_subagent_manager_init():
    """测试SubagentManager初始化"""
    manager = SubagentManager()
    assert manager.project_root == Path.cwd()
    assert manager.subagents == {}
    assert manager._initialized is False


def test_subagent_manager_init_with_project_root(tmp_path):
    """测试SubagentManager使用自定义项目根目录"""
    manager = SubagentManager(project_root=tmp_path)
    assert manager.project_root == tmp_path


def test_subagent_manager_create_subagents(temp_project_root, mock_ai_agent):
    """测试创建子智能体"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)

        manager.create_subagents(
            model="gpt-4",
            base_url="https://api.example.com",
            api_key="test_key"
        )

        # 验证所有子智能体都被创建
        assert len(manager.subagents) == 4
        assert manager._initialized is True

        # 验证所有预期的子智能体都存在
        expected_subagents = [
            "multi-dimensional-data-perception-agent",
            "anomaly-detection-agent",
            "rule-reasoning-agent",
            "disposition-execution-agent"
        ]
        for name in expected_subagents:
            assert name in manager.subagents


def test_subagent_manager_get_subagent(temp_project_root, mock_ai_agent):
    """测试获取子智能体"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        # 获取存在的子智能体
        subagent = manager.get_subagent("anomaly-detection-agent")
        assert subagent is not None
        assert subagent == mock_ai_agent

        # 获取不存在的子智能体
        subagent = manager.get_subagent("non-existent-agent")
        assert subagent is None


def test_subagent_manager_get_all_subagents(temp_project_root, mock_ai_agent):
    """测试获取所有子智能体"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        all_subagents = manager.get_all_subagents()

        assert len(all_subagents) == 4
        # 验证返回的是副本
        all_subagents.clear()
        assert len(manager.subagents) == 4


def test_subagent_manager_list_subagents(temp_project_root, mock_ai_agent):
    """测试列出所有子智能体名称"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        subagent_names = manager.list_subagents()

        assert len(subagent_names) == 4
        assert "anomaly-detection-agent" in subagent_names
        assert "rule-reasoning-agent" in subagent_names


def test_subagent_manager_is_subagent_available(temp_project_root, mock_ai_agent):
    """测试检查子智能体是否可用"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        assert manager.is_subagent_available("anomaly-detection-agent") is True
        assert manager.is_subagent_available("non-existent-agent") is False


def test_subagent_manager_shutdown(temp_project_root, mock_ai_agent):
    """测试关闭子智能体管理器"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)
        manager.create_subagents()

        manager.shutdown()

        # 验证所有子智能体被清理
        assert len(manager.subagents) == 0
        assert manager._initialized is False

        # 验证每个子智能体的shutdown方法被调用
        assert mock_ai_agent.shutdown.call_count == 4


def test_subagent_manager_double_initialize(temp_project_root, mock_ai_agent):
    """测试重复初始化"""
    with patch('scripts.subagent_manager.AIAgent', return_value=mock_ai_agent):
        manager = SubagentManager(project_root=temp_project_root)

        # 第一次初始化
        manager.create_subagents()
        assert len(manager.subagents) == 4

        # 第二次初始化（应该跳过）
        manager.create_subagents()
        assert len(manager.subagents) == 4  # 数量不变
```

- [ ] **Step 3: 运行测试验证功能**

```bash
cd E:/project/Ecological_env
python -m pytest tests/unit/test_subagent_manager.py -v
```

预期输出：
```
collected 9 items

tests/unit/test_subagent_manager.py::test_subagent_manager_init PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_init_with_project_root PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_create_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_get_subagent PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_get_all_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_list_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_is_subagent_available PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_shutdown PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_double_initialize PASSED

9 passed in 0.85s
```

- [ ] **Step 4: 提交代码**

```bash
git add workspace/skills/orchestrator-core/scripts/subagent_manager.py tests/unit/test_subagent_manager.py
git commit -m "feat: add subagent instance manager"
```

---

## Task 4: 实现call_subagent工具

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/subagent_tools.py`
- Test: `tests/unit/test_subagent_tools.py`

- [ ] **Step 1: 创建子智能体调用工具**

```python
# workspace/skills/orchestrator-core/scripts/subagent_tools.py
"""子智能体调用工具

提供主智能体调用子智能体的工具函数
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 全局子智能体管理器实例
_subagent_manager = None


def get_subagent_manager():
    """获取全局子智能体管理器实例"""
    global _subagent_manager
    if _subagent_manager is None:
        from subagent_manager import SubagentManager
        # 使用项目根目录初始化
        project_root = Path(__file__).parents[4]  # 回到项目根目录
        _subagent_manager = SubagentManager(project_root=project_root)
    return _subagent_manager


def initialize_subagents(model: str = None, base_url: str = None, api_key: str = None) -> Dict[str, Any]:
    """初始化所有子智能体

    Args:
        model: LLM模型名称
        base_url: API基础URL
        api_key: API密钥

    Returns:
        初始化结果，包含:
        - success: bool - 是否成功
        - count: int - 创建的子智能体数量
        - subagents: list - 子智能体名称列表
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        manager.create_subagents(model=model, base_url=base_url, api_key=api_key)

        return {
            "success": True,
            "count": len(manager.subagents),
            "subagents": manager.list_subagents()
        }
    except Exception as e:
        logger.error(f"Failed to initialize subagents: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def call_subagent(
    subagent_name: str,
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """调用子智能体执行任务

    Args:
        subagent_name: 子智能体名称
        task: 需要子智能体执行的任务描述
        context: 可选的上下文信息

    Returns:
        子智能体的执行结果，包含:
        - success: bool - 是否成功
        - result: str - 执行结果
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()

        # 检查子智能体是否可用
        if not manager.is_subagent_available(subagent_name):
            return {
                "success": False,
                "error": f"子智能体 '{subagent_name}' 不存在或未初始化"
            }

        # 获取子智能体实例
        subagent = manager.get_subagent(subagent_name)
        if not subagent:
            return {
                "success": False,
                "error": f"无法获取子智能体 '{subagent_name}'"
            }

        # 构建完整的任务描述（包含上下文）
        full_task = task
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            full_task = f"上下文信息：\n{context_str}\n\n任务：\n{task}"

        # 调用子智能体执行任务
        logger.info(f"Calling subagent '{subagent_name}' with task: {task[:100]}...")

        result = subagent.run_conversation(full_task)

        # 提取最终响应
        if isinstance(result, dict):
            final_response = result.get("final_response", "")
        else:
            final_response = str(result)

        logger.info(f"Subagent '{subagent_name}' completed successfully")

        return {
            "success": True,
            "result": final_response
        }

    except Exception as e:
        logger.error(f"Error calling subagent '{subagent_name}': {e}")
        return {
            "success": False,
            "error": str(e)
        }


def list_available_subagents() -> Dict[str, Any]:
    """列出所有可用的子智能体

    Returns:
        可用子智能体列表，包含:
        - success: bool - 是否成功
        - subagents: list - 子智能体名称列表
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        subagent_names = manager.list_subagents()

        return {
            "success": True,
            "subagents": subagent_names
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_subagent_info(subagent_name: str) -> Dict[str, Any]:
    """获取子智能体信息

    Args:
        subagent_name: 子智能体名称

    Returns:
        子智能体信息，包含:
        - success: bool - 是否成功
        - available: bool - 是否可用
        - description: str - 描述
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()

        if subagent_name not in SubagentManager.SUBAGENT_CONFIGS:
            return {
                "success": False,
                "error": f"未知的子智能体: '{subagent_name}'"
            }

        config = SubagentManager.SUBAGENT_CONFIGS[subagent_name]
        available = manager.is_subagent_available(subagent_name)

        return {
            "success": True,
            "available": available,
            "description": config["description"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def shutdown_subagents() -> Dict[str, Any]:
    """关闭所有子智能体

    Returns:
        关闭结果，包含:
        - success: bool - 是否成功
        - error: str - 错误信息（如果有）
    """
    try:
        manager = get_subagent_manager()
        manager.shutdown()

        return {
            "success": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

- [ ] **Step 2: 创建子智能体工具测试**

```python
# tests/unit/test_subagent_tools.py
"""测试子智能体调用工具"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from scripts.subagent_tools import (
    call_subagent,
    initialize_subagents,
    list_available_subagents,
    get_subagent_info,
    shutdown_subagents,
    get_subagent_manager
)


@pytest.fixture
def mock_subagent_manager():
    """模拟子智能体管理器"""
    mock_manager = MagicMock()
    mock_manager.subagents = {}
    mock_manager._initialized = False
    mock_manager.is_subagent_available = MagicMock(return_value=True)
    mock_manager.get_subagent = MagicMock()
    mock_manager.list_subagents = MagicMock(return_value=[])
    mock_manager.create_subagents = MagicMock()
    mock_manager.shutdown = MagicMock()
    return mock_manager


@pytest.fixture
def mock_ai_agent():
    """模拟AIAgent实例"""
    mock_agent = MagicMock()
    mock_agent.run_conversation = MagicMock(return_value={
        "final_response": "Test response from subagent"
    })
    return mock_agent


def test_initialize_subagents(mock_subagent_manager):
    """测试初始化子智能体"""
    with patch('scripts.subagent_tools.SubagentManager', return_value=mock_subagent_manager):
        result = initialize_subagents(
            model="gpt-4",
            base_url="https://api.example.com",
            api_key="test_key"
        )

        assert result["success"] is True
        assert mock_subagent_manager.create_subagents.called


def test_initialize_subagents_error(mock_subagent_manager):
    """测试初始化子智能体失败"""
    mock_subagent_manager.create_subagents.side_effect = Exception("Init failed")

    with patch('scripts.subagent_tools.SubagentManager', return_value=mock_subagent_manager):
        result = initialize_subagents()

        assert result["success"] is False
        assert "error" in result


def test_call_subagent_success(mock_subagent_manager, mock_ai_agent):
    """测试成功调用子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = True
    mock_subagent_manager.get_subagent.return_value = mock_ai_agent

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测数据异常"
        )

        assert result["success"] is True
        assert result["result"] == "Test response from subagent"
        assert mock_ai_agent.run_conversation.called


def test_call_subagent_not_available(mock_subagent_manager):
    """测试调用不存在的子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = False

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = call_subagent(
            subagent_name="non-existent-agent",
            task="执行任务"
        )

        assert result["success"] is False
        assert "不存在" in result["error"]


def test_call_subagent_with_context(mock_subagent_manager, mock_ai_agent):
    """测试带上下文调用子智能体"""
    mock_subagent_manager.is_subagent_available.return_value = True
    mock_subagent_manager.get_subagent.return_value = mock_ai_agent

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        context = {"data_source": "sensor-001", "time_range": "2024-01-01"}
        result = call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常",
            context=context
        )

        assert result["success"] is True
        # 验证上下文被包含在任务中
        call_args = mock_ai_agent.run_conversation.call_args
        assert "上下文信息" in call_args[0][0]


def test_list_available_subagents(mock_subagent_manager):
    """测试列出可用子智能体"""
    mock_subagent_manager.list_subagents.return_value = [
        "multi-dimensional-data-perception-agent",
        "anomaly-detection-agent"
    ]

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = list_available_subagents()

        assert result["success"] is True
        assert len(result["subagents"]) == 2


def test_get_subagent_info(mock_subagent_manager):
    """测试获取子智能体信息"""
    mock_subagent_manager.is_subagent_available.return_value = True

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = get_subagent_info("anomaly-detection-agent")

        assert result["success"] is True
        assert result["available"] is True
        assert "description" in result


def test_get_subagent_info_unknown():
    """测试获取未知子智能体信息"""
    with patch('scripts.subagent_tools.SubagentManager') as MockManager:
        MockManager.SUBAGENT_CONFIGS = {"known-agent": {}}
        result = get_subagent_info("unknown-agent")

        assert result["success"] is False
        assert "未知" in result["error"]


def test_shutdown_subagents(mock_subagent_manager):
    """测试关闭子智能体"""
    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = shutdown_subagents()

        assert result["success"] is True
        assert mock_subagent_manager.shutdown.called


def test_shutdown_subagents_error(mock_subagent_manager):
    """测试关闭子智能体失败"""
    mock_subagent_manager.shutdown.side_effect = Exception("Shutdown failed")

    with patch('scripts.subagent_tools.get_subagent_manager', return_value=mock_subagent_manager):
        result = shutdown_subagents()

        assert result["success"] is False
        assert "error" in result
```

- [ ] **Step 3: 运行测试验证功能**

```bash
cd E:/project/Ecological_env
python -m pytest tests/unit/test_subagent_tools.py -v
```

预期输出：
```
collected 11 items

tests/unit/test_subagent_tools.py::test_initialize_subagents PASSED
tests/unit/test_subagent_tools.py::test_initialize_subagents_error PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_success PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_not_available PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_with_context PASSED
tests/unit/test_subagent_tools.py::test_list_available_subagents PASSED
tests/unit/test_subagent_tools.py::test_get_subagent_info PASSED
tests/unit/test_subagent_tools.py::test_get_subagent_info_unknown PASSED
tests/unit/test_subagent_tools.py::test_shutdown_subagents PASSED
tests/unit/test_subagent_tools.py::test_shutdown_subagents_error PASSED

11 passed in 0.95s
```

- [ ] **Step 4: 提交代码**

```bash
git add workspace/skills/orchestrator-core/scripts/subagent_tools.py tests/unit/test_subagent_tools.py
git commit -m "feat: add subagent calling tools"
```

---

## Task 5: 编写orchestrator-core的SKILL.md

**Files:**
- Create: `workspace/skills/orchestrator-core/SKILL.md`

- [ ] **Step 1: 创建orchestrator-core的SKILL.md**

```markdown
# 编排器核心技能

## 技能描述

本技能是主智能体的核心编排能力，负责管理和调用4个子智能体完成复杂的废水监测任务。通过LLM决策和自然语言描述引导，实现智能的任务分发和结果聚合。

## 子智能体职责

### multi-dimensional-data-perception-agent（多维数据感知子智能体）

**职责范围：**
- 多源数据获取（CSV、API、数据库）
- 数据质量检查和清洗
- 时序数据对齐处理
- 字段标准化处理
- 数据完整性验证

**典型任务：**
- "获取最近24小时的监测数据"
- "检查数据质量并标记异常值"
- "对齐多个传感器的时间序列数据"

### anomaly-detection-agent（异常检测子智能体）

**职责范围：**
- 5类异常识别：平稳、突变、趋势、周期、高频波动
- 4类违规检测：插瓶干扰、人工拟合、稀释排放、恶意逃避
- 置信度评估和异常评分
- 异常模式聚类分析

**典型任务：**
- "检测数据中的异常模式"
- "识别可能的插瓶干扰行为"
- "评估异常的置信度"

### rule-reasoning-agent（规则推理子智能体）

**职责范围：**
- 法规规则匹配和验证
- 工艺机理校验
- 专家推理和经验应用
- 违规性质判定

**典型任务：**
- "验证检测结果是否符合排放标准"
- "根据工艺知识判断数据合理性"
- "应用专家经验分析异常"

### disposition-execution-agent（研判预警与处置执行子智能体）

**职责范围：**
- 融合共识算法
- 三级预警分类（高、中、低）
- 工单生成和分发
- 处置建议生成

**典型任务：**
- "综合分析结果并生成预警"
- "创建处置工单"
- "生成处置建议方案"

## 调用原则

### 1. 单一职责优先
- 优先调用最相关的子智能体，而非同时调用多个
- 每个子智能体专注于特定领域，避免职责重叠

### 2. 协作按需
- 当任务需要多领域协作时，可以按顺序调用多个子智能体
- 前一个子智能体的结果可以作为后一个子智能体的输入

### 3. 结果传递
- 将前序子智能体的关键结果传递给后续子智能体
- 保持上下文的连贯性

### 4. 避免重复
- 不要为同一任务重复调用同一个子智能体
- 已有结果可以直接使用时，避免重复计算

## 典型工作流

### 数据异常检测完整流程

```
用户查询 → 主智能体分析 → 调用子智能体 → 结果聚合 → 响应用户

详细步骤：
1. 调用 multi-dimensional-data-perception-agent 获取数据
2. 调用 anomaly-detection-agent 检测异常
3. 调用 rule-reasoning-agent 进行规则验证
4. 调用 disposition-execution-agent 生成预警
5. 主智能体汇总结果并生成自然语言响应
```

### 简化数据查询流程

```
用户查询 → 主智能体分析 → 调用单个子智能体 → 响应用户

示例：
用户: "获取最新的监测数据"
1. 调用 multi-dimensional-data-perception-agent 获取数据
2. 直接响应用户
```

## 工具说明

### call_subagent

调用指定的子智能体执行任务。

**参数：**
- `subagent_name` (str): 子智能体名称，必须是以下之一：
  - "multi-dimensional-data-perception-agent"
  - "anomaly-detection-agent"
  - "rule-reasoning-agent"
  - "disposition-execution-agent"
- `task` (str): 需要子智能体执行的任务描述
- `context` (dict, 可选): 附加的上下文信息

**返回：**
- `success` (bool): 是否成功
- `result` (str): 执行结果
- `error` (str): 错误信息（如果有）

**使用示例：**
```
调用 anomaly-detection-agent 检测异常
subagent_name: "anomaly-detection-agent"
task: "检测以下数据中的异常模式：[数据]"
```

### initialize_subagents

初始化所有子智能体实例。

**参数：**
- `model` (str, 可选): LLM模型名称
- `base_url` (str, 可选): API基础URL
- `api_key` (str, 可选): API密钥

**返回：**
- `success` (bool): 是否成功
- `count` (int): 创建的子智能体数量
- `subagents` (list): 子智能体名称列表

**注意：** 通常在系统启动时自动调用，无需手动调用。

### list_available_subagents

列出所有可用的子智能体。

**返回：**
- `success` (bool): 是否成功
- `subagents` (list): 子智能体名称列表

## 决策指南

### 何时调用子智能体

**应该调用：**
- 需要专业领域知识（数据感知、异常检测、规则推理、处置执行）
- 需要执行复杂计算或分析
- 需要访问特定数据源或知识库

**不应该调用：**
- 简单的信息查询（可以直接回答）
- 已有结果的重复请求
- 超出子智能体职责范围的任务

### 选择哪个子智能体

| 用户需求 | 调用的子智能体 |
|---------|--------------|
| 获取/处理数据 | multi-dimensional-data-perception-agent |
| 检测异常/违规 | anomaly-detection-agent |
| 规则匹配/工艺校验 | rule-reasoning-agent |
| 生成预警/工单 | disposition-execution-agent |

## 错误处理

### 子智能体调用失败
如果子智能体调用失败（`success: false`），应该：
1. 检查错误信息
2. 如果是临时性问题，可以重试
3. 如果是配置问题，提示用户检查系统配置
4. 向用户清晰解释错误原因

### 子智能体不存在
如果调用的子智能体不存在：
1. 检查子智能体名称是否正确
2. 使用 `list_available_subagents` 查看可用子智能体
3. 提示用户正确的子智能体名称

## 技能约束

本技能有以下约束：
- 只能调用预定义的4个子智能体
- 子智能体之间不能直接通信，必须通过主智能体中转
- 子智能体的执行结果需要主智能体进行汇总和解释
- 一次只能调用一个子智能体（串行调用）

## 技能进化

本技能会根据使用情况不断优化：
- 记录常见的调用模式
- 优化工作流路径
- 改进错误处理
- 增强调试信息
```

- [ ] **Step 2: 提交代码**

```bash
git add workspace/skills/orchestrator-core/SKILL.md
git commit -m "docs: add orchestrator-core skill definition"
```

---

## Task 6: 创建集成测试

**Files:**
- Create: `tests/integration/test_multi_agent_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
# tests/integration/test_multi_agent_integration.py
"""多智能体架构集成测试

测试主智能体、子智能体管理器、调用工具的完整集成流程
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加scripts目录到路径
scripts_dir = Path(__file__).parents[2] / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def mock_subagent():
    """模拟子智能体"""
    mock = MagicMock()
    mock.run_conversation = MagicMock(return_value={
        "final_response": "Test subagent response"
    })
    return mock


@pytest.fixture
def temp_project_structure(tmp_path):
    """创建临时项目结构"""
    # 创建主智能体工作区
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("# 主智能体SOUL")

    # 创建子智能体工作区
    subagents = {
        "multi-dimensional-data-perception-agent": "多维数据感知",
        "anomaly-detection-agent": "异常检测",
        "rule-reasoning-agent": "规则推理",
        "disposition-execution-agent": "研判预警"
    }

    for name, desc in subagents.items():
        subagent_path = tmp_path / "subagents" / name
        subagent_path.mkdir(parents=True)
        (subagent_path / "SOUL.md").write_text(f"# {desc}子智能体")

    return tmp_path


@pytest.mark.integration
def test_full_integration_flow(temp_project_structure, mock_subagent):
    """测试完整的集成流程"""
    with patch('subagent_manager.AIAgent', return_value=mock_subagent):
        # 导入模块（使用临时项目结构）
        import subagent_manager
        import subagent_tools

        # 设置项目根目录
        subagent_manager._project_root = temp_project_structure

        # 1. 初始化子智能体
        init_result = subagent_tools.initialize_subagents()
        assert init_result["success"] is True
        assert init_result["count"] == 4

        # 2. 查看可用子智能体
        list_result = subagent_tools.list_available_subagents()
        assert list_result["success"] is True
        assert len(list_result["subagents"]) == 4

        # 3. 调用子智能体
        call_result = subagent_tools.call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常"
        )
        assert call_result["success"] is True
        assert "result" in call_result

        # 4. 关闭子智能体
        shutdown_result = subagent_tools.shutdown_subagents()
        assert shutdown_result["success"] is True


@pytest.mark.integration
def test_multi_subagent_call_sequence(temp_project_structure, mock_subagent):
    """测试顺序调用多个子智能体"""
    with patch('subagent_manager.AIAgent', return_value=mock_subagent):
        import subagent_tools

        # 初始化
        subagent_tools.initialize_subagents()

        # 按顺序调用多个子智能体
        sequence = [
            ("multi-dimensional-data-perception-agent", "获取数据"),
            ("anomaly-detection-agent", "检测异常"),
            ("rule-reasoning-agent", "规则验证"),
        ]

        for name, task in sequence:
            result = subagent_tools.call_subagent(name, task)
            assert result["success"] is True
            print(f"{name}: {result['result']}")


@pytest.mark.integration
def test_subagent_error_handling(temp_project_structure):
    """测试子智能体错误处理"""
    with patch('subagent_manager.AIAgent', return_value=MagicMock(side_effect=Exception("Test error"))):
        import subagent_tools

        # 初始化
        subagent_tools.initialize_subagents()

        # 调用失败的子智能体
        result = subagent_tools.call_subagent(
            subagent_name="anomaly-detection-agent",
            task="检测异常"
        )

        assert result["success"] is False
        assert "error" in result
```

- [ ] **Step 2: 运行集成测试**

```bash
cd E:/project/Ecological_env
python -m pytest tests/integration/test_multi_agent_integration.py -v --tb=short
```

预期输出：
```
collected 3 items

tests/integration/test_multi_agent_integration.py::test_full_integration_flow PASSED
tests/integration/test_multi_agent_integration.py::test_multi_subagent_call_sequence PASSED
tests/integration/test_multi_agent_integration.py::test_subagent_error_handling PASSED

3 passed in 3.5s
```

- [ ] **Step 3: 提交代码**

```bash
git add tests/integration/test_multi_agent_integration.py
git commit -m "test: add multi-agent integration tests"
```

---

## Task 7: 创建项目文档

**Files:**
- Create: `docs/architecture/multi-agent-architecture.md`

- [ ] **Step 1: 创建架构文档**

```markdown
# 多智能体架构说明

## 概述

本文档说明废水监测系统的多智能体架构实现。

## 架构设计

系统采用同进程+逻辑隔离的多智能体架构：

```
┌──────────────────────────────────────────────────┐
│               单一进程                            │
│                                                   │
│  ┌────────────┐                                  │
│  │ 主智能体   │                                  │
│  │ AIAgent    │                                  │
│  └──────┬─────┘                                  │
│         │                                        │
│         ├──→ call_subagent                       │
│         │                                        │
│         ▼                                        │
│  ┌────────────────────────────────┐            │
│  │   SubagentManager              │            │
│  │   管理4个子智能体实例            │            │
│  └────────────┬───────────────────┘            │
│               │                                 │
│    ┌──────────┼──────────┬──────────┐          │
│    ▼          ▼          ▼          ▼          │
│ ┌─────┐  ┌─────┐   ┌─────┐   ┌─────┐        │
│ │数据  │  │异常  │   │规则  │   │预警  │        │
│ │感知  │  │检测  │   │推理  │   │处置  │        │
│ └─────┘  └─────┘   └─────┘   └─────┘        │
└──────────────────────────────────────────────────┘
```

## 核心组件

### 1. AIAgent（扩展版）

基于Hermes Agent框架的AIAgent，增加了`identity_path`参数支持。

**关键特性：**
- 支持从自定义路径加载身份文件
- 支持7个身份文件（IDENTITY.md, SOUL.md, AGENTS.md, MEMORY.md, USER.md, TOOLS.md, HEARTBEAT.md）
- 完整的工具调用系统
- 会话管理

### 2. SubagentManager

子智能体实例管理器，负责：
- 创建所有子智能体实例
- 管理子智能体生命周期
- 提供子智能体查询接口

### 3. call_subagent工具

主智能体调用子智能体的工具接口：
- `call_subagent(subagent_name, task, context)`
- 返回子智能体的执行结果

### 4. orchestrator-core技能

主智能体的核心编排技能，定义在`workspace/skills/orchestrator-core/SKILL.md`。

## 使用方法

### 创建主智能体

```python
from run_agent import AIAgent

master_agent = AIAgent(
    model="gpt-4",
    identity_path="workspace",
    load_soul_identity=True
)
```

### 创建子智能体管理器

```python
from scripts.subagent_manager import SubagentManager

manager = SubagentManager(project_root="/path/to/project")
manager.create_subagents(
    model="gpt-4",
    base_url="https://api.example.com",
    api_key="your-api-key"
)
```

### 调用子智能体

```python
from scripts.subagent_tools import call_subagent

result = call_subagent(
    subagent_name="anomaly-detection-agent",
    task="检测数据异常"
)

if result["success"]:
    print(result["result"])
else:
    print(f"Error: {result['error']}")
```

## 目录结构

```
项目根目录/
├── workspace/                      # 主智能体工作区
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── AGENTS.md
│   ├── MEMORY.md
│   ├── USER.md
│   ├── TOOLS.md
│   ├── HEARTBEAT.md
│   └── skills/
│       └── orchestrator-core/
│           ├── SKILL.md
│           └── scripts/
│               ├── subagent_manager.py
│               └── subagent_tools.py
│
├── subagents/                      # 子智能体工作区
│   ├── multi-dimensional-data-perception-agent/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── skills/
│   ├── anomaly-detection-agent/
│   ├── rule-reasoning-agent/
│   └── disposition-execution-agent/
│
├── shared/framework/hermes_agent/  # Hermes框架（已修改）
│   ├── agent/
│   │   ├── identity_loader.py      # 新增：身份文件加载器
│   │   ├── agent_init.py           # 修改：支持identity_path
│   │   ├── prompt_builder.py       # 修改：支持identity_path
│   │   └── system_prompt.py        # 修改：支持identity_path
│   └── run_agent.py                # 修改：支持identity_path
│
└── tests/                          # 测试
    ├── unit/
    │   ├── test_identity_loader.py
    │   ├── test_ai_agent_identity_path.py
    │   ├── test_subagent_manager.py
    │   └── test_subagent_tools.py
    └── integration/
        └── test_multi_agent_integration.py
```

## API参考

### AIAgent参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| identity_path | str\|Path | None | 身份文件目录路径 |
| model | str | "" | LLM模型名称 |
| base_url | str | 从环境变量 | API基础URL |
| api_key | str | 从环境变量 | API密钥 |
| load_soul_identity | bool | False | 是否加载身份文件 |

### SubagentManager方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| create_subagents | model, base_url, api_key | None | 创建所有子智能体 |
| get_subagent | name | AIAgent\|None | 获取子智能体实例 |
| list_subagents | - | list[str] | 列出所有子智能体名称 |
| is_subagent_available | name | bool | 检查子智能体是否可用 |
| shutdown | - | None | 关闭所有子智能体 |

### call_subagent工具

| 工具 | 参数 | 返回值 |
|------|------|--------|
| call_subagent | subagent_name, task, context | {success, result, error} |
| initialize_subagents | model, base_url, api_key | {success, count, subagents} |
| list_available_subagents | - | {success, subagents} |
| get_subagent_info | subagent_name | {success, available, description} |
| shutdown_subagents | - | {success, error} |

## 开发指南

### 添加新的子智能体

1. 创建子智能体目录和身份文件
2. 在`SubagentManager.SUBAGENT_CONFIGS`中添加配置
3. 在`orchestrator-core/SKILL.md`中更新职责描述
4. 编写相应测试

### 调试技巧

1. 使用`list_available_subagents`检查子智能体状态
2. 查看日志输出了解调用流程
3. 使用单元测试验证组件功能
4. 使用集成测试验证完整流程

## 参考资料

- 设计文档：`docs/superpowers/specs/2026-07-13-多智能体底层架构设计.md`
- 实现计划：`docs/superpowers/plans/2026-07-13-multi-agent-architecture.md`
- Hermes Agent文档：https://github.com/NousResearch/hermes-agent
```

- [ ] **Step 2: 提交代码**

```bash
git add docs/architecture/multi-agent-architecture.md
git commit -m "docs: add multi-agent architecture documentation"
```

---

## Task 8: 运行完整测试套件

**Files:**
- Test: All test files

- [ ] **Step 1: 运行所有单元测试**

```bash
cd E:/project/Ecological_env
python -m pytest tests/unit/ -v --tb=short
```

预期输出：
```
collected 31 items

tests/unit/test_identity_loader.py::test_resolve_identity_path_absolute PASSED
tests/unit/test_identity_loader.py::test_resolve_identity_path_relative PASSED
tests/unit/test_identity_loader.py::test_resolve_identity_path_none PASSED
tests/unit/test_identity_loader.py::test_load_identity_files_from_nonexistent_path PASSED
tests/unit/test_identity_loader.py::test_load_single_identity_file PASSED
tests/unit/test_identity_loader.py::test_load_single_identity_file_nonexistent PASSED
tests/unit/test_identity_loader.py::test_load_identity_files_from_path_multiple_files PASSED
tests/unit/test_ai_agent_identity_path.py::test_ai_agent_with_identity_path PASSED
tests/unit/test_ai_agent_identity_path.py::test_ai_agent_without_identity_path PASSED
tests/unit/test_ai_agent_identity_path.py::test_ai_agent_identity_path_relative PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_init PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_init_with_project_root PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_create_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_get_subagent PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_get_all_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_list_subagents PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_is_subagent_available PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_shutdown PASSED
tests/unit/test_subagent_manager.py::test_subagent_manager_double_initialize PASSED
tests/unit/test_subagent_tools.py::test_initialize_subagents PASSED
tests/unit/test_subagent_tools.py::test_initialize_subagents_error PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_success PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_not_available PASSED
tests/unit/test_subagent_tools.py::test_call_subagent_with_context PASSED
tests/unit/test_subagent_tools.py::test_list_available_subagents PASSED
tests/unit/test_subagent_tools.py::test_get_subagent_info PASSED
tests/unit/test_subagent_tools.py::test_get_subagent_info_unknown PASSED
tests/unit/test_subagent_tools.py::test_shutdown_subagents PASSED
tests/unit/test_subagent_tools.py::test_shutdown_subagents_error PASSED

31 passed in 5.2s
```

- [ ] **Step 2: 运行所有集成测试**

```bash
cd E:/project/Ecological_env
python -m pytest tests/integration/ -v --tb=short
```

预期输出：
```
collected 3 items

tests/integration/test_multi_agent_integration.py::test_full_integration_flow PASSED
tests/integration/test_multi_agent_integration.py::test_multi_subagent_call_sequence PASSED
tests/integration/test_multi_agent_integration.py::test_subagent_error_handling PASSED

3 passed in 3.8s
```

- [ ] **Step 3: 运行测试覆盖率**

```bash
cd E:/project/Ecological_env
python -m pytest tests/ --cov=shared/framework/hermes_agent/agent --cov=workspace/skills/orchestrator-core/scripts --cov-report=html --cov-report=term
```

预期输出：
```
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------------------------------------------------------------
shared/framework/hermes_agent/agent/         85      5    94%
workspace/skills/orchestrator-core/scripts   120      8    93%
-------------------------------------------------------------------------------------------------------------------
TOTAL                                        205     13    94%
```

- [ ] **Step 4: 提交最终代码**

```bash
git add .
git commit -m "test: all tests passing, implementation complete"
```

---

## 完成检查清单

在实现完成后，验证以下内容：

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 测试覆盖率 ≥ 90%
- [ ] 代码已提交到git
- [ ] 文档已更新
- [ ] 设计文档中的所有需求都已实现

---

**实施顺序建议：**
1. 先完成Task 1-2（Hermes框架适配）
2. 再完成Task 3-4（子智能体管理）
3. 然后完成Task 5-7（技能和文档）
4. 最后完成Task 8（测试验证）

**预计总时间：** 6-8小时

**风险点：**
- Hermes框架的内部结构可能有变化，需要灵活调整
- 子智能体的身份文件路径需要正确配置
- 测试环境需要正确设置项目根目录

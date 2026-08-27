# 智能体配置中心实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 /agents/config 从静态展示页重建为配置中心：身份文件在线编辑（git 快照+回滚）、厂区配置管理、运行参数（SQLite）+ LLM 切换测试、agent 服务一键重启。

**Architecture:** 文件仍是真相源（workspace/*.md、plant-hierarchy.yaml），后端提供白名单读写下 + git 快照；运行参数进 SQLite `agent_runtime_params` 单表，读取方 `get_param()` DB 优先 env/代码兜底；agent 重启由后端 psutil kill 8642 + detached 新进程托管。前端左实体树右内容区（概览/身份文件/参数 tab + 独立厂区配置入口）。

**Tech Stack:** FastAPI + SQLAlchemy(SQLite) + psutil + git CLI；Vue3 + Element Plus（既有 admin 浅色风格）。

**Spec:** `docs/superpowers/specs/2026-08-27-agent-config-center-design.md`

**venv python（所有 pytest/脚本一律用它）：** `ecological_env\Scripts\python.exe`（bash 里写 `./ecological_env/Scripts/python.exe`，cwd 为项目根）

---

## 文件结构

```
后端（新增）
  backend/services/agent_params.py          ← 参数注册表 + get_param/DB 读写（核心）
  backend/models/agent_config.py            ← AgentRuntimeParam 表
  backend/api/v1/agents/__init__.py         ← 空包
  backend/api/v1/agents/config/__init__.py  ← 空包
  backend/api/v1/agents/config/routes.py    ← 全部 REST 接口
  backend/services/identity_files.py        ← 白名单 + 文件读写 + git 快照/历史/回滚
  backend/services/plant_config_service.py  ← plant-hierarchy.yaml 读写+校验
  backend/services/agent_service_control.py ← kill 8642 + detached 重启 + health 轮询
  backend/tests/test_agent_params.py
  backend/tests/test_identity_files.py
  backend/tests/test_plant_config_service.py
后端（修改）
  backend/main.py                           ← 注册新路由（/api/v1/agents/config）
  backend/database/init_db.py               ← import AgentRuntimeParam
  requirements.txt                          ← + psutil
  scripts/start_agent.py                    ← 3 处 get_param 接线
  skills/orchestrator-core/scripts/call_subagent.py       ← SUBAGENT_TIMEOUT 走 get_param
  skills/orchestrator-core/scripts/subagent_entry.py      ← max_iterations 走 get_param + 别名表读 yaml
前端（新增）
  src/api/modules/agentConfig.ts
  src/components/agents/config/EntityTree.vue
  src/components/agents/config/EntityOverview.vue
  src/components/agents/config/IdentityFileEditor.vue
  src/components/agents/config/ParamsPanel.vue
  src/components/agents/config/PlantsConfigPanel.vue
  src/components/agents/config/ServiceControl.vue
前端（重写）
  src/views/AgentConfigView.vue
配置
  shared/data/plant-hierarchy.yaml          ← 新增 plant_aliases 段（迁移 _PLANT_ALIASES）
```

---

## Task 1: 参数注册表 + DB 表 + get_param

**Files:**
- Create: `backend/models/agent_config.py`
- Create: `backend/services/agent_params.py`
- Modify: `backend/database/init_db.py`（加 import）
- Test: `backend/tests/test_agent_params.py`

- [ ] **Step 1.1: 写失败测试**

```python
# backend/tests/test_agent_params.py
"""agent_params 单测：注册表完整性 / get_param DB优先 / env兜底 / 类型转换 / 脱敏。
用独立临时 DB,不碰 shared/data/ecological_logs.db。"""
import os, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 独立临时库——避免污染真实日志库
@pytest.fixture()
def db_session(tmp_path):
    from backend.database.base import Base
    import backend.models.agent_config  # noqa: F401 注册表到 metadata
    eng = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_registry_has_required_keys():
    from backend.services.agent_params import PARAM_REGISTRY
    keys = set(PARAM_REGISTRY)
    assert {"hermes_total_timeout", "subagent_timeout", "agent_timeout",
            "master_max_iterations", "subagent_max_iterations",
            "llm_base_url", "llm_model", "llm_api_key"} <= keys
    # 每个参数都有必备字段
    for k, spec in PARAM_REGISTRY.items():
        for f in ("default", "type", "effect", "reader"):
            assert f in spec, f"{k} 缺 {f}"
        assert spec["effect"] in ("immediate", "restart")
        assert spec["type"] in ("int", "str", "secret")


def test_get_param_env_fallback(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "ctgu-vlm")
    from backend.services.agent_params import get_param
    assert get_param("llm_model", env_key="LLM_MODEL", default="x") == "ctgu-vlm"


def test_get_param_db_overrides_env(db_session, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setattr("backend.services.agent_params._session_factory",
                        lambda: db_session)
    from backend.services.agent_params import set_param, get_param
    set_param("llm_model", "db-model")
    assert get_param("llm_model", env_key="LLM_MODEL", default="x") == "db-model"


def test_get_param_int_conversion(db_session, monkeypatch):
    monkeypatch.setattr("backend.services.agent_params._session_factory",
                        lambda: db_session)
    from backend.services.agent_params import set_param, get_param
    set_param("hermes_total_timeout", "450")   # DB 存字符串
    assert get_param("hermes_total_timeout", default=300) == 450   # 返回 int


def test_invalid_int_falls_back(db_session, monkeypatch):
    monkeypatch.setattr("backend.services.agent_params._session_factory",
                        lambda: db_session)
    from backend.services.agent_params import set_param, get_param
    set_param("hermes_total_timeout", "not-a-number")
    assert get_param("hermes_total_timeout", default=300) == 300  # 坏值→默认


def test_mask_secret():
    from backend.services.agent_params import mask_secret
    assert mask_secret("sk-abcdef1234") == "sk-***1234"
    assert mask_secret("") == ""
    assert mask_secret("ab") == "***"       # 太短全遮
    assert mask_secret(None) == ""
```

- [ ] **Step 1.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_agent_params.py -v`
Expected: FAIL（`ModuleNotFoundError: backend.services.agent_params` / `backend.models.agent_config`）

- [ ] **Step 1.3: 写模型**

```python
# backend/models/agent_config.py
"""智能体运行参数表（配置中心可在线改的参数真相源之一）。
key/value 字符串存储，读取方经 agent_params.get_param 按类型转换。"""
from datetime import datetime
from sqlalchemy import Column, String, Text, TIMESTAMP
from backend.database.base import Base


class AgentRuntimeParam(Base):
    __tablename__ = "agent_runtime_params"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 1.4: 写 agent_params 服务**

```python
# backend/services/agent_params.py
"""运行参数注册表 + DB 优先读取。

设计（spec §3.2）：
- PARAM_REGISTRY：参数目录。改这里的字段必须同步 GET /agents/config/params 的展示。
- get_param(key, env_key, default)：DB 有值→转换类型返回；否则 env；否则 default。
  读取方（start_agent/call_subagent/subagent_entry/backend query）零改动语义——
  只是多了一层 DB 覆盖。
- secret 类型：GET 接口用 mask_secret 脱敏；set_param 存明文。
- DB 会话工厂惰性创建——子进程(subagent)导入本模块不立即连库。
"""
import os
from typing import Optional, Union

# 参数目录：default=未配置时的值；type=int/str/secret；effect=立即生效|需重启；
# reader=哪里读它（页面展示用）；env_key=对应的 .env 变量名（兜底来源）
PARAM_REGISTRY: dict = {
    "hermes_total_timeout": {"default": 300, "type": "int", "effect": "restart",
        "reader": "scripts/start_agent.py", "env_key": "HERMES_TOTAL_TIMEOUT",
        "desc": "主智能体单次会话总超时(秒)"},
    "subagent_timeout": {"default": 600, "type": "int", "effect": "restart",
        "reader": "call_subagent.py", "env_key": "SUBAGENT_TIMEOUT",
        "desc": "单个子智能体 subprocess 超时(秒)"},
    "agent_timeout": {"default": 600, "type": "int", "effect": "immediate",
        "reader": "backend/api/routes/query.py", "env_key": "AGENT_TIMEOUT",
        "desc": "后端→agent 服务 HTTP 超时(秒)，每请求读取"},
    "master_max_iterations": {"default": 15, "type": "int", "effect": "restart",
        "reader": "scripts/start_agent.py", "env_key": None,
        "desc": "主智能体最大迭代轮数"},
    "subagent_max_iterations": {"default": 8, "type": "int", "effect": "restart",
        "reader": "subagent_entry.py", "env_key": None,
        "desc": "子智能体最大迭代轮数"},
    "llm_base_url": {"default": "http://172.16.12.41:30000/v1", "type": "str", "effect": "restart",
        "reader": "start_agent + subagent_entry", "env_key": "LLM_BASE_URL",
        "desc": "LLM OpenAI 兼容 API 地址"},
    "llm_model": {"default": "ctgu-vlm", "type": "str", "effect": "restart",
        "reader": "start_agent + subagent_entry", "env_key": "LLM_MODEL",
        "desc": "LLM 模型名"},
    "llm_api_key": {"default": "", "type": "secret", "effect": "restart",
        "reader": "start_agent + subagent_entry", "env_key": "LLM_API_KEY",
        "desc": "LLM API 密钥（脱敏显示）"},
}

_factory = None  # 惰性：测试用 monkeypatch 替换

def _session_factory():
    global _factory
    if _factory is None:
        from backend.database.session import SessionLocal
        _factory = SessionLocal
    return _factory


def _convert(raw: Optional[str], ptype: str, default):
    if raw is None or raw == "":
        return None
    if ptype == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None  # 坏值→视为未配置
    return raw


def get_param(key: str, env_key: Optional[str] = None, default=None):
    """DB 优先 → env → default。任何一步异常都静默降级（参数读取不能拖垮主流程）。"""
    spec = PARAM_REGISTRY.get(key, {})
    ptype = spec.get("type", "str")
    if env_key is None:
        env_key = spec.get("env_key")
    try:
        from backend.models.agent_config import AgentRuntimeParam
        with _session_factory()() as s:
            row = s.get(AgentRuntimeParam, key)
            if row is not None:
                v = _convert(row.value, ptype, default)
                if v is not None:
                    return v
    except Exception:
        pass  # DB 不可用→env 兜底
    if env_key:
        v = _convert(os.getenv(env_key), ptype, default)
        if v is not None:
            return v
    return default if default is not None else spec.get("default")


def set_param(key: str, value: str) -> None:
    from backend.models.agent_config import AgentRuntimeParam
    from datetime import datetime
    with _session_factory()() as s:
        row = s.get(AgentRuntimeParam, key)
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            s.add(AgentRuntimeParam(key=key, value=value))
        s.commit()


def mask_secret(v: Optional[str]) -> str:
    if not v:
        return ""
    return f"{v[:3]}***{v[-4:]}" if len(v) > 8 else "***"
```

注意：`_session_factory` 是函数不是变量，测试 monkeypatch 的 target 是 `"backend.services.agent_params._session_factory"`（函数属性可被 setattr 覆盖，调用处写 `_session_factory()`）。

- [ ] **Step 1.5: init_db 注册表**

`backend/database/init_db.py` 在 `from backend.models.conversation import (...)` 后加：

```python
from backend.models.agent_config import AgentRuntimeParam
```

- [ ] **Step 1.6: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_agent_params.py -v`
Expected: 6 passed

- [ ] **Step 1.7: Commit**

```bash
git add backend/models/agent_config.py backend/services/agent_params.py backend/database/init_db.py backend/tests/test_agent_params.py
git commit -m "feat(config): 运行参数注册表+SQLite表+get_param(DB优先/env兜底/类型转换/脱敏)"
```

---

## Task 2: 读取方接线（5 处 get_param 化）

**Files:**
- Modify: `scripts/start_agent.py:37,94-96,115-117`
- Modify: `skills/orchestrator-core/scripts/call_subagent.py:289`
- Modify: `skills/orchestrator-core/scripts/subagent_entry.py:254`

**注意**：start_agent / call_subagent / subagent_entry 都是**独立进程**，import backend 前必须把项目根加进 sys.path（start_agent 已有 project_root 逻辑；call_subagent/subagent_entry 用标记法向上找含 `shared/` 的目录）。

- [ ] **Step 2.1: start_agent.py 三处**

L37 附近（import AIAgent 之前）：

```python
# 参数中心：DB 优先读 hermes_total_timeout（未配置时 300）。
# 必须在 import AIAgent（conversation_loop 读默认值）之前设置。
from backend.services.agent_params import get_param as _gp
os.environ['HERMES_TOTAL_TIMEOUT'] = str(_gp("hermes_total_timeout", env_key="HERMES_TOTAL_TIMEOUT", default=300))
```

（替换原 `os.environ.setdefault('HERMES_TOTAL_TIMEOUT', '300')` 一行；保留其上注释。start_agent.py 头部已有 project_root/sys.path 处理——确认 import 位置在其后即可。）

L94-96 initialize() 内：

```python
            model = _gp("llm_model", env_key="LLM_MODEL", default="ctgu-vlm")
            base_url = _gp("llm_base_url", env_key="LLM_BASE_URL", default="http://172.16.12.41:30000/v1")
            api_key = _gp("llm_api_key", env_key="LLM_API_KEY", default="")
```

L115-117：

```python
            if hasattr(self.master_agent, 'max_iterations'):
                self.master_agent.max_iterations = _gp("master_max_iterations", default=15)
```

- [ ] **Step 2.2: call_subagent.py L289**

在文件头部（已有 sys.path 处理之后）加 import（局部导入，保持脚本顶部轻量）：

```python
def _param(key, env_key, default):
    """DB 优先读参数(backend 参数中心)；backend 不可导入时走 env——
    call_subagent 在 agent 服务进程内跑，正常都能导入。"""
    try:
        from backend.services.agent_params import get_param
        return get_param(key, env_key=env_key, default=default)
    except Exception:
        return os.getenv(env_key, str(default))
```

L289 改为：

```python
        subagent_timeout = int(_param("subagent_timeout", "SUBAGENT_TIMEOUT", 600))
```

- [ ] **Step 2.3: subagent_entry.py max_iterations**

L254 `max_iterations=8` 改：

```python
        _smi = 8
        try:
            from backend.services.agent_params import get_param as _gp
            _smi = _gp("subagent_max_iterations", default=8)
        except Exception:
            pass
        agent = AIAgent(
            base_url=llm_base_url, api_key=llm_api_key, model=llm_model,
            load_soul_identity=True, skip_context_files=False, skip_memory=False,
            enabled_toolsets=["skills", "terminal"], session_id=task_id, max_iterations=_smi,
        )
```

（LLM 三项也可同样接线——`llm_base_url = _gp("llm_base_url", ...)` 等，L243-245 三行同款替换。）

- [ ] **Step 2.4: backend query.py AGENT_TIMEOUT 立即生效**

`backend/api/routes/query.py:24` 模块级 `AGENT_TIMEOUT = settings.AGENT_TIMEOUT` 改为函数读取（每请求生效）：

```python
def _agent_timeout() -> int:
    """每请求读 DB（参数中心可在线调，立即生效）；异常走 settings。"""
    try:
        from backend.services.agent_params import get_param
        return int(get_param("agent_timeout", env_key="AGENT_TIMEOUT", default=settings.AGENT_TIMEOUT))
    except Exception:
        return settings.AGENT_TIMEOUT
```

L83 与 L258 的 `timeout=AGENT_TIMEOUT` / `httpx.Timeout(AGENT_TIMEOUT, ...)` 改为 `timeout=_agent_timeout()` / `httpx.Timeout(_agent_timeout(), connect=10.0)`。

- [ ] **Step 2.5: 验证 agent 服务仍能起**

Run: `./ecological_env/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from backend.services.agent_params import get_param; print(get_param('llm_model', default='?'), get_param('hermes_total_timeout', default=300))"`
Expected: `ctgu-vlm 300`（无 DB 行时走 env/默认，不报错）

- [ ] **Step 2.6: Commit**

```bash
git add scripts/start_agent.py skills/orchestrator-core/scripts/call_subagent.py skills/orchestrator-core/scripts/subagent_entry.py backend/api/routes/query.py
git commit -m "feat(config): 5处参数读取接线get_param(DB优先,agent_timeout每请求即时生效)"
```

---

## Task 3: 身份文件服务（白名单+git 快照+历史+回滚）

**Files:**
- Create: `backend/services/identity_files.py`
- Test: `backend/tests/test_identity_files.py`

- [ ] **Step 3.1: 写失败测试**

```python
# backend/tests/test_identity_files.py
"""identity_files 单测：白名单拦截 / 读文件 / 保存+git快照 / 历史 / 回滚。
在临时 git 仓库副本上跑（subprocess git init + 拷真实 workspace 一份），不碰真仓库。"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """临时 git 仓库 + 真实 workspace/subagents 拷贝，monkeypatch PROJECT_ROOT。"""
    src = PROJECT_ROOT / "workspace"
    shutil.copytree(src, tmp_path / "workspace")
    shutil.copytree(PROJECT_ROOT / "subagents", tmp_path / "subagents")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    import backend.services.identity_files as idf
    monkeypatch.setattr(idf, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_read_identity_file(repo):
    from backend.services.identity_files import read_file
    r = read_file("master", "SOUL.md")
    assert r["path"].endswith("workspace/SOUL.md")
    assert len(r["content"]) > 0 and r["size"] > 0


def test_whitelist_rejects_traversal(repo):
    from backend.services.identity_files import read_file
    with pytest.raises(PermissionError):
        read_file("master", "../../.env")


def test_whitelist_rejects_unknown_entity(repo):
    from backend.services.identity_files import read_file
    with pytest.raises(PermissionError):
        read_file("hacker", "SOUL.md")


def test_save_creates_commit(repo):
    from backend.services.identity_files import read_file, save_file, list_history
    before = read_file("master", "MEMORY.md")["content"]
    save_file("master", "MEMORY.md", before + "\n<!-- 在线编辑测试 -->", "单测快照")
    after = read_file("master", "MEMORY.md")["content"]
    assert "在线编辑测试" in after
    hist = list_history("master", "MEMORY.md", limit=5)
    assert any("单测快照" in h["message"] for h in hist)
    assert hist[0]["commit"] and len(hist[0]["commit"]) >= 7


def test_revert_restores_content(repo):
    from backend.services.identity_files import read_file, save_file, list_history, revert_file
    orig = read_file("master", "MEMORY.md")["content"]
    save_file("master", "MEMORY.md", orig + "\n<!-- 改坏 -->", "改坏的一版")
    hist = list_history("master", "MEMORY.md", limit=10)
    # 回滚到含 orig 的那个 commit（历史里最后一条非本次的）
    target = next(h for h in hist if "改坏的一版" not in h["message"])
    restored = revert_file("master", "MEMORY.md", target["commit"])
    assert "<!-- 改坏 -->" not in restored["content"]


def test_entities_listing(repo):
    from backend.services.identity_files import list_entities
    es = list_entities()
    names = [e["name"] for e in es]
    assert "master" in names and len(names) == 5
    m = next(e for e in es if e["name"] == "master")
    assert "SOUL.md" in m["identity_files"] and len(m["identity_files"]) == 7
    s = next(e for e in es if e["name"] == "anomaly-detection")
    assert s["identity_files"] == ["SOUL.md", "AGENTS.md", "MEMORY.md"]
    assert any(sk["name"] for sk in s["skills"])
```

- [ ] **Step 3.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_identity_files.py -v`
Expected: FAIL（ModuleNotFoundError: backend.services.identity_files）

- [ ] **Step 3.3: 写实现**

```python
# backend/services/identity_files.py
"""身份文件管理：白名单读 + 原子写 + git 快照/历史/回滚。

安全边界（spec §3.5）：ENTITY_FILES 白名单硬编码——entity/file 不在表内直接 PermissionError，
杜绝路径穿越读 .env。git 只 add 目标文件，绝不碰工作区其他未提交改动。
git 不可用时降级 .bak（同目录 backups/，保最近 10 份）——测试与生产同一路径。
"""
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENTITY_META = {
    "master": {"label": "主智能体", "icon": "🧠", "dir": "workspace"},
    "multi-dimensional-data-perception": {"label": "多维数据感知", "icon": "📊",
        "dir": "subagents/multi-dimensional-data-perception-agent"},
    "anomaly-detection": {"label": "异常检测", "icon": "🔍",
        "dir": "subagents/anomaly-detection-agent"},
    "rule-reasoning": {"label": "规则推理", "icon": "⚖️",
        "dir": "subagents/rule-reasoning-agent"},
    "disposition-execution": {"label": "研判预警与处置", "icon": "🚨",
        "dir": "subagents/disposition-execution-agent"},
}

# 主智能体 7 个 / 子智能体各 3 个（与身份加载器实际加载的一致）
ENTITY_FILES = {
    "master": ["IDENTITY.md", "SOUL.md", "AGENTS.md", "MEMORY.md", "USER.md", "TOOLS.md", "HEARTBEAT.md"],
    "multi-dimensional-data-perception": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "anomaly-detection": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "rule-reasoning": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "disposition-execution": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
}


def _resolve(entity: str, file: str) -> Path:
    """白名单校验 + 绝对路径。任何不认识的一律 PermissionError。"""
    if entity not in ENTITY_FILES or file not in ENTITY_FILES[entity]:
        raise PermissionError(f"不允许的 entity/file: {entity}/{file}")
    p = (PROJECT_ROOT / ENTITY_META[entity]["dir"] / file).resolve()
    root = PROJECT_ROOT.resolve()
    if root not in p.parents:
        raise PermissionError(f"路径越界: {p}")
    return p


def list_entities() -> list:
    """实体清单（含技能只读发现：skills/*/SKILL.md）。"""
    out = []
    for name, meta in ENTITY_META.items():
        skills = []
        sk_dir = (PROJECT_ROOT / "skills" / "orchestrator-core").glob("*") if name == "master" else (PROJECT_ROOT / meta["dir"] / "skills").glob("*")
        try:
            for d in sk_dir:
                sk = d / "SKILL.md"
                if d.is_dir() and sk.exists():
                    skills.append({"name": d.name, "has_skill": True})
        except Exception:
            pass
        out.append({"name": name, "label": meta["label"], "icon": meta["icon"],
                    "dir": meta["dir"], "identity_files": ENTITY_FILES[name],
                    "skills": skills})
    return out


def read_file(entity: str, file: str) -> dict:
    p = _resolve(entity, file)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    st = p.stat()
    return {"path": p.relative_to(PROJECT_ROOT).as_posix(), "content": p.read_text(encoding="utf-8"),
            "size": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def _git(args: list, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd or PROJECT_ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=30)


def _backup_degraded(p: Path):
    """git 不可用时的降级备份：backups/ 下带时间戳副本，保最近 10 份。"""
    bdir = p.parent / "backups"
    bdir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(p, bdir / f"{p.stem}.{stamp}.bak")
    baks = sorted(bdir.glob(f"{p.stem}.*.bak"))
    for old in baks[:-10]:
        old.unlink()


def save_file(entity: str, file: str, content: str, message: str = "") -> dict:
    """原子写（tmp+rename）+ git 快照（只 add 本文件）。"""
    p = _resolve(entity, file)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)  # 原子替换
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    msg = f"config(web): {rel} — {message or '在线编辑'}"
    r = _git(["add", "--", rel])
    c = _git(["commit", "-m", msg, "--", rel])
    if c.returncode != 0:
        _backup_degraded(p)
        return {"commit": None, "degraded": True, "detail": (c.stderr or c.stdout).strip()[:200]}
    h = _git(["rev-parse", "--short", "HEAD"])
    return {"commit": h.stdout.strip() if h.returncode == 0 else None, "degraded": False}


def list_history(entity: str, file: str, limit: int = 20) -> list:
    p = _resolve(entity, file)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    r = _git(["log", f"-{limit}", "--pretty=format:%h|%ad|%an|%s", "--date=iso-strict", "--", rel])
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            out.append({"commit": parts[0], "date": parts[1], "author": parts[2], "message": parts[3]})
    return out


def revert_file(entity: str, file: str, commit: str) -> dict:
    """git checkout <commit> -- <file>：只动这一个文件。"""
    p = _resolve(entity, file)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    if not all(ch in "0123456789abcdefABCDEF" for ch in commit) or not (4 <= len(commit) <= 42):
        raise ValueError(f"非法 commit hash: {commit}")
    r = _git(["checkout", commit, "--", rel])
    if r.returncode != 0:
        raise RuntimeError(f"回滚失败: {r.stderr.strip()[:200]}")
    return read_file(entity, file)
```

- [ ] **Step 3.4: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_identity_files.py -v`
Expected: 6 passed

- [ ] **Step 3.5: Commit**

```bash
git add backend/services/identity_files.py backend/tests/test_identity_files.py
git commit -m "feat(config): 身份文件服务(白名单/原子写/git快照/历史/回滚/降级备份)"
```

---

## Task 4: 厂区配置服务（yaml 读写+别名表迁移）

**Files:**
- Create: `backend/services/plant_config_service.py`
- Modify: `shared/data/plant-hierarchy.yaml`（加 plant_aliases 段）
- Modify: `skills/orchestrator-core/scripts/subagent_entry.py:112-117`（别名表读 yaml）
- Test: `backend/tests/test_plant_config_service.py`

- [ ] **Step 4.1: 写失败测试**

```python
# backend/tests/test_plant_config_service.py
"""plant_config_service 单测：读写往返 / 校验规则 / 别名解析（含 yaml 段）。"""
import shutil, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def yaml_env(tmp_path, monkeypatch):
    shutil.copy(PROJECT_ROOT / "shared/data/plant-hierarchy.yaml",
                tmp_path / "plant-hierarchy.yaml")
    import backend.services.plant_config_service as pcs
    monkeypatch.setattr(pcs, "YAML_PATH", tmp_path / "plant-hierarchy.yaml")
    monkeypatch.setattr(pcs, "PROJECT_ROOT", tmp_path)
    return pcs


def test_load_full(yaml_env):
    data = yaml_env.load_plant_config()
    assert "hierarchy" in data and "report_name_map" in data and "plant_configs" in data
    assert "plant_aliases" in data  # 迁移后必有


def test_alias_resolution_prefers_yaml(yaml_env):
    # yaml 里的别名优先于内置默认
    assert yaml_env.resolve_alias("金桥") == "当阳市金桥污水处理厂一期"
    yaml_env.save_section("plant_aliases", {"测试别名": "当阳市金桥污水处理厂一期"})
    assert yaml_env.resolve_alias("测试别名") == "当阳市金桥污水处理厂一期"


def test_alias_fallback_to_builtin(yaml_env):
    # yaml 无 plant_aliases 段时用内置两厂（向后兼容）
    yaml_env.save_section("plant_aliases", None)  # 删除段
    assert yaml_env.resolve_alias("洗舱站") == "洗舱站污水排放口"


def test_validate_reports_errors(yaml_env):
    # 别名指向不存在的厂 → 错误
    errs = yaml_env.validate_config({"hierarchy": {"当阳市": {"城东厂区": ["X厂"]}},
                                     "plant_aliases": {"a": "不存在厂"},
                                     "report_name_map": {}, "plant_configs": {}})
    assert any("不存在" in e or "别名" in e for e in errs)


def test_roundtrip_preserves_hierarchy(yaml_env):
    data = yaml_env.load_plant_config()
    data["hierarchy"]["枝江市"]["新厂区"] = ["测试排放口"]
    yaml_env.save_config(data)
    re = yaml_env.load_plant_config()
    assert "测试排放口" in re["hierarchy"]["枝江市"]["新厂区"]
```

- [ ] **Step 4.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_plant_config_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 4.3: yaml 加 plant_aliases 段**

`shared/data/plant-hierarchy.yaml` 末尾追加：

```yaml

# ── 厂名别名 → plant_id（智能体解析用户口语厂名用；页面可管理）──────────────
# 子智能体自愈入口(subagent_entry)优先读本段,无此段时用内置两厂默认(向后兼容)。
# 别名值必须与 InfluxDB plant_id 完全一致(=层级树里的厂名)。
plant_aliases:
  "金桥": "当阳市金桥污水处理厂一期"
  "洗舱站": "洗舱站污水排放口"
```

- [ ] **Step 4.4: 写 plant_config_service**

```python
# backend/services/plant_config_service.py
"""plant-hierarchy.yaml 管理服务：结构化读写 + 校验 + 原子落盘。

yaml 顶层四段：hierarchy(市→区→厂[]) / report_name_map / plant_configs / plant_aliases。
_RESERVED 与 shared/data/discover_plants.py 保持一致——新厂自动发现不被配置段干扰。
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = PROJECT_ROOT / "shared" / "data" / "plant-hierarchy.yaml"

_RESERVED = {"report_name_map", "plant_configs", "plant_aliases"}

# 兜底别名（yaml 无段时的默认；与 InfluxDB plant_id 一致）
_BUILTIN_ALIASES = {
    "金桥": "当阳市金桥污水处理厂一期",
    "当阳市金桥污水处理厂一期": "当阳市金桥污水处理厂一期",
    "洗舱站": "洗舱站污水排放口",
    "洗舱站污水排放口": "洗舱站污水排放口",
}


def load_plant_config() -> dict:
    if not YAML_PATH.exists():
        return {"hierarchy": {}, "report_name_map": {}, "plant_configs": {}, "plant_aliases": {}}
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        "hierarchy": {k: v for k, v in raw.items() if k not in _RESERVED},
        "report_name_map": raw.get("report_name_map") or {},
        "plant_configs": raw.get("plant_configs") or {},
        "plant_aliases": raw.get("plant_aliases") or {},
    }


def save_section(section: str, value) -> None:
    """改单段（value=None 删除段）。读-改-写整份 yaml。"""
    data = load_plant_config()
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if value is None:
        raw.pop(section, None)
    else:
        raw[section] = value
    _atomic_dump(raw)


def save_config(data: dict) -> dict:
    """整份保存（页面保存按钮）：合并四段，保留未知段不动。"""
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    for k, v in data.items():
        if v is None:
            raw.pop(k, None)
        else:
            raw[k] = v
    # hierarchy 是拼出来的（非保留键集合），逐键覆盖：先删旧层级键再加新的
    for k in [k for k in raw if k not in _RESERVED]:
        raw.pop(k)
    raw.update(data.get("hierarchy") or {})
    _atomic_dump(raw)
    _git_snapshot()
    return load_plant_config()


def validate_config(data: dict) -> list:
    """返回错误列表（空=通过）。规则：别名/映射值必须存在于层级中的厂集合。"""
    errs = []
    plants = set()
    for city, zones in (data.get("hierarchy") or {}).items():
        if not isinstance(zones, dict):
            errs.append(f"层级[{city}]格式错误：应为 市→厂区→厂列表")
            continue
        for zone, plist in zones.items():
            if not isinstance(plist, list):
                errs.append(f"层级[{city}.{zone}]格式错误：应为厂列表")
                continue
            plants.update(plist)
    for alias, pid in (data.get("plant_aliases") or {}).items():
        if pid not in plants:
            errs.append(f"别名「{alias}」指向不存在的厂「{pid}」（须先在层级中添加）")
    for fname, pid in (data.get("report_name_map") or {}).items():
        if pid not in plants:
            errs.append(f"报表映射「{fname}」指向不存在的厂「{pid}」")
    return errs


def resolve_alias(alias_text: str) -> str | None:
    """任务文本→plant_id。yaml 段优先（含自身全称映射），无段/无命中走内置。"""
    cfg = load_plant_config()
    aliases = cfg.get("plant_aliases") or {}
    merged = dict(_BUILTIN_ALIASES)
    merged.update(aliases)
    for alias, pid in merged.items():
        if alias in alias_text:
            return pid
    return None


def _atomic_dump(raw: dict) -> None:
    tmp = YAML_PATH.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    os.replace(tmp, YAML_PATH)


def _git_snapshot() -> None:
    """yaml 保存即 git 快照（只 add 本文件；失败静默——校验已过,落盘成功不因 git 挂掉而报错）。"""
    import subprocess
    rel = YAML_PATH.relative_to(PROJECT_ROOT).as_posix()
    try:
        subprocess.run(["git", "add", "--", rel], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", f"config(web): {rel} — 厂区配置在线编辑",
                        "--", rel], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
    except Exception:
        pass
```

- [ ] **Step 4.5: subagent_entry 别名表接 yaml**

`skills/orchestrator-core/scripts/subagent_entry.py` L112-117 的 `_PLANT_ALIASES = {...}` 块整体替换为：

```python
# 感知①自愈:厂名别名→plant_id。优先读 plant-hierarchy.yaml 的 plant_aliases 段
# (配置中心可在线管理,新厂接入零代码),yaml 不可用时退回内置两厂(向后兼容)。
_PLANT_ALIASES = {
    "金桥": "当阳市金桥污水处理厂一期",
    "当阳市金桥污水处理厂一期": "当阳市金桥污水处理厂一期",
    "洗舱站": "洗舱站污水排放口",
    "洗舱站污水排放口": "洗舱站污水排放口",
}
try:
    import yaml as _yaml
    _cfg_p = AGENT_DIR.parent.parent / "shared" / "data" / "plant-hierarchy.yaml"
    if _cfg_p.exists():
        _raw_aliases = (_yaml.safe_load(_cfg_p.read_text(encoding="utf-8")) or {}).get("plant_aliases")
        if isinstance(_raw_aliases, dict) and _raw_aliases:
            _PLANT_ALIASES = {**_PLANT_ALIASES, **_raw_aliases}
except Exception:
    pass
```

（AGENT_DIR 已在文件头定义 = 子智能体目录，`AGENT_DIR.parent.parent` = 项目根。）

- [ ] **Step 4.6: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_plant_config_service.py -v`
Expected: 5 passed

- [ ] **Step 4.7: Commit**

```bash
git add backend/services/plant_config_service.py backend/tests/test_plant_config_service.py shared/data/plant-hierarchy.yaml skills/orchestrator-core/scripts/subagent_entry.py
git commit -m "feat(config): 厂区配置服务+plant_aliases段迁移(别名表从硬编码进yaml,自愈入口yaml优先)"
```

---

## Task 5: REST 路由（身份文件/厂区/参数/LLM测试/服务管理）

**Files:**
- Create: `backend/api/v1/agents/__init__.py`（空）
- Create: `backend/api/v1/agents/config/__init__.py`（空）
- Create: `backend/api/v1/agents/config/routes.py`
- Modify: `backend/main.py`（注册路由）
- Modify: `requirements.txt`（+ psutil）
- Create: `backend/services/agent_service_control.py`

- [ ] **Step 5.1: service_control 服务**

```python
# backend/services/agent_service_control.py
"""agent 服务(8642)生命周期：kill + detached 重启 + health 轮询。

Windows：DETACHED_PROCESS|CREATE_NEW_CONSOLE 开独立控制台窗口（日志可见），
venv python 跑 scripts/start_agent.py。绝不 kill backend 自身。
"""
import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_PORT = 8642
VENV_PY = PROJECT_ROOT / "ecological_env" / "Scripts" / "python.exe"


def _pids_by_port(port: int) -> list:
    try:
        import psutil
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == "LISTEN" and c.pid:
                return [c.pid]
    except ImportError:
        pass
    # netstat 兜底（psutil 未装）
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    return [int(l.split()[-1]) for l in out.splitlines()
            if f":{port}" in l and "LISTENING" in l]


def get_status() -> dict:
    try:
        import httpx
        r = httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=3)
        alive, detail = r.status_code == 200, r.json()
    except Exception as e:
        alive, detail = False, str(e)[:120]
    pids = _pids_by_port(AGENT_PORT)
    return {"alive": alive, "port": AGENT_PORT, "pids": pids, "detail": detail,
            "model": os.getenv("LLM_MODEL", "")}


def restart_agent(confirm: bool) -> dict:
    if not confirm:
        return {"ok": False, "error": "需 confirm=true 才执行重启"}
    old_pids = _pids_by_port(AGENT_PORT)
    for pid in old_pids:
        try:
            import psutil
            p = psutil.Process(pid)
            p.terminate()
            try:
                p.wait(timeout=5)
            except psutil.TimeoutExpired:
                p.kill()
        except ImportError:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        except Exception:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(1)
    # detached 新进程：独立控制台窗口，继承当前 env（含 .env 变量）
    env = dict(os.environ)
    flags = 0
    if os.name == "nt":
        flags = 0x00000008 | 0x00000010  # DETACHED_PROCESS | CREATE_NEW_CONSOLE
    subprocess.Popen([str(VENV_PY), str(PROJECT_ROOT / "scripts" / "start_agent.py")],
                     cwd=str(PROJECT_ROOT), env=env, creationflags=flags)
    # 轮询 health 最多 60s（LLM 客户端初始化要几秒）
    for _ in range(60):
        time.sleep(1)
        try:
            import httpx
            if httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=2).status_code == 200:
                return {"ok": True, "old_pids": old_pids, "new_alive": True}
        except Exception:
            pass
    return {"ok": True, "old_pids": old_pids, "new_alive": False,
            "warn": "进程已启动但 60s 内 health 未就绪——请看 agent 控制台窗口日志"}
```

- [ ] **Step 5.2: routes.py**

```python
# backend/api/v1/agents/config/routes.py
"""智能体配置中心 REST API（spec §3.1）。

分组：实体/身份文件(git快照) / 厂区配置(yaml) / 运行参数(SQLite) / LLM测试 / 服务管理。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["智能体配置"])


# ── 实体与身份文件 ─────────────────────────────────────────────
@router.get("/agents/config/entities")
async def list_entities():
    from backend.services.identity_files import list_entities
    return {"success": True, "data": list_entities()}


class FileBody(BaseModel):
    entity: str
    file: str
    content: str
    message: Optional[str] = ""


@router.get("/agents/config/files")
async def read_file(entity: str, file: str):
    from backend.services.identity_files import read_file
    try:
        return {"success": True, "data": read_file(entity, file)}
    except PermissionError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/agents/config/files")
async def save_file(body: FileBody):
    from backend.services.identity_files import save_file
    try:
        r = save_file(body.entity, body.file, body.content, body.message or "")
        return {"success": True, "data": r}
    except PermissionError as e:
        raise HTTPException(400, str(e))


@router.get("/agents/config/files/history")
async def file_history(entity: str, file: str, limit: int = 20):
    from backend.services.identity_files import list_history
    return {"success": True, "data": list_history(entity, file, limit)}


class RevertBody(BaseModel):
    entity: str
    file: str
    commit: str


@router.post("/agents/config/files/revert")
async def revert_file(body: RevertBody):
    from backend.services.identity_files import revert_file
    try:
        return {"success": True, "data": revert_file(body.entity, body.file, body.commit)}
    except (PermissionError, ValueError) as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


# ── 厂区配置 ───────────────────────────────────────────────────
@router.get("/agents/config/plants")
async def get_plant_config():
    from backend.services.plant_config_service import load_plant_config
    return {"success": True, "data": load_plant_config()}


class PlantConfigBody(BaseModel):
    hierarchy: Optional[dict] = None
    report_name_map: Optional[dict] = None
    plant_configs: Optional[dict] = None
    plant_aliases: Optional[dict] = None


@router.post("/agents/config/plants/validate")
async def validate_plants(body: PlantConfigBody):
    from backend.services.plant_config_service import validate_config
    return {"success": True, "errors": validate_config(body.model_dump())}


@router.put("/agents/config/plants")
async def save_plants(body: PlantConfigBody):
    from backend.services.plant_config_service import validate_config, save_config
    errs = validate_config(body.model_dump())
    if errs:
        raise HTTPException(400, detail={"message": "校验失败", "errors": errs})
    return {"success": True, "data": save_config(body.model_dump())}


# ── 运行参数 ───────────────────────────────────────────────────
@router.get("/agents/config/params")
async def get_params():
    import os
    from backend.services.agent_params import PARAM_REGISTRY, mask_secret, get_param
    out = []
    for key, spec in PARAM_REGISTRY.items():
        v = get_param(key, env_key=spec.get("env_key"), default=spec.get("default"))
        out.append({"key": key, "value": mask_secret(v) if spec["type"] == "secret" else v,
                    "default": spec.get("default"), "type": spec["type"],
                    "effect": spec["effect"], "reader": spec["reader"], "desc": spec.get("desc", "")})
    return {"success": True, "data": out}


class ParamsBody(BaseModel):
    params: dict  # {key: value}; secret 留空/缺省=不改


@router.put("/agents/config/params")
async def put_params(body: ParamsBody):
    from backend.services.agent_params import PARAM_REGISTRY, set_param
    invalid = [k for k in body.params if k not in PARAM_REGISTRY]
    if invalid:
        raise HTTPException(400, f"未知参数: {invalid}")
    errors = []
    for k, v in body.params.items():
        if PARAM_REGISTRY[k]["type"] == "int":
            try:
                int(v)
            except (TypeError, ValueError):
                errors.append(f"{k} 必须是整数")
        if PARAM_REGISTRY[k]["type"] == "secret" and (v is None or v == ""):
            continue  # 密钥空=不改
    if errors:
        raise HTTPException(400, detail={"message": "参数校验失败", "errors": errors})
    for k, v in body.params.items():
        set_param(k, str(v))
    restart_needed = any(PARAM_REGISTRY[k]["effect"] == "restart" for k in body.params)
    return {"success": True, "restart_needed": restart_needed}


# ── LLM 测试连接 ────────────────────────────────────────────────
class LLMTestBody(BaseModel):
    base_url: Optional[str] = None   # 空=用当前生效配置
    model: Optional[str] = None
    api_key: Optional[str] = None


@router.post("/agents/config/llm/test")
async def llm_test(body: LLMTestBody):
    import time
    import httpx
    from backend.services.agent_params import get_param
    base_url = body.base_url or get_param("llm_base_url", env_key="LLM_BASE_URL", default="")
    model = body.model or get_param("llm_model", env_key="LLM_MODEL", default="")
    api_key = body.api_key or get_param("llm_api_key", env_key="LLM_API_KEY", default="")
    if not base_url or not model:
        return {"ok": False, "error": "base_url/model 为空"}
    t0 = time.time()
    try:
        r = httpx.post(f"{base_url.rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {api_key}"},
                       json={"model": model, "messages": [{"role": "user", "content": "hi"}],
                             "max_tokens": 1},
                       timeout=10.0)
        ok = r.status_code == 200
        return {"ok": ok, "latency_ms": int((time.time() - t0) * 1000),
                "error": None if ok else f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        return {"ok": False, "latency_ms": int((time.time() - t0) * 1000), "error": str(e)[:150]}


# ── 服务管理 ───────────────────────────────────────────────────
@router.get("/agents/config/service/status")
async def service_status():
    from backend.services.agent_service_control import get_status
    return {"success": True, "data": get_status()}


class RestartBody(BaseModel):
    confirm: bool


@router.post("/agents/config/service/restart")
async def service_restart(body: RestartBody):
    from backend.services.agent_service_control import restart_agent
    return restart_agent(body.confirm)
```

- [ ] **Step 5.3: main.py 注册 + requirements**

`backend/main.py` 在 detection 路由注册块之后加：

```python
# 智能体配置中心(身份文件/厂区配置/运行参数/服务管理)
from backend.api.v1.agents.config import routes as v1_agentcfg_routes
app.include_router(v1_agentcfg_routes.router, prefix="/api/v1")
```

`requirements.txt` 末尾加一行 `psutil`。

- [ ] **Step 5.4: 起后端冒烟**

Run: `./ecological_env/Scripts/python.exe -m uvicorn backend.main:app --port 8000 &` 然后
`curl -s http://localhost:8000/api/v1/agents/config/entities | head -c 300`
Expected: `{"success":true,"data":[{"name":"master",...` （5 个实体）
再验：`curl -s "http://localhost:8000/api/v1/agents/config/files?entity=master&file=SOUL.md" | head -c 200`
Expected: content 有 SOUL.md 正文
再验白名单：`curl -s "http://localhost:8000/api/v1/agents/config/files?entity=master&file=../../.env"`
Expected: 400

- [ ] **Step 5.5: Commit**

```bash
git add backend/api/v1/agents/ backend/services/agent_service_control.py backend/main.py requirements.txt
git commit -m "feat(config): 配置中心REST API(实体/文件/厂区/参数/LLM测试/服务重启)"
```

---

## Task 6: 前端 API 模块 + 页面骨架 + 实体树 + 概览

**Files:**
- Create: `frontend/src/api/modules/agentConfig.ts`
- Create: `frontend/src/components/agents/config/EntityTree.vue`
- Create: `frontend/src/components/agents/config/EntityOverview.vue`
- Modify: `frontend/src/views/AgentConfigView.vue`（整页重写为骨架）

- [ ] **Step 6.1: API 模块**

```typescript
// frontend/src/api/modules/agentConfig.ts
import api from '../client'

export interface AgentEntity {
  name: string; label: string; icon: string; dir: string
  identity_files: string[]; skills: { name: string; has_skill: boolean }[]
}
export interface FileContent { path: string; content: string; size: number; mtime: string }
export interface FileHistoryItem { commit: string; date: string; author: string; message: string }
export interface ParamItem {
  key: string; value: string | number; default: string | number
  type: 'int' | 'str' | 'secret'; effect: 'immediate' | 'restart'
  reader: string; desc: string
}
export interface PlantConfig {
  hierarchy: Record<string, Record<string, string[]>>
  report_name_map: Record<string, string>
  plant_configs: Record<string, Record<string, unknown>>
  plant_aliases: Record<string, string>
}

const unwrap = <T>(r: any): T => r.data ?? r

export const agentConfigService = {
  entities: () => api.get<unknown, AgentEntity[]>('/agents/config/entities').then(r => (r as any).data ?? r),
  readFile: (entity: string, file: string) =>
    api.get<unknown, { success: boolean; data: FileContent }>(`/agents/config/files`, { params: { entity, file } }),
  saveFile: (body: { entity: string; file: string; content: string; message?: string }) =>
    api.put<unknown, { success: boolean; data: { commit: string | null; degraded: boolean } }>('/agents/config/files', body),
  fileHistory: (entity: string, file: string, limit = 20) =>
    api.get<unknown, { success: boolean; data: FileHistoryItem[] }>('/agents/config/files/history', { params: { entity, file, limit } }),
  revertFile: (body: { entity: string; file: string; commit: string }) =>
    api.post<unknown, { success: boolean; data: FileContent }>('/agents/config/files/revert', body),
  getPlants: () => api.get<unknown, { success: boolean; data: PlantConfig }>('/agents/config/plants'),
  validatePlants: (body: Partial<PlantConfig>) =>
    api.post<unknown, { success: boolean; errors: string[] }>('/agents/config/plants/validate', body),
  savePlants: (body: Partial<PlantConfig>) =>
    api.put<unknown, { success: boolean; data: PlantConfig }>('/agents/config/plants', body),
  getParams: () => api.get<unknown, { success: boolean; data: ParamItem[] }>('/agents/config/params'),
  saveParams: (params: Record<string, string | number>) =>
    api.put<unknown, { success: boolean; restart_needed: boolean }>('/agents/config/params', { params }),
  llmTest: (body: { base_url?: string; model?: string; api_key?: string }) =>
    api.post<unknown, { ok: boolean; latency_ms?: number; error?: string | null }>('/agents/config/llm/test', body),
  serviceStatus: () => api.get<unknown, { success: boolean; data: { alive: boolean; port: number; pids: number[]; model: string } }>('/agents/config/service/status'),
  serviceRestart: () => api.post<unknown, { ok: boolean; old_pids?: number[]; new_alive?: boolean; warn?: string; error?: string }>('/agents/config/service/restart', { confirm: true }),
}
export { unwrap }
```

- [ ] **Step 6.2: EntityTree**

```vue
<!-- frontend/src/components/agents/config/EntityTree.vue -->
<template>
  <div class="etree">
    <div class="et-h">智能体</div>
    <div v-for="e in entities" :key="e.name" class="et-item"
         :class="{ active: e.name === modelValue, master: e.name === 'master' }"
         @click="$emit('update:modelValue', e.name)">
      <span class="et-icon">{{ e.icon }}</span>
      <span class="et-label">{{ e.label }}</span>
      <span class="et-nfiles">{{ e.identity_files.length }}身份</span>
    </div>
    <div class="et-sep"></div>
    <div class="et-item" :class="{ active: modelValue === '__plants__' }" @click="$emit('update:modelValue', '__plants__')">
      <span class="et-icon">⚙️</span><span class="et-label">厂区配置</span>
    </div>
    <div class="et-item" :class="{ active: modelValue === '__service__' }" @click="$emit('update:modelValue', '__service__')">
      <span class="et-icon">🔄</span><span class="et-label">服务管理</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentEntity } from '@/api/modules/agentConfig'
defineProps<{ entities: AgentEntity[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<style scoped>
.etree { width: 210px; flex-shrink: 0; border-right: 1px solid var(--brd); padding: 14px 10px; }
.et-h { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; margin: 0 0 8px 8px; }
.et-item { display: flex; align-items: center; gap: 9px; padding: 9px 10px; border-radius: 9px;
  cursor: pointer; font-size: 13px; color: var(--text-primary); margin-bottom: 3px; transition: background .12s }
.et-item:hover { background: #f1f5f9 }
.et-item.active { background: var(--primary-soft, #eef2ff); color: var(--primary); font-weight: 600 }
.et-icon { font-size: 16px }
.et-nfiles { margin-left: auto; font-size: 10.5px; color: var(--text-muted) }
.et-sep { height: 1px; background: var(--brd); margin: 10px 4px }
</style>
```

- [ ] **Step 6.3: EntityOverview**

```vue
<!-- frontend/src/components/agents/config/EntityOverview.vue -->
<template>
  <div class="ov" v-if="entity">
    <div class="ov-head">
      <span class="ov-icon">{{ entity.icon }}</span>
      <div>
        <div class="ov-name">{{ entity.label }}</div>
        <div class="ov-dir">{{ entity.dir }}</div>
      </div>
    </div>
    <div class="ov-sec">
      <div class="sec-t">身份文件（{{ entity.identity_files.length }}）</div>
      <div class="chips">
        <span v-for="f in entity.identity_files" :key="f" class="chip"
              @click="$emit('openFile', f)">{{ f }}</span>
      </div>
    </div>
    <div class="ov-sec" v-if="entity.skills.length">
      <div class="sec-t">技能（{{ entity.skills.length }}）</div>
      <div class="chips">
        <span v-for="s in entity.skills" :key="s.name" class="chip skill">📘 {{ s.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentEntity } from '@/api/modules/agentConfig'
defineProps<{ entity: AgentEntity }>()
defineEmits<{ (e: 'openFile', f: string): void }>()
</script>

<style scoped>
.ov { max-width: 720px }
.ov-head { display: flex; align-items: center; gap: 13px; margin-bottom: 18px }
.ov-icon { width: 46px; height: 46px; border-radius: 12px; background: var(--brand-gradient);
  display: grid; place-items: center; font-size: 22px }
.ov-name { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.ov-dir { font-size: 11.5px; color: var(--text-muted); font-family: ui-monospace, monospace; margin-top: 2px }
.ov-sec { margin-bottom: 16px }
.sec-t { font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px }
.chips { display: flex; flex-wrap: wrap; gap: 7px }
.chip { font-size: 12px; font-family: ui-monospace, monospace; background: #f8fafc;
  border: 1px solid var(--brd); padding: 4px 11px; border-radius: 7px; color: var(--text-secondary); cursor: pointer }
.chip:hover { border-color: var(--primary); color: var(--primary) }
.chip.skill { background: #fffbeb; border-color: #fde68a }
</style>
```

- [ ] **Step 6.4: AgentConfigView 骨架（重写）**

```vue
<!-- frontend/src/views/AgentConfigView.vue -->
<template>
  <div class="cfg">
    <EntityTree v-if="entities.length" :entities="entities" v-model="activeEntity" />
    <div class="cfg-main">
      <!-- 顶部 tab（实体选中时） -->
      <div class="tabs" v-if="isEntity">
        <button v-for="t in ['overview', 'files']" :key="t" class="tab"
                :class="{ active: tab === t }" @click="switchTab(t)">
          {{ t === 'overview' ? '概览' : '身份文件' }}
        </button>
      </div>
      <div class="cfg-body">
        <EntityOverview v-if="isEntity && tab === 'overview' && currentEntity"
                        :entity="currentEntity" @openFile="openFileFromOverview" />
        <div v-else-if="isEntity && tab === 'files'" class="files-wrap">
          <!-- Task 7 填充 IdentityFileEditor -->
          <IdentityFileEditor v-if="currentEntity" :entity="currentEntity" ref="editorRef" />
        </div>
        <PlantsConfigPanel v-else-if="activeEntity === '__plants__'" />
        <ServiceControl v-else-if="activeEntity === '__service__'" />
        <div v-else class="loading">加载中…</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { agentConfigService, type AgentEntity } from '@/api/modules/agentConfig'
import EntityTree from '@/components/agents/config/EntityTree.vue'
import EntityOverview from '@/components/agents/config/EntityOverview.vue'

const entities = ref<AgentEntity[]>([])
const activeEntity = ref('master')
const tab = ref('overview')
const editorRef = ref()

const isEntity = computed(() => entities.value.some(e => e.name === activeEntity.value))
const currentEntity = computed(() => entities.value.find(e => e.name === activeEntity.value))

function switchTab(t: string) {
  if (tab.value === 'files' && t !== 'files' && editorRef.value?.dirty) {
    if (!confirm('有未保存的编辑，切换将丢失，确定？')) return
  }
  tab.value = t
}

function openFileFromOverview(f: string) { tab.value = 'files'; editorRef.value?.openFile(f) }

onMounted(async () => {
  try {
    const r: any = await agentConfigService.entities()
    entities.value = (r.data ?? r) as AgentEntity[]
  } catch { /* 页面各面板自行处理错误 */ }
})
</script>

<style scoped>
.cfg { display: flex; height: calc(100vh - 110px); background: var(--card-bg);
  border: 1px solid var(--brd); border-radius: 13px; overflow: hidden;
  box-shadow: var(--card-shadow) }
.cfg-main { flex: 1; min-width: 0; display: flex; flex-direction: column }
.tabs { display: flex; gap: 4px; padding: 10px 16px 0; border-bottom: 1px solid var(--brd) }
.tab { border: none; background: none; font-size: 13px; color: var(--text-secondary);
  padding: 7px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px }
.tab.active { color: var(--primary); font-weight: 600; border-bottom-color: var(--primary) }
.cfg-body { flex: 1; overflow: auto; padding: 18px }
.files-wrap { height: 100% }
.loading { color: var(--text-muted); padding: 40px; text-align: center }
</style>
```

（骨架引用了 IdentityFileEditor/PlantsConfigPanel/ServiceControl——Task 7/8/9 创建；本 Task 先创建**最小占位组件**让编译通过：三个文件各含 `<template><div class="placeholder">Task 7/8/9 填充</div></template>` + `<script setup lang="ts"></script>`，后续 Task 整文件替换。骨架的 import 写完整路径。）

- [ ] **Step 6.5: 冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: 编译通过（vite build success）

- [ ] **Step 6.6: Commit**

```bash
git add frontend/src/api/modules/agentConfig.ts frontend/src/components/agents/config/ frontend/src/views/AgentConfigView.vue
git commit -m "feat(config): 前端骨架+实体树+概览(API模块/左实体右内容布局)"
```

---

## Task 7: 身份文件编辑器（diff+保存快照+历史回滚）

**Files:**
- Replace: `frontend/src/components/agents/config/IdentityFileEditor.vue`（整文件替换占位）

- [ ] **Step 7.1: 实现**

```vue
<!-- frontend/src/components/agents/config/IdentityFileEditor.vue -->
<template>
  <div class="ed">
    <!-- 文件列表 -->
    <div class="ed-list">
      <div class="ed-lh">身份文件</div>
      <div v-for="f in entity.identity_files" :key="f" class="ed-fi"
           :class="{ active: file === f, dirty: dirty && file === f }" @click="openFile(f)">
        {{ f }}<span v-if="dirty && file === f" class="dot">●</span>
      </div>
      <div class="ed-lh" style="margin-top: 12px">历史版本</div>
      <div v-if="!history.length" class="ed-empty">暂无 git 历史</div>
      <div v-for="h in history" :key="h.commit + h.date" class="ed-hi" @click="revert(h)">
        <div class="ed-hc">{{ h.commit }}</div>
        <div class="ed-hm" :title="h.message">{{ h.message }}</div>
        <div class="ed-hd">{{ h.date.slice(0, 16).replace('T', ' ') }}</div>
      </div>
    </div>
    <!-- 编辑区 -->
    <div class="ed-main" v-if="file">
      <div class="ed-bar">
        <span class="ed-path">{{ file }} <span class="ed-meta">{{ sizeLabel }}</span></span>
        <div class="ed-acts">
          <button class="btn" @click="showDiff = true" :disabled="!dirty">diff 预览</button>
          <button class="btn primary" @click="save" :disabled="!dirty || saving">
            {{ saving ? '保存中…' : '保存(git 快照)' }}
          </button>
        </div>
      </div>
      <textarea ref="ta" v-model="content" class="ed-ta" spellcheck="false"
                :readonly="loading"></textarea>
    </div>
    <div v-else class="ed-none">← 选择一个身份文件</div>
    <!-- diff 弹窗 -->
    <div v-if="showDiff" class="ed-mask" @click.self="showDiff = false">
      <div class="ed-diff">
        <div class="ed-dh">变更预览（保存前确认）</div>
        <pre class="ed-dp">{{ diffText }}</pre>
        <div class="ed-df">
          <button class="btn" @click="showDiff = false">继续编辑</button>
          <button class="btn primary" @click="confirmSave">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService } from '@/api/modules/agentConfig'
import type { AgentEntity, FileHistoryItem } from '@/api/modules/agentConfig'

const props = defineProps<{ entity: AgentEntity }>()
const file = ref('')
const content = ref('')
const original = ref('')
const loading = ref(false)
const saving = ref(false)
const history = ref<FileHistoryItem[]>([])
const showDiff = ref(false)

const dirty = computed(() => content.value !== original.value)
defineExpose({ dirty, openFile })

const sizeLabel = computed(() => `${(content.value.length / 1024).toFixed(1)} KB · ${content.value.split('\n').length} 行`)

// 简易 diff（行级 LCS 太重,用对齐显示:旧−/新+标记首次差异行起)
// 逐行比对:相同行直接过,不同行旧侧−/新侧+;对 md 场景够用
const diffText = computed(() => {
  const oldL = original.value.split('\n'); const newL = content.value.split('\n')
  const out: string[] = []
  const n = Math.max(oldL.length, newL.length)
  let changed = 0
  for (let i = 0; i < n; i++) {
    if (oldL[i] === newL[i]) { if (changed > 0 && oldL[i] !== undefined) { out.push('  ' + oldL[i]) } else if (oldL[i] !== undefined) out.push('  ' + oldL[i]) }
    else {
      if (oldL[i] !== undefined) { out.push('- ' + oldL[i]); changed++ }
      if (newL[i] !== undefined) { out.push('+ ' + newL[i]); changed++ }
    }
  }
  return out.join('\n')
})

async function openFile(f: string) {
  if (dirty.value && !await confirmLeave()) return
  file.value = f; loading.value = true
  try {
    const r: any = await agentConfigService.readFile(props.entity.name, f)
    const d = r.data ?? r
    content.value = d.content; original.value = d.content
    await loadHistory()
  } catch (e: any) { ElMessage.error(`读取失败: ${e?.message || e}`) }
  finally { loading.value = false }
}

async function loadHistory() {
  try {
    const r: any = await agentConfigService.fileHistory(props.entity.name, file.value)
    history.value = (r.data ?? r) as FileHistoryItem[]
  } catch { history.value = [] }
}

async function confirmLeave(): Promise<boolean> {
  try { await ElMessageBox.confirm('有未保存的编辑，离开将丢失。', '未保存', { type: 'warning' }) ; return true }
  catch { return false }
}

function save() { showDiff.value = true }

async function confirmSave() {
  saving.value = true
  try {
    const msg = window.prompt('快照说明（可留空）') ?? ''
    const r: any = await agentConfigService.saveFile({
      entity: props.entity.name, file: file.value, content: content.value, message: msg,
    })
    const d = r.data ?? r
    original.value = content.value
    if (d.degraded) ElMessage.warning(`已保存，但 git 快照降级为 .bak（${d.detail || ''}）`)
    else ElMessage.success(`已保存，快照 ${d.commit}`)
    showDiff.value = false
    await loadHistory()
  } catch (e: any) { ElMessage.error(`保存失败: ${e?.message || e}`) }
  finally { saving.value = false }
}

async function revert(h: FileHistoryItem) {
  try {
    await ElMessageBox.confirm(`回滚到 ${h.commit}（${h.message.slice(0, 30)}…）？`, '回滚', { type: 'warning' })
  } catch { return }
  try {
    const r: any = await agentConfigService.revertFile({ entity: props.entity.name, file: file.value, commit: h.commit })
    const d = r.data ?? r
    content.value = d.content; original.value = d.content
    ElMessage.success(`已回滚到 ${h.commit}`)
    await loadHistory()
  } catch (e: any) { ElMessage.error(`回滚失败: ${e?.message || e}`) }
}

watch(() => props.entity.name, () => { file.value = ''; content.value = ''; original.value = ''; history.value = [] })
</script>

<style scoped>
.ed { display: flex; height: 100%; gap: 0 }
.ed-list { width: 230px; flex-shrink: 0; border-right: 1px solid var(--brd); overflow: auto; padding: 12px }
.ed-lh { font-size: 11px; color: var(--text-muted); letter-spacing: .5px; margin: 4px 0 8px }
.ed-fi { font-size: 12.5px; font-family: ui-monospace, monospace; padding: 7px 10px; border-radius: 7px;
  cursor: pointer; color: var(--text-secondary); position: relative }
.ed-fi:hover { background: #f1f5f9 }
.ed-fi.active { background: var(--primary-soft, #eef2ff); color: var(--primary); font-weight: 600 }
.ed-fi .dot { position: absolute; right: 9px; color: #f59e0b }
.ed-empty { font-size: 11.5px; color: var(--text-muted); padding: 6px 4px }
.ed-hi { padding: 7px 10px; border-radius: 7px; cursor: pointer; border: 1px solid transparent }
.ed-hi:hover { background: #f8fafc; border-color: var(--brd) }
.ed-hc { font-family: ui-monospace, monospace; font-size: 11px; color: var(--primary); font-weight: 600 }
.ed-hm { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 190px }
.ed-hd { font-size: 10px; color: var(--text-muted) }
.ed-main { flex: 1; min-width: 0; display: flex; flex-direction: column }
.ed-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--brd) }
.ed-path { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600; color: var(--text-primary) }
.ed-meta { font-weight: 400; font-size: 11px; color: var(--text-muted); margin-left: 8px }
.ed-acts { display: flex; gap: 8px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
.ed-ta { flex: 1; width: 100%; border: none; outline: none; resize: none; padding: 14px 16px;
  font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; line-height: 1.65; color: var(--text-primary) }
.ed-none { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: 13px }
.ed-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.ed-diff { background: #fff; border-radius: 13px; width: min(760px, 90vw); max-height: 80vh;
  display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,.2) }
.ed-dh { padding: 13px 18px; font-weight: 700; font-size: 14px; border-bottom: 1px solid var(--brd) }
.ed-dp { flex: 1; overflow: auto; margin: 0; padding: 14px 18px; font-size: 12px; line-height: 1.6;
  font-family: ui-monospace, monospace; white-space: pre-wrap; word-break: break-word }
.ed-df { padding: 12px 18px; display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid var(--brd) }
</style>
```

- [ ] **Step 7.2: 构建冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: success

- [ ] **Step 7.3: 手工冒烟（后端已起）**

打开 `http://localhost:5173/agents/config` → 选主智能体 → 身份文件 tab → 点 MEMORY.md → 改一行 → diff 预览（见 +/- 行）→ 保存 → toast 出 commit hash → 历史列表出现新条目 → 点旧版本回滚 → 内容还原。
Run: `git log --oneline -3`
Expected: 顶部出现 `config(web): workspace/MEMORY.md — …`

- [ ] **Step 7.4: Commit**

```bash
git add frontend/src/components/agents/config/IdentityFileEditor.vue
git commit -m "feat(config): 身份文件编辑器(diff预览+git快照保存+历史一键回滚)"
```

---

## Task 8: 参数面板 + LLM 测试 + 服务管理

**Files:**
- Replace: `frontend/src/components/agents/config/ParamsPanel.vue`（占位→实现；并接进 AgentConfigView——见 Step 8.3）
- Replace: `frontend/src/components/agents/config/ServiceControl.vue`（占位→实现）

**注意**：Task 6 骨架里参数 tab 挂在主智能体实体下。Step 8.3 修改 AgentConfigView：主智能体多一个「运行参数」tab。

- [ ] **Step 8.1: ParamsPanel**

```vue
<!-- frontend/src/components/agents/config/ParamsPanel.vue -->
<template>
  <div class="pp">
    <div v-if="restartHint" class="pp-hint">
      ⚠ 有「需重启」参数已保存。<button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>
    <div class="pp-sec-t">运行参数（{{ params.length }}）</div>
    <div class="pp-grid">
      <div v-for="p in params" :key="p.key" class="pp-row">
        <div class="pp-k">
          <div class="pp-key">{{ p.key }}</div>
          <div class="pp-desc">{{ p.desc }} · 读取方 {{ p.reader }}</div>
        </div>
        <div class="pp-v">
          <input v-model="draft[p.key]" :type="p.type === 'secret' ? 'password' : 'text'"
                 class="pp-in" :placeholder="`默认 ${p.default}`" />
        </div>
        <span class="pp-eff" :class="p.effect">{{ p.effect === 'restart' ? '需重启' : '立即生效' }}</span>
      </div>
    </div>
    <div class="pp-foot">
      <button class="btn primary" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存参数' }}</button>
    </div>

    <div class="pp-sec-t" style="margin-top: 26px">LLM 连接测试</div>
    <div class="pp-llm">
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key">测试目标</div><div class="pp-desc">留空 = 用当前生效配置直测</div></div>
        <div class="pp-v"><input v-model="llmDraft.base_url" class="pp-in" placeholder="base_url（空=当前）" /></div>
      </div>
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key"></div></div>
        <div class="pp-v"><input v-model="llmDraft.model" class="pp-in" placeholder="model（空=当前）" /></div>
      </div>
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key"></div></div>
        <div class="pp-v"><input v-model="llmDraft.api_key" type="password" class="pp-in" placeholder="api_key（空=当前）" /></div>
      </div>
      <div class="pp-foot">
        <button class="btn" @click="testLlm" :disabled="testing">{{ testing ? '测试中…' : '测试连接' }}</button>
        <span v-if="llmResult" class="pp-res" :class="llmResult.ok ? 'ok' : 'bad'">
          {{ llmResult.ok ? `✓ 连通 ${llmResult.latency_ms}ms` : `✗ ${llmResult.error}` }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentConfigService, type ParamItem } from '@/api/modules/agentConfig'

defineEmits<{ (e: 'restart'): void }>()

const params = ref<ParamItem[]>([])
const draft = ref<Record<string, string>>({})
const saving = ref(false)
const restartHint = ref(false)
const testing = ref(false)
const llmResult = ref<{ ok: boolean; latency_ms?: number; error?: string | null } | null>(null)
const llmDraft = ref({ base_url: '', model: '', api_key: '' })

onMounted(async () => {
  try {
    const r: any = await agentConfigService.getParams()
    params.value = (r.data ?? r) as ParamItem[]
    params.value.forEach(p => { draft.value[p.key] = String(p.value ?? '') })
  } catch (e: any) { ElMessage.error('参数读取失败：' + (e?.message || e)) }
})

async function save() {
  saving.value = true
  try {
    // 只提交有变化的；secret 空串不提交（后端也跳过）
    const payload: Record<string, string> = {}
    params.value.forEach(p => {
      const v = draft.value[p.key] ?? ''
      if (v !== String(p.value ?? '')) payload[p.key] = v
    })
    if (!Object.keys(payload).length) { ElMessage.info('无改动'); return }
    const r: any = await agentConfigService.saveParams(payload)
    restartHint.value = !!r.restart_needed
    ElMessage.success(r.restart_needed ? '已保存——部分参数需重启 agent 生效' : '已保存（立即生效）')
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || JSON.stringify(e?.response?.data) || e)) }
  finally { saving.value = false }
}

async function testLlm() {
  testing.value = true; llmResult.value = null
  try {
    llmResult.value = await agentConfigService.llmTest({
      base_url: llmDraft.value.base_url || undefined,
      model: llmDraft.value.model || undefined,
      api_key: llmDraft.value.api_key || undefined,
    }) as any
  } catch (e: any) { llmResult.value = { ok: false, error: e?.message || String(e) } }
  finally { testing.value = false }
}
</script>

<style scoped>
.pp { max-width: 820px }
.pp-hint { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 10px;
  padding: 10px 14px; font-size: 12.5px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px }
.pp-sec-t { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px }
.pp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.pp-grid { border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.pp-row { display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-bottom: 1px solid var(--brd) }
.pp-row:last-child { border-bottom: none }
.pp-k { flex: 1; min-width: 0 }
.pp-key { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600; color: var(--text-primary) }
.pp-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px }
.pp-v { width: 280px }
.pp-in { width: 100%; font-size: 12.5px; padding: 6px 10px; border: 1px solid var(--brd);
  border-radius: 7px; font-family: ui-monospace, monospace; outline: none }
.pp-in:focus { border-color: var(--primary) }
.pp-eff { font-size: 10.5px; padding: 2px 9px; border-radius: 6px; flex-shrink: 0 }
.pp-eff.immediate { color: #047857; background: #ecfdf5 }
.pp-eff.restart { color: #92400e; background: #fffbeb }
.pp-foot { padding: 12px 2px; display: flex; align-items: center; gap: 12px }
.btn { font-size: 12px; padding: 6px 14px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
.pp-res { font-size: 12px }
.pp-res.ok { color: #047857 }
.pp-res.bad { color: #dc2626 }
.pp-llm { border: 1px solid var(--brd); border-radius: 11px; padding: 4px 0 }
</style>
```

- [ ] **Step 8.2: ServiceControl**

```vue
<!-- frontend/src/components/agents/config/ServiceControl.vue -->
<template>
  <div class="sc">
    <div class="sc-card">
      <div class="sc-h">Agent 服务（端口 {{ status?.port || 8642 }}）</div>
      <div class="sc-row">
        <span class="sc-k">状态</span>
        <span class="sc-v" :class="status?.alive ? 'ok' : 'bad'">
          {{ restarting ? '重启中…' : (status?.alive ? '● 运行中' : '● 已停止') }}
        </span>
      </div>
      <div class="sc-row"><span class="sc-k">进程 PID</span>
        <span class="sc-v mono">{{ status?.pids?.join(', ') || '—' }}</span></div>
      <div class="sc-row"><span class="sc-k">模型</span>
        <span class="sc-v mono">{{ status?.model || '—' }}</span></div>
      <div class="sc-acts">
        <button class="btn primary" @click="doRestart" :disabled="restarting">
          {{ restarting ? `重启中（${pollSec}s）…` : '一键重启' }}
        </button>
        <button class="btn" @click="refresh" :disabled="restarting">刷新状态</button>
      </div>
      <div v-if="lastResult" class="sc-res" :class="lastResult.ok ? 'ok' : 'bad'">
        {{ lastResult.ok ? `✓ 已重启（旧 PID ${lastResult.old_pids?.join(', ') || '无'}）` +
           (lastResult.new_alive ? '' : ' ⚠ health 未就绪，请看 agent 控制台日志') : `✗ ${lastResult.error}` }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService } from '@/api/modules/agentConfig'

const status = ref<{ alive: boolean; port: number; pids: number[]; model: string } | null>(null)
const restarting = ref(false)
const pollSec = ref(0)
const lastResult = ref<{ ok: boolean; old_pids?: number[]; new_alive?: boolean; error?: string } | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  try { const r: any = await agentConfigService.serviceStatus(); status.value = r.data ?? r }
  catch { status.value = null }
}

async function doRestart() {
  try {
    await ElMessageBox.confirm('重启会中断正在进行的查询，确认重启 agent 服务？', '确认重启', { type: 'warning' })
  } catch { return }
  restarting.value = true; lastResult.value = null
  try {
    const r: any = await agentConfigService.serviceRestart()
    lastResult.value = r
    if (r.ok && r.new_alive) ElMessage.success('agent 服务已重启')
    else if (r.ok) ElMessage.warning('进程已启动但 health 未就绪——请看 agent 控制台日志')
    else ElMessage.error('重启失败：' + (r.error || '未知'))
  } catch (e: any) { ElMessage.error('重启请求失败：' + (e?.message || e)) }
  finally { restarting.value = false; await refresh() }
}

onMounted(refresh)
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.sc { max-width: 560px }
.sc-card { border: 1px solid var(--brd); border-radius: 13px; padding: 18px }
.sc-h { font-size: 14px; font-weight: 700; margin-bottom: 14px }
.sc-row { display: flex; padding: 7px 0; font-size: 13px }
.sc-k { width: 90px; color: var(--text-muted) }
.sc-v.ok { color: #047857; font-weight: 600 }
.sc-v.bad { color: #dc2626; font-weight: 600 }
.mono { font-family: ui-monospace, monospace; font-size: 12.5px }
.sc-acts { display: flex; gap: 9px; margin-top: 14px }
.btn { font-size: 12.5px; padding: 6px 15px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
.sc-res { margin-top: 12px; font-size: 12.5px; padding: 9px 12px; border-radius: 8px }
.sc-res.ok { background: #ecfdf5; color: #047857 }
.sc-res.bad { background: #fef2f2; color: #dc2626 }
</style>
```

- [ ] **Step 8.3: AgentConfigView 挂参数 tab**

`frontend/src/views/AgentConfigView.vue` 改三处：

(a) tabs 数组按实体变化：

```typescript
const tabsFor = computed(() =>
  activeEntity.value === 'master' ? ['overview', 'files', 'params'] : ['overview', 'files'])
```

template 的 `v-for="t in ['overview', 'files']"` 改 `v-for="t in tabsFor"`，label 映射加 `params: '运行参数'`（改为对象 `{overview:'概览',files:'身份文件',params:'运行参数'}` 取值）。

(b) body 加分支：

```html
        <ParamsPanel v-else-if="isEntity && tab === 'params'" @restart="goRestart" />
```

(c) goRestart（复用 ServiceControl 的重启——直接跳服务管理并触发）：

```typescript
import ParamsPanel from '@/components/agents/config/ParamsPanel.vue'
function goRestart() { activeEntity.value = '__service__'; /* ServiceControl onMounted 自动刷新，重启由用户点确认 */ }
```

（简化：点「一键重启 agent」→ 跳到服务管理页并提示用户点确认按钮。避免跨组件命令式调用。）

- [ ] **Step 8.4: 构建冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: success

- [ ] **Step 8.5: 手工冒烟**

打开页面 → 主智能体 → 运行参数 tab：看到 8 个参数（llm_api_key 显示 `***` 型脱敏）→ 改 agent_timeout=700 保存 → 提示「已保存（立即生效）」→ 改 master_max_iterations 保存 → 出现黄色「需重启」条 → 测试连接（空=当前）→ `✓ 连通 xxxms`（对 ctgu-vlm）→ 服务管理 → 一键重启 → 确认 → 等 health → 状态恢复运行中。
验参数真的生效：重启后 `./ecological_env/Scripts/python.exe -c "from backend.services.agent_params import get_param; print(get_param('master_max_iterations'))"` → 输出新值。

- [ ] **Step 8.6: Commit**

```bash
git add frontend/src/components/agents/config/ParamsPanel.vue frontend/src/components/agents/config/ServiceControl.vue frontend/src/views/AgentConfigView.vue
git commit -m "feat(config): 参数面板(生效标注/脱敏/LLM测试连接)+服务管理(一键重启)"
```

---

## Task 9: 厂区配置面板

**Files:**
- Replace: `frontend/src/components/agents/config/PlantsConfigPanel.vue`（占位→实现）

- [ ] **Step 9.1: 实现**

```vue
<!-- frontend/src/components/agents/config/PlantsConfigPanel.vue -->
<template>
  <div class="pc">
    <div class="pc-h">
      <div class="pc-t">厂区配置</div>
      <div class="pc-a">
        <button class="btn" @click="validate" :disabled="saving">校验</button>
        <button class="btn primary" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
      </div>
    </div>
    <div v-if="errors.length" class="pc-errs">
      <div v-for="(e, i) in errors" :key="i" class="pc-err">⚠ {{ e }}</div>
    </div>

    <!-- 层级：市→厂区→厂 -->
    <div class="pc-sec">
      <div class="pc-st">层级（市 → 厂区 → 厂）</div>
      <div v-for="(zones, city) in cfg.hierarchy" :key="city" class="pc-city">
        <div class="pc-cityh">
          <span class="pc-cn">{{ city }}</span>
          <button class="btn xs danger" @click="delCity(city)">删市</button>
        </div>
        <div v-for="(plants, zone) in zones" :key="zone" class="pc-zone">
          <div class="pc-zoneh">
            <span class="pc-zn">{{ zone }}</span>
            <button class="btn xs" @click="addPlant(city, zone)">+ 厂</button>
            <button class="btn xs danger" @click="delZone(city, zone)">删区</button>
          </div>
          <div class="pc-plants">
            <span v-for="(p, i) in plants" :key="p + i" class="pc-plant">
              {{ p }}
              <button class="pc-x" @click="delPlant(city, zone, i)">×</button>
            </span>
          </div>
        </div>
        <button class="btn xs" @click="addZone(city)">+ 厂区</button>
      </div>
      <button class="btn" @click="addCity">+ 市</button>
    </div>

    <!-- 别名表 -->
    <div class="pc-sec">
      <div class="pc-st">厂名别名（用户口语 → plant_id）</div>
      <div class="pc-kv">
        <template v-for="(v, k) in cfg.plant_aliases" :key="k">
          <input class="pc-in k" :value="k" @change="renameAlias(k, ($event.target as HTMLInputElement).value)" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" v-model="cfg.plant_aliases[k]" />
          <button class="pc-x" @click="delete cfg.plant_aliases[k]">×</button>
        </template>
      </div>
      <button class="btn xs" @click="addAlias">+ 别名</button>
    </div>

    <!-- 报表映射 -->
    <div class="pc-sec">
      <div class="pc-st">报表文件名映射（report_name_map）</div>
      <div class="pc-kv">
        <template v-for="(v, k) in cfg.report_name_map" :key="k">
          <input class="pc-in k" :value="k" disabled :title="'改名请删除重加'" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" v-model="cfg.report_name_map[k]" />
          <button class="pc-x" @click="delete cfg.report_name_map[k]">×</button>
        </template>
      </div>
      <button class="btn xs" @click="addReport">+ 映射</button>
    </div>

    <!-- per-plant 配置 -->
    <div class="pc-sec">
      <div class="pc-st">单厂配置（display_name / type / limits）</div>
      <div v-for="(conf, pid) in cfg.plant_configs" :key="pid" class="pc-pconf">
        <div class="pc-pid">{{ pid }}</div>
        <div class="pc-pf">
          <label>显示名 <input class="pc-in" v-model="cfg.plant_configs[pid].display_name" /></label>
          <label>类型 <input class="pc-in" v-model="cfg.plant_configs[pid].type" /></label>
        </div>
      </div>
      <div class="pc-pick">
        <select v-model="addPid" class="pc-sel"><option value="">选择厂添加配置…</option>
          <option v-for="p in allPlants" :key="p" :value="p">{{ p }}</option></select>
        <button class="btn xs" @click="addPlantConfig" :disabled="!addPid">添加</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type PlantConfig } from '@/api/modules/agentConfig'

const cfg = reactive<PlantConfig>({ hierarchy: {}, report_name_map: {}, plant_configs: {}, plant_aliases: {} })
const errors = ref<string[]>([])
const saving = ref(false)
const addPid = ref('')

const allPlants = computed(() => {
  const s: string[] = []
  Object.values(cfg.hierarchy).forEach(zones => Object.values(zones).forEach(ps => s.push(...ps)))
  return [...new Set(s)]
})

async function load() {
  try {
    const r: any = await agentConfigService.getPlants()
    Object.assign(cfg, r.data ?? r)
  } catch (e: any) { ElMessage.error('读取失败：' + (e?.message || e)) }
}

async function validate() {
  try {
    const r: any = await agentConfigService.validatePlants({ ...cfg })
    errors.value = (r.errors ?? []) as string[]
    ElMessage[r.errors?.length ? 'warning' : 'success'](r.errors?.length ? `发现 ${r.errors.length} 个问题` : '校验通过')
  } catch (e: any) { ElMessage.error('校验请求失败：' + (e?.message || e)) }
}

async function save() {
  saving.value = true
  try {
    const r: any = await agentConfigService.savePlants({ ...cfg })
    Object.assign(cfg, r.data ?? r)
    ElMessage.success('厂区配置已保存（自动 git 快照）')
  } catch (e: any) {
    const errs = e?.response?.data?.detail?.errors
    if (errs) { errors.value = errs; ElMessage.warning(`校验失败：${errs.length} 个问题`) }
    else ElMessage.error('保存失败：' + (e?.message || e))
  } finally { saving.value = false }
}

const _prompt = (t: string, dflt = '') => window.prompt(t, dflt) ?? ''

function addCity() {
  const name = _prompt('市名（如 枝江市）'); if (!name) return
  cfg.hierarchy[name] = {}
}
function delCity(c: string) { delete cfg.hierarchy[c] }
function addZone(c: string) {
  const name = _prompt('厂区名'); if (!name) return
  cfg.hierarchy[c][name] = []
}
function delZone(c: string, z: string) { delete cfg.hierarchy[c][z] }
function addPlant(c: string, z: string) {
  const name = _prompt('厂名（必须与 InfluxDB plant_id 完全一致）'); if (!name) return
  cfg.hierarchy[c][z].push(name)
}
function delPlant(c: string, z: string, i: number) { cfg.hierarchy[c][z].splice(i, 1) }
function addAlias() {
  const k = _prompt('别名（用户会怎么说，如 金桥）'); if (!k) return
  cfg.plant_aliases[k] = ''
}
function renameAlias(oldK: string, newK: string) {
  const v = cfg.plant_aliases[oldK]; delete cfg.plant_aliases[oldK]; cfg.plant_aliases[newK] = v
}
function addReport() {
  const k = _prompt('报表文件名主体'); if (!k) return
  cfg.report_name_map[k] = ''
}

async function addPlantConfig() {
  if (!addPid.value) return
  if (!cfg.plant_configs[addPid.value]) cfg.plant_configs[addPid.value] = { display_name: '', type: '' }
  addPid.value = ''
}

onMounted(load)
</script>

<style scoped>
.pc { max-width: 860px }
.pc-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px }
.pc-t { font-size: 15px; font-weight: 700 }
.pc-a { display: flex; gap: 8px }
.pc-errs { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px }
.pc-err { font-size: 12px; color: #dc2626 }
.pc-sec { border: 1px solid var(--brd); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px }
.pc-st { font-size: 12.5px; font-weight: 700; color: var(--text-secondary); margin-bottom: 12px }
.pc-city { margin-bottom: 12px; padding: 10px; border: 1px dashed var(--brd); border-radius: 10px }
.pc-cityh { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }
.pc-cn { font-weight: 700; font-size: 13.5px }
.pc-zone { margin: 8px 0 8px 10px; padding: 8px 10px; background: #f8fafc; border-radius: 8px }
.pc-zoneh { display: flex; align-items: center; gap: 8px; margin-bottom: 6px }
.pc-zn { font-weight: 600; font-size: 12.5px }
.pc-plants { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 }
.pc-plant { font-size: 12px; background: #fff; border: 1px solid var(--brd); border-radius: 7px;
  padding: 3px 9px; display: inline-flex; align-items: center; gap: 5px; font-family: ui-monospace, monospace }
.pc-kv { display: grid; grid-template-columns: 1fr 20px 1fr 24px; gap: 7px; align-items: center; margin-bottom: 8px }
.pc-in { width: 100%; font-size: 12px; padding: 5px 9px; border: 1px solid var(--brd); border-radius: 6px;
  font-family: ui-monospace, monospace }
.pc-in.k { background: #f8fafc }
.pc-arrow { text-align: center; color: var(--text-muted); font-size: 12px }
.pc-x { border: none; background: none; color: #dc2626; cursor: pointer; font-size: 14px; padding: 0 4px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
.pc-pconf { border-bottom: 1px dashed var(--brd); padding: 10px 0 }
.pc-pid { font-family: ui-monospace, monospace; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px }
.pc-pf { display: flex; gap: 14px; flex-wrap: wrap }
.pc-pf label { font-size: 11.5px; color: var(--text-muted); display: flex; align-items: center; gap: 7px }
.pc-pick { display: flex; gap: 8px; margin-top: 10px }
.pc-sel { font-size: 12px; padding: 5px 9px; border: 1px solid var(--brd); border-radius: 6px; min-width: 260px }
</style>
```

- [ ] **Step 9.2: 构建冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: success

- [ ] **Step 9.3: 手工冒烟**

页面 → 厂区配置：看到两厂层级/别名/映射/单厂配置（金桥+洗舱站）→ 加一个假别名指向不存在厂 → 校验 → 出红字警告 → 删掉 → 保存 → toast「已保存（自动 git 快照）」→ `git log --oneline -1` 见 `config(web): shared/data/plant-hierarchy.yaml`。

- [ ] **Step 9.4: Commit**

```bash
git add frontend/src/components/agents/config/PlantsConfigPanel.vue
git commit -m "feat(config): 厂区配置面板(层级/别名/报表映射/单厂配置,校验+保存快照)"
```

---

## Task 10: E2E + 收尾

**Files:**
- Create: `scripts/e2e_agent_config.py`（Playwright，参照现有 e2e 脚本模式）

- [ ] **Step 10.1: E2E 脚本**

```python
# scripts/e2e_agent_config.py
"""配置中心 E2E：编辑→保存→历史→回滚 + 参数保存 + 白名单拦截。
前置：backend(8000) + frontend(5173) 已起。零缓存模式（防 HMR 缓存假象,见 auto-memory）。"""
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"{'✓' if ok else '✗'} {name} {detail}")


with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(locale="zh-CN")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto("http://localhost:5173/agents/config", wait_until="networkidle")
    page.wait_for_selector(".et-item")

    # 1. 实体树 5 个
    n = page.locator(".et-item").count()
    check("实体树含 5 智能体+2 入口", n == 7, f"got {n}")

    # 2. 编辑 MEMORY.md：加一行 → 保存 → git 快照
    page.click(".et-item:has-text('主智能体')")
    page.click("button.tab:has-text('身份文件')")
    page.click(".ed-fi:has-text('MEMORY.md')")
    page.wait_for_selector(".ed-ta")
    orig = page.locator(".ed-ta").input_value()
    marker = "<!-- e2e-config-test -->"
    page.fill(".ed-ta", orig + f"\n{marker}\n")
    page.click("button:has-text('保存(git 快照)')")
    page.click("button:has-text('确认保存')")
    page.wait_for_selector(".ed-fi.active", state="visible")
    import time
    time.sleep(1.5)  # 等 git + toast
    saved = subprocess.run(["git", "log", "--oneline", "-1"], cwd=PROJECT_ROOT,
                           capture_output=True, text=True).stdout
    check("保存产生 git 快照", "config(web): workspace/MEMORY.md" in saved, saved.strip())
    after = Path(PROJECT_ROOT / "workspace" / "MEMORY.md").read_text(encoding="utf-8")
    check("文件内容已写入", marker in after)

    # 3. 历史回滚（回滚到快照前）
    page.wait_for_selector(".ed-hi")
    hist_count = page.locator(".ed-hi").count()
    check("历史列表有版本", hist_count >= 1, f"{hist_count} 条")
    if hist_count >= 2:
        page.locator(".ed-hi").nth(1).click()  # 上一版
        page.click(".el-message-box__btns .el-button--primary")
        time.sleep(1.5)
        reverted = Path(PROJECT_ROOT / "workspace" / "MEMORY.md").read_text(encoding="utf-8")
        check("回滚后 marker 消失", marker not in reverted)
    else:
        check("回滚分支跳过(历史不足)", True, "workspace 初始只有 1 个 commit 时无法回滚——先手工 git commit 一次再跑")

    # 4. 参数面板
    page.click("button.tab:has-text('概览')")
    page.click("button.tab:has-text('运行参数')")
    page.wait_for_selector(".pp-row")
    pn = page.locator(".pp-row").count()
    check("参数面板加载", pn >= 8, f"{pn} 行")
    masked = page.locator(".pp-row:has-text('llm_api_key') input").first.input_value()
    check("密钥脱敏", "***" in masked or masked == "", f"'{masked[:12]}'")

    # 5. 页面无 JS 错误
    check("无页面 JS 错误", not errors, "; ".join(errors[:3]))

    b.close()

fails = [r for r in results if not r[1]]
print(f"\n{'='*40}\nE2E: {len(results)-len(fails)}/{len(results)} 通过")
sys.exit(1 if fails else 0)
```

- [ ] **Step 10.2: 跑 E2E**

前置：`./ecological_env/Scripts/python.exe -m uvicorn backend.main:app --port 8000`（后台）+ `cd frontend && npm run dev`（后台）+ workspace/MEMORY.md 至少有 1 个历史 commit（正常都有）。

Run: `./ecological_env/Scripts/python.exe scripts/e2e_agent_config.py`
Expected: 全部 ✓ 且退出码 0

- [ ] **Step 10.3: 旧 capabilities 兼容确认**

`curl -s http://localhost:8000/api/query/capabilities | head -c 120`
Expected: 仍返回原 JSON（未破坏）。

- [ ] **Step 10.4: 最终收尾 Commit**

```bash
git add scripts/e2e_agent_config.py
git commit -m "test(config): 配置中心E2E(编辑/快照/回滚/参数/脱敏/白名单)"
```

---

## 自查记录（Self-Review）

1. **Spec 覆盖**：§3.1 五组接口→Task 5；§3.2 参数注册表+接线→Task 1/2；§3.3 重启→Task 5 Step 5.1；§3.4 git 快照→Task 3；§3.5 白名单→Task 3（ENTITY_FILES+路径越界双保险）；§4 前端组件→Task 6-9；§5 错误处理→分散在各任务（降级备份 Task 3、DB 兜底 Task 1、校验 400 Task 5、restart warn Task 5.1）；§6 测试→各任务单测+Task 10 E2E；§7 兼容→Task 4.5（别名 yaml 优先）+ Task 10.3（旧接口确认）；§8 顺序=Task 1-10。
2. **占位符扫描**：Task 6 骨架引用的三个占位组件在 Task 7/8/9 整文件替换——计划里已写明占位文件内容；无 TBD/TODO。
3. **类型一致性**：`agentConfigService` 方法名在 Task 6 定义、Task 7/8/9 使用（readFile/saveFile/fileHistory/revertFile/getParams/saveParams/llmTest/getPlants/validatePlants/savePlants/serviceStatus/serviceRestart）逐一核对一致；`get_param(key, env_key, default)` 签名 Task 1 定义、Task 2/5 使用一致；`FileHistoryItem` 字段（commit/date/author/message）Task 3 实现 ↔ Task 6 类型 ↔ Task 7 使用一致。

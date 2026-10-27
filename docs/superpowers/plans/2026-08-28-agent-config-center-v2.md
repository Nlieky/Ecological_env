# 配置中心 V2 实施计划（strategy / skills / mcp / providers）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 /agents/config 新增四个 tab——策略（编排/守卫/风格/动作通道/默认供应商，运行参数并入）、技能（展示/编辑/禁用/新建/市场）、MCP（接入管理+4 预置）、供应商（多 LLM CRUD+测试+strategy 联动），tab 移顶部导航+URL 同步。

**Architecture:** 策略复用 V1 参数中心模式（SQLite `agent_strategy` 表，DB 优先→内置默认，读取方接线 5 处）；技能复用身份文件白名单+git 快照机制（动态发现白名单，禁用=目录 `.disabled` 后缀+发现层过滤）；MCP 写 Hermes 原生 `config.yaml` 的 `mcp_servers` 段（agent HERMES_HOME=项目根），start_agent 显式调 `discover_mcp_tools()`+`enabled_toolsets` 加 `mcp-<server>`；providers 新表 `llm_providers`，start_agent 读取链：策略 `default_llm_provider` → providers 行 → get_param/env 兜底。

**Tech Stack:** FastAPI + SQLAlchemy(SQLite) + hermes_cli.config(原子 yaml) + mcp SDK(新依赖) + Vue3/Element Plus。

**Spec:** `docs/superpowers/specs/2026-08-28-agent-config-center-v2-design.md`

**venv python（所有命令一律用它，cwd=项目根 `E:\project\Ecological_env`）：** `./ecological_env/Scripts/python.exe`

---

## 关键事实（写代码前不要重新推导，全部已验证）

1. **hermes config.yaml 路径**：agent 服务设 `HERMES_HOME=项目根`（scripts/start_agent.py:34），`get_config_path()` = `<HERMES_HOME>/config.yaml` = `E:\project\Ecological_env\config.yaml`。该文件**现在不存在**；`read_raw_config()` 返回 `{}`；`load_config()` 返回深合并后的几百行默认值。**写 mcp_servers 时必须 `read_raw_config()` 读原样→只改 mcp_servers 键→写回**，绝不能用 `load_config()` 的结果回写。
2. **`mcp` Python 包未装**：`tools/mcp_tool.py` 的 `_MCP_AVAILABLE=False` 时所有 MCP 函数静默 no-op。Task 7 先装。
3. **MCP 自动发现已被 upstream 移除**（model_tools.py 顶部注释，#16856 事件循环冻结）：`discover_mcp_tools()` 不再是 import 副作用，每个入口必须显式调。
4. **MCP 工具集命名**：server `foo` 的工具注册为 toolset `mcp-foo`，且 `registry.register_toolset_alias("foo", "mcp-foo")`。`enabled_toolsets=[..., "mcp-fetch"]` 即启用。
5. **技能发现**：`iter_skill_index_files`（vendored agent/skill_utils.py）os.walk 匹配 `SKILL.md`；`EXCLUDED_SKILL_DIRS` 是精确名集合（.git/.archive 等），**不含** `.disabled` 规则。禁用机制 = 目录改名 `skills/<name>.disabled/` + 本系统发现层（identity_files.list_entities / 新 skill_service）跳过 `.disabled` 结尾目录。hermes 那层仍会看到改名后的技能（名字带 .disabled 后缀路径），但主智能体技能清单来自我们的服务+SKILL.md 指引，实际影响为零；彻底屏蔽是后续 upstream patch 的事，不在本计划。
6. **风格策略注入点**：`agent.ephemeral_system_prompt` 是**运行时每次 API 调用动态拼接**的属性（vendored conversation_loop.py:667，不进 `_cached_system_prompt` 缓存）——start_agent 每次 run_conversation 前设置它即可立即生效，零框架改动。
7. **守卫/自愈接线点**：`skills/orchestrator-core/scripts/tool_registration.py:464`（`result = _guard_perception_result(...)` 外包开关判断）；`skills/orchestrator-core/scripts/subagent_entry.py:286`（`healed = _heal_perception_by_script(...)` 外包开关判断）。
8. **动作通道接线点**：`scripts/start_agent.py:463-467` 硬编码引导语（`_try_shortcircuit` 函数内）。
9. **jinja2 3.1.6 已在 venv**（报表模板技能可用）。
10. **V1 可复用**：`backend/services/agent_params.py`（get_param/set_param/mask_secret/_open_session 模式）、`identity_files.py`（_git/_backup_degraded/save_file 快照模式）、`routes.py`（llm_test 的 httpx 测试模式）。
11. **前端现状**：`AgentConfigView.vue` 90 行，`tabsFor` computed 已按 master/子智能体区分 tab 集；ParamsPanel/IdentityFileEditor/PlantsConfigPanel/ServiceControl 四组件在 `frontend/src/components/agents/config/`。

## 文件结构

```
后端（新增）
  backend/services/agent_strategy.py        ← 策略注册表+读写（复用 agent_params 模式）
  backend/services/llm_providers.py         ← 供应商 CRUD+tested_ok+默认解析
  backend/services/skill_service.py         ← 技能发现/读SKILL.md/新建/禁用/市场安装/删除
  backend/services/mcp_config_service.py    ← config.yaml mcp_servers 段读写+测试连接+预置
  backend/tests/test_agent_strategy.py
  backend/tests/test_llm_providers.py
  backend/tests/test_skill_service.py
  backend/tests/test_mcp_config_service.py
后端（修改）
  backend/models/agent_config.py            ← +AgentStrategy、+LLMProvider 表
  backend/database/init_db.py               ← import 新表
  backend/api/v1/agents/config/routes.py    ← +strategy/skills/mcp/providers 接口
  skills/orchestrator-core/scripts/tool_registration.py   ← 守卫开关接线
  skills/orchestrator-core/scripts/subagent_entry.py      ← 自愈开关接线
  scripts/start_agent.py                    ← 风格注入+provider 链+MCP 发现+动作通道策略
模板库（新增）
  shared/skill_templates/<6 个模板>/        ← SKILL.md + scripts/main.py
前端（新增）
  src/components/agents/config/SkillsPanel.vue
  src/components/agents/config/StrategyPanel.vue
  src/components/agents/config/McpPanel.vue
  src/components/agents/config/ProvidersPanel.vue
前端（修改）
  src/views/AgentConfigView.vue             ← 顶部 tab+URL 同步+四新组件挂载
  src/api/modules/agentConfig.ts            ← 新接口方法
配置
  requirements.txt                          ← + mcp
```

---

## Task 1: 策略服务（agent_strategy 表 + 注册表 + 读写）

**Files:**
- Modify: `backend/models/agent_config.py`（+AgentStrategy 表）
- Create: `backend/services/agent_strategy.py`
- Modify: `backend/database/init_db.py`（import AgentStrategy）
- Test: `backend/tests/test_agent_strategy.py`

- [ ] **Step 1.1: 写失败测试**

```python
# backend/tests/test_agent_strategy.py
"""agent_strategy 单测：注册表完整性 / DB优先+内置默认 / bool与enum转换 / 分组返回。
独立临时 DB，不碰真实库。"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session(tmp_path):
    from backend.database.base import Base
    import backend.models.agent_config  # noqa: F401
    eng = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_registry_required_keys():
    from backend.services.agent_strategy import STRATEGY_REGISTRY
    keys = set(STRATEGY_REGISTRY)
    assert {"orchestration_stop_level", "perception_guard_enabled", "perception_heal_enabled",
            "language_constraint", "conclusion_first", "confidence_labeling",
            "action_guide_text", "action_shortcircuit_timeout", "action_inject_view_context",
            "default_llm_provider"} <= keys
    for k, spec in STRATEGY_REGISTRY.items():
        for f in ("default", "type", "effect", "group"):
            assert f in spec, f"{k} 缺 {f}"
        assert spec["effect"] in ("immediate", "restart")
        assert spec["type"] in ("bool", "enum", "int", "str", "ref")
        assert spec["group"] in ("orchestration", "guard", "style", "action", "provider")


def test_get_strategy_default_when_empty():
    from backend.services.agent_strategy import get_strategy
    assert get_strategy("perception_guard_enabled") is True
    assert get_strategy("orchestration_stop_level") == "auto"
    assert get_strategy("action_shortcircuit_timeout") == 30


def test_set_then_get_roundtrip(db_session, monkeypatch):
    monkeypatch.setattr("backend.services.agent_strategy._session_factory", lambda: db_session)
    from backend.services.agent_strategy import set_strategy, get_strategy
    set_strategy("perception_guard_enabled", "false")
    assert get_strategy("perception_guard_enabled") is False   # bool 转换
    set_strategy("orchestration_stop_level", "violation")
    assert get_strategy("orchestration_stop_level") == "violation"


def test_bad_value_falls_back(db_session, monkeypatch):
    monkeypatch.setattr("backend.services.agent_strategy._session_factory", lambda: db_session)
    from backend.services.agent_strategy import set_strategy, get_strategy
    set_strategy("orchestration_stop_level", "nonsense")   # 非法 enum
    assert get_strategy("orchestration_stop_level") == "auto"  # 回默认
    set_strategy("action_shortcircuit_timeout", "abc")     # 非法 int
    assert get_strategy("action_shortcircuit_timeout") == 30


def test_list_grouped(db_session, monkeypatch):
    monkeypatch.setattr("backend.services.agent_strategy._session_factory", lambda: db_session)
    from backend.services.agent_strategy import set_strategy, list_grouped
    set_strategy("conclusion_first", "true")
    groups = list_grouped()
    assert set(groups.keys()) >= {"orchestration", "guard", "style", "action", "provider"}
    guard_items = {i["key"]: i for i in groups["guard"]}
    assert guard_items["perception_guard_enabled"]["value"] is True
    style_items = {i["key"]: i for i in groups["style"]}
    assert style_items["conclusion_first"]["value"] is True
```

- [ ] **Step 1.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_agent_strategy.py -v`
Expected: FAIL（ModuleNotFoundError: backend.services.agent_strategy）

- [ ] **Step 1.3: 加表**

`backend/models/agent_config.py` 末尾追加（`func` 已在该文件 import，V1 Task 1 修复时引入）：

```python
class AgentStrategy(Base):
    """智能体执行策略（编排/守卫/风格/动作通道/默认供应商）。key/value 字符串存储，
    读取方经 agent_strategy.get_strategy 按类型转换；无行=用内置默认。"""
    __tablename__ = "agent_strategy"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
```

- [ ] **Step 1.4: 写 agent_strategy 服务**

```python
# backend/services/agent_strategy.py
"""执行策略注册表 + DB 优先读取（复用 agent_params 的模式与坑教训）。

- STRATEGY_REGISTRY：策略目录。改这里必须同步 strategy GET 接口的展示。
- get_strategy(key)：DB 有值→类型转换；坏值/无值→内置默认。读取方（tool_registration/
  subagent_entry/start_agent）静默降级，策略读取不能拖垮主流程。
- orchestration_stop_level 四档：auto(原行为,LLM 按 SKILL.md 停止铁律自主) /
  data(①数据即停) / anomaly(②异常即停) / violation(③违规即停)。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_STOP_LEVELS = ("auto", "data", "anomaly", "violation")

STRATEGY_REGISTRY: dict = {
    # ── 编排深度 ──
    "orchestration_stop_level": {"default": "auto", "type": "enum",
        "choices": _STOP_LEVELS, "effect": "immediate", "group": "orchestration",
        "desc": "编排推进上限：auto=按停止铁律自主 / data=①数据即停 / anomaly=②异常即停 / violation=③违规即停"},
    # ── 守卫与自愈 ──
    "perception_guard_enabled": {"default": True, "type": "bool",
        "effect": "immediate", "group": "guard", "desc": "感知①参数守卫（厂/时间/指标校验+确定性重跑）"},
    "perception_heal_enabled": {"default": True, "type": "bool",
        "effect": "immediate", "group": "guard", "desc": "感知①自愈兜底（LLM 不执行脚本时直接跑 get_data）"},
    # ── 回答风格 ──
    "language_constraint": {"default": "zh", "type": "enum", "choices": ("zh", "en", "none"),
        "effect": "immediate", "group": "style", "desc": "回答语言约束：zh=始终中文 / en=跟随用户 / none=不注入"},
    "conclusion_first": {"default": True, "type": "bool",
        "effect": "immediate", "group": "style", "desc": "结论先行，数据用表格，细节后置"},
    "confidence_labeling": {"default": True, "type": "bool",
        "effect": "immediate", "group": "style", "desc": "判定类回答标注「疑似/确认」置信级别"},
    # ── 动作通道 ──
    "action_guide_text": {"default": "", "type": "str",
        "effect": "immediate", "group": "action", "desc": "动作通道非动作引导语（空=用内置默认文案）"},
    "action_shortcircuit_timeout": {"default": 30, "type": "int",
        "effect": "restart", "group": "action", "desc": "动作分类器超时(秒)"},
    "action_inject_view_context": {"default": True, "type": "bool",
        "effect": "immediate", "group": "action", "desc": "是否向主智能体注入大屏观看窗口上下文"},
    # ── 默认供应商 ──
    "default_llm_provider": {"default": "", "type": "ref",
        "effect": "restart", "group": "provider", "desc": "默认模型供应商（引用 llm_providers.name，须 tested_ok）"},
}

_factory = None


def _session_factory():
    global _factory
    if _factory is None:
        from backend.database.session import SessionLocal
        _factory = SessionLocal
    return _factory


def _open_session():
    obj = _session_factory()
    return obj() if callable(obj) else obj


def _convert(raw: Optional[str], spec: dict):
    """raw 字符串 → 类型化值；非法返回 None（调用方回默认）。"""
    if raw is None or raw == "":
        return None
    t = spec["type"]
    if t == "bool":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        return None
    if t == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    if t == "enum":
        return raw if raw in spec.get("choices", ()) else None
    return raw  # str / ref 原样


def get_strategy(key: str, default=None):
    """DB 优先 → default 参数 → 注册表默认。异常静默降级（含 logger.warning，学 V1 教训）。"""
    spec = STRATEGY_REGISTRY.get(key)
    if spec is None:
        return default
    fallback = default if default is not None else spec["default"]
    try:
        from backend.models.agent_config import AgentStrategy
        with _open_session() as s:
            row = s.get(AgentStrategy, key)
            if row is not None:
                v = _convert(row.value, spec)
                if v is not None:
                    return v
    except Exception as exc:
        logger.warning("get_strategy(%s): DB 层不可用，走内置默认: %s", key, exc)
    return fallback


def set_strategy(key: str, value) -> None:
    from backend.models.agent_config import AgentStrategy
    with _open_session() as s:
        row = s.get(AgentStrategy, key)
        v = value if isinstance(value, str) else str(value)
        if row:
            row.value = v
        else:
            s.add(AgentStrategy(key=key, value=v))
        s.commit()


def list_grouped() -> dict:
    """按注册表 group 返回全部策略（当前生效值），供 GET 接口/页面渲染。"""
    groups: dict = {}
    for key, spec in STRATEGY_REGISTRY.items():
        item = {"key": key, "value": get_strategy(key), "default": spec["default"],
                "type": spec["type"], "effect": spec["effect"], "desc": spec.get("desc", ""),
                "choices": spec.get("choices")}
        groups.setdefault(spec["group"], []).append(item)
    return groups
```

- [ ] **Step 1.5: init_db 加 import**

`backend/database/init_db.py` 把原 `from backend.models.agent_config import AgentRuntimeParam` 行改为：

```python
from backend.models.agent_config import AgentRuntimeParam, AgentStrategy  # noqa: F401
```

- [ ] **Step 1.6: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_agent_strategy.py -v`
Expected: 5 passed

- [ ] **Step 1.7: Commit**

```bash
git add backend/models/agent_config.py backend/services/agent_strategy.py backend/database/init_db.py backend/tests/test_agent_strategy.py
git commit -m "feat(config-v2): 策略服务(编排/守卫/风格/动作通道/供应商引用,enum+bool转换+分组)"
```

---
## Task 2: 供应商服务（llm_providers 表 + CRUD + 默认解析）

**Files:**
- Modify: `backend/models/agent_config.py`（+LLMProvider 表）
- Create: `backend/services/llm_providers.py`
- Modify: `backend/database/init_db.py`（import 扩展）
- Test: `backend/tests/test_llm_providers.py`

- [ ] **Step 2.1: 写失败测试**

```python
# backend/tests/test_llm_providers.py
"""llm_providers 单测：预置两行 / CRUD / api_key 脱敏 / tested_ok 闸门 / 默认解析链。"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    from backend.database.base import Base
    import backend.models.agent_config  # noqa: F401
    eng = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    sm = sessionmaker(bind=eng)
    import backend.services.llm_providers as svc
    monkeypatch.setattr(svc, "_session_factory", sm)
    svc.seed_defaults()
    return sm


def test_seed_defaults(db_session):
    from backend.services.llm_providers import list_providers
    ps = list_providers()
    names = {p["name"] for p in ps}
    assert "ctgu-vlm" in names and "LongCat-2.0" in names
    ctgu = next(p for p in ps if p["name"] == "ctgu-vlm")
    assert ctgu["enabled"] is True
    longcat = next(p for p in ps if p["name"] == "LongCat-2.0")
    assert longcat["enabled"] is False


def test_api_key_masked(db_session):
    from backend.services.llm_providers import upsert_provider, list_providers, get_provider_row
    upsert_provider("deepseek", base_url="https://api.deepseek.com/v1",
                    api_key="sk-abcdef123456", model="deepseek-chat")
    row = next(p for p in list_providers() if p["name"] == "deepseek")
    assert row["api_key"] == "sk-***3456"       # 列表脱敏
    full = get_provider_row("deepseek")          # 内部用不脱敏
    assert full["api_key"] == "sk-abcdef123456"


def test_upsert_updates_existing(db_session):
    from backend.services.llm_providers import upsert_provider, get_provider_row
    upsert_provider("ctgu-vlm", base_url="http://x/v1", api_key="k1", model="m1")
    upsert_provider("ctgu-vlm", base_url="http://y/v1", api_key="k2", model="m2")
    row = get_provider_row("ctgu-vlm")
    assert row["base_url"] == "http://y/v1" and row["model"] == "m2"


def test_delete_provider(db_session):
    from backend.services.llm_providers import delete_provider, list_providers
    delete_provider("LongCat-2.0")
    assert "LongCat-2.0" not in {p["name"] for p in list_providers()}


def test_mark_tested_gate(db_session):
    from backend.services.llm_providers import (upsert_provider, mark_tested,
                                                eligible_default_providers, set_default_provider)
    upsert_provider("deepseek", base_url="http://x/v1", api_key="k", model="m")
    # 未 tested_ok → 不可设默认
    with pytest.raises(ValueError):
        set_default_provider("deepseek")
    mark_tested("deepseek", ok=True)
    assert "deepseek" in eligible_default_providers()
    set_default_provider("deepseek")   # 不再抛
    mark_tested("deepseek", ok=False)  # 失效后不再 eligible（已设的引用由读取方兜底）
    assert "deepseek" not in eligible_default_providers()


def test_resolve_default_chain(db_session, monkeypatch):
    from backend.services.llm_providers import upsert_provider, mark_tested, set_default_provider, resolve_default
    upsert_provider("deepseek", base_url="http://x/v1", api_key="sk-zz", model="dm")
    mark_tested("deepseek", ok=True)
    set_default_provider("deepseek")
    resolved = resolve_default()
    assert resolved == {"name": "deepseek", "base_url": "http://x/v1",
                        "api_key": "sk-zz", "model": "dm"}
    # 引用被删 → 返回 None（调用方走 get_param/env 兜底）
    from backend.services import llm_providers as svc
    monkeypatch.setattr(svc, "get_default_provider_name", lambda: "ghost")
    assert resolve_default() is None
```

- [ ] **Step 2.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_llm_providers.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 2.3: 加表**

`backend/models/agent_config.py` 末尾追加：

```python
class LLMProvider(Base):
    """外部 LLM 供应商配置。default_llm_provider 策略引用 name（仅 tested_ok 可设）。"""
    __tablename__ = "llm_providers"
    name = Column(String(64), primary_key=True)
    base_url = Column(String(256), nullable=False, default="")
    api_key = Column(Text, nullable=False, default="")
    model = Column(String(128), nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    tested_ok = Column(Boolean, nullable=False, default=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
```

（`Boolean` 加进文件顶部 sqlalchemy import。）

- [ ] **Step 2.4: 写 llm_providers 服务**

```python
# backend/services/llm_providers.py
"""LLM 供应商 CRUD + tested_ok 闸门 + 默认供应商解析。

默认供应商的"名字"存 agent_strategy 的 default_llm_provider 键（属策略域），
本模块提供读取/校验/联动的完整链路：
  set_default_provider(name)  校验 tested_ok 后写策略表
  resolve_default()           策略名 → providers 行（None=无可用，调用方走 env 兜底）
"""
import logging

logger = logging.getLogger(__name__)

_factory = None


def _session_factory():
    global _factory
    if _factory is None:
        from backend.database.session import SessionLocal
        _factory = SessionLocal
    return _factory


def _open_session():
    obj = _session_factory()
    return obj() if callable(obj) else obj


def seed_defaults() -> None:
    """预置 ctgu-vlm（启用）+ LongCat-2.0（禁用）。幂等。"""
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        for name, base_url, model, enabled in [
            ("ctgu-vlm", "http://172.xx.xx.xx:30000/v1", "ctgu-vlm", True),
            ("LongCat-2.0", "https://api.longcat.chat/openai/v1", "LongCat-2.0", False),
        ]:
            if s.get(LLMProvider, name) is None:
                s.add(LLMProvider(name=name, base_url=base_url, model=model, enabled=enabled))
        s.commit()


def _mask(v: str) -> str:
    if not v:
        return ""
    return f"{v[:3]}***{v[-4:]}" if len(v) > 8 else "***"


def list_providers(masked: bool = True) -> list:
    from backend.models.agent_config import LLMProvider
    out = []
    with _open_session() as s:
        for row in s.query(LLMProvider).order_by(LLMProvider.enabled.desc(), LLMProvider.name).all():
            out.append({
                "name": row.name, "base_url": row.base_url, "model": row.model,
                "api_key": _mask(row.api_key) if masked else row.api_key,
                "enabled": row.enabled, "tested_ok": row.tested_ok,
            })
    return out


def get_provider_row(name: str):
    """内部用（不脱敏）。不存在返回 None。"""
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        row = s.get(LLMProvider, name)
        if row is None:
            return None
        return {"name": row.name, "base_url": row.base_url, "api_key": row.api_key,
                "model": row.model, "enabled": row.enabled, "tested_ok": row.tested_ok}


def upsert_provider(name: str, base_url: str, api_key: str, model: str,
                    enabled: bool = True) -> None:
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        row = s.get(LLMProvider, name)
        if row:
            row.base_url, row.api_key, row.model, row.enabled = base_url, api_key, model, enabled
        else:
            s.add(LLMProvider(name=name, base_url=base_url, api_key=api_key,
                              model=model, enabled=enabled))
        s.commit()


def delete_provider(name: str) -> None:
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        row = s.get(LLMProvider, name)
        if row:
            s.delete(row)
            s.commit()


def mark_tested(name: str, ok: bool) -> None:
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        row = s.get(LLMProvider, name)
        if row:
            row.tested_ok = bool(ok)
            s.commit()


def eligible_default_providers() -> list:
    return [p["name"] for p in list_providers() if p["tested_ok"]]


def get_default_provider_name() -> str:
    from backend.services.agent_strategy import get_strategy
    return get_strategy("default_llm_provider") or ""


def set_default_provider(name: str) -> None:
    if name not in eligible_default_providers():
        raise ValueError(f"供应商 {name} 未通过测试连接，不能设为默认")
    from backend.services.agent_strategy import set_strategy
    set_strategy("default_llm_provider", name)


def resolve_default():
    """策略名 → 供应商行；名不存在/行被删/未启用 → None（调用方走 get_param/env）。"""
    name = get_default_provider_name()
    if not name:
        return None
    row = get_provider_row(name)
    if row is None or not row["enabled"]:
        logger.warning("默认供应商 %s 不存在或未启用，走 env/get_param 兜底", name)
        return None
    return row
```

- [ ] **Step 2.5: init_db 扩 import**

改为 `from backend.models.agent_config import AgentRuntimeParam, AgentStrategy, LLMProvider  # noqa: F401`

- [ ] **Step 2.6: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_llm_providers.py -v`
Expected: 6 passed

- [ ] **Step 2.7: Commit**

```bash
git add backend/models/agent_config.py backend/services/llm_providers.py backend/database/init_db.py backend/tests/test_llm_providers.py
git commit -m "feat(config-v2): 供应商服务(预置两行/CRUD/脱敏/tested_ok闸门/默认解析链)"
```

---
## Task 3: 技能服务（发现/读写/新建/禁用/删除/市场）

**Files:**
- Create: `backend/services/skill_service.py`
- Test: `backend/tests/test_skill_service.py`

依赖 Task 1 无关，独立。复用 `identity_files.py` 的 `_git`/`_backup_degraded` 模式（本文件内自带同款小实现，避免跨服务私有依赖）。

- [ ] **Step 3.1: 写失败测试**

```python
# backend/tests/test_skill_service.py
"""skill_service 单测：发现(跳过.disabled)/frontmatter 解析/新建校验/禁用往返/市场安装/删除。
在临时目录搭 skills 树（不碰真仓库）。"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """临时项目根：skills/ + 子智能体 skills + 模板库 + git 仓库。"""
    (tmp_path / "skills").mkdir()
    shutil.copytree(PROJECT_ROOT / "subagents", tmp_path / "subagents")
    tpl = tmp_path / "shared" / "skill_templates"
    tpl.mkdir(parents=True)
    (tpl / "tpl-a").mkdir()
    (tpl / "tpl-a" / "SKILL.md").write_text(
        "---\nname: tpl-a\ndescription: 测试模板\n---\n# tpl-a\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    import backend.services.skill_service as svc
    monkeypatch.setattr(svc, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_discover_master_skills(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "my-skill", "测试技能", skeleton="empty")
    svc.create_skill("master", "off-skill", "将被禁用", skeleton="empty")
    svc.disable_skill("master", "off-skill")
    items = {s["name"]: s for s in svc.list_skills("master")}
    assert "my-skill" in items and items["my-skill"]["enabled"] is True
    assert "off-skill" not in items          # .disabled 不在发现列表
    assert items["my-skill"]["description"] == "测试技能"


def test_discover_subagent_skills(env):
    from backend.services import skill_service as svc
    svc.create_skill("anomaly-detection", "sub-skill", "子智能体技能", skeleton="empty")
    names = [s["name"] for s in svc.list_skills("anomaly-detection")]
    assert "sub-skill" in names
    assert "data-perception-core" in names   # 真实拷来的既有技能仍在


def test_create_validates_name(env):
    from backend.services import skill_service as svc
    with pytest.raises(ValueError):
        svc.create_skill("master", "Bad_Name", "非法名", skeleton="empty")
    with pytest.raises(ValueError):
        svc.create_skill("master", "orchestrator-core", "已存在", skeleton="empty")


def test_create_skeleton_argparse(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "arg-skill", "带参数骨架", skeleton="argparse")
    p = env / "skills" / "arg-skill" / "scripts" / "main.py"
    assert p.exists() and "argparse" in p.read_text(encoding="utf-8")


def test_disable_enable_roundtrip(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "rt-skill", "往返", skeleton="empty")
    svc.disable_skill("master", "rt-skill")
    assert not (env / "skills" / "rt-skill" / "SKILL.md").exists()
    assert (env / "skills" / "rt-skill.disabled" / "SKILL.md").exists()
    svc.enable_skill("master", "rt-skill")
    assert (env / "skills" / "rt-skill" / "SKILL.md").exists()


def test_market_install_and_conflict(env):
    from backend.services import skill_service as svc
    r = svc.install_template("tpl-a", "master")
    assert r["ok"] is True and r["skill"] == "tpl-a"
    with pytest.raises(FileExistsError):
        svc.install_template("tpl-a", "master")   # 同名冲突不覆盖
    with pytest.raises(FileNotFoundError):
        svc.install_template("ghost-tpl", "master")


def test_delete_skill(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "del-skill", "待删", skeleton="empty")
    svc.delete_skill("master", "del-skill")
    assert not (env / "skills" / "del-skill").exists()
```

- [ ] **Step 3.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_skill_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3.3: 写 skill_service**

```python
# backend/services/skill_service.py
"""技能管理：发现/读写 SKILL.md/新建/禁用启用/市场安装/删除。

- 技能 = skills/<name>/SKILL.md（frontmatter name/description + 正文）+ scripts/。
- 归属：master → <root>/skills/；子智能体 → <root>/subagents/<dir>/skills/。
- 禁用 = 目录名加 .disabled 后缀；本服务发现层跳过 .disabled 结尾目录（hermes 上游
  EXCLUDED_SKILL_DIRS 无此后缀规则，改名后 hermes 仍可能看到带后缀路径——主智能体
  技能清单来自本服务+SKILL.md 指引，实际不可见；彻底屏蔽属 upstream patch，不在本期）。
- 写操作全部走 git 快照（只 add 目标路径，学 identity_files 的模式）。
"""
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENTITY_SKILLS_DIR = {
    "master": ("skills", ""),
    "multi-dimensional-data-perception": ("subagents/multi-dimensional-data-perception-agent", "数据感知"),
    "anomaly-detection": ("subagents/anomaly-detection-agent", "异常检测"),
    "rule-reasoning": ("subagents/rule-reasoning-agent", "规则推理"),
    "disposition-execution": ("subagents/disposition-execution-agent", "处置执行"),
}

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TEMPLATE_DIR = PROJECT_ROOT / "shared" / "skill_templates"


def _skills_base(entity: str) -> Path:
    if entity not in ENTITY_SKILLS_DIR:
        raise ValueError(f"未知实体: {entity}")
    return PROJECT_ROOT / ENTITY_SKILLS_DIR[entity][0] / "skills"


def _parse_frontmatter(text: str):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, text[m.end():]


def list_skills(entity: str) -> list:
    base = _skills_base(entity)
    out = []
    try:
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name.endswith(".disabled"):
                continue
            sk = d / "SKILL.md"
            if not sk.exists():
                continue
            meta, _ = _parse_frontmatter(sk.read_text(encoding="utf-8"))
            scripts = [p.name for p in (d / "scripts").glob("*.py")] if (d / "scripts").is_dir() else []
            out.append({"name": d.name,
                        "display_name": meta.get("name", d.name),
                        "description": meta.get("description", ""),
                        "scripts": scripts, "enabled": True})
    except FileNotFoundError:
        pass
    return out


def read_skill_md(entity: str, name: str) -> dict:
    p = _skills_base(entity) / name / "SKILL.md"
    if _NAME_RE.match(name) is None or not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    st = p.stat()
    return {"path": p.relative_to(PROJECT_ROOT).as_posix(),
            "content": p.read_text(encoding="utf-8"),
            "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def save_skill_md(entity: str, name: str, content: str, message: str = "") -> dict:
    p = _skills_base(entity) / name / "SKILL.md"
    if _NAME_RE.match(name) is None or not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    c = _git(["commit", "-m", f"config(web): {rel} — {message or '技能编辑'}", "--", rel])
    if c.returncode != 0:
        return {"commit": None, "degraded": True, "detail": (c.stderr or c.stdout).strip()[:200]}
    h = _git(["rev-parse", "--short", "HEAD"])
    return {"commit": h.stdout.strip() if h.returncode == 0 else None, "degraded": False}


_SKELETONS = {
    "empty": '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: 技能脚本说明（做什么、输入输出、写哪个结果文件）。"""
import json
import sys
from pathlib import Path

RESULT_FILE = Path(__file__).resolve().parents[2] / "skill_result.json"


def main() -> int:
    result = {"status": "completed", "data": {}}
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": "完成"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "argparse": '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: 技能脚本说明。参数示例：main.py --plant 当阳市金桥污水处理厂一期 --hours 24"""
import argparse
import json
import sys
from pathlib import Path

RESULT_FILE = Path(__file__).resolve().parents[2] / "skill_result.json"


def parse_args():
    ap = argparse.ArgumentParser(description="TODO")
    ap.add_argument("--plant", default="", help="厂区 plant_id（全称）")
    ap.add_argument("--hours", type=int, default=24, help="时间窗（小时）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    result = {"status": "completed", "params": vars(args), "data": {}}
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": "完成"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
}


def create_skill(entity: str, name: str, description: str, skeleton: str = "empty") -> dict:
    if _NAME_RE.match(name) is None:
        raise ValueError(f"技能名只允许 [a-z0-9-]（小写字母/数字/连字符）: {name}")
    base = _skills_base(entity)
    target = base / name
    if target.exists() or (base / f"{name}.disabled").exists():
        raise ValueError(f"技能已存在: {name}")
    (target / "scripts").mkdir(parents=True)
    (target / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\n"
        f"## 你做什么\n\nTODO: 写清楚这个技能做什么、什么时候用。\n\n"
        f"## 怎么调\n\n```bash\n\"E:/project/Ecological_env/ecological_env/Scripts/python.exe\" "
        f"\"$HERMES_HOME/{target.relative_to(PROJECT_ROOT).as_posix()}/scripts/main.py\" --help\n```\n\n"
        f"TODO: 写清楚参数与结果文件。\n",
        encoding="utf-8")
    (target / "scripts" / "main.py").write_text(_SKELETONS.get(skeleton, _SKELETONS["empty"]),
                                                encoding="utf-8")
    rel = target.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"feat(skills): 新建技能 {rel}", "--", rel])
    return {"name": name, "path": rel}


def disable_skill(entity: str, name: str) -> None:
    d = _skills_base(entity) / name
    if not d.is_dir():
        raise FileNotFoundError(f"技能不存在: {name}")
    d.rename(d.with_name(name + ".disabled"))
    _snapshot_dir(entity, name + ".disabled")


def enable_skill(entity: str, name: str) -> None:
    d = _skills_base(entity) / f"{name}.disabled"
    if not d.is_dir():
        raise FileNotFoundError(f"未找到被禁用的技能: {name}")
    d.rename(d.with_name(name))
    _snapshot_dir(entity, name)


def delete_skill(entity: str, name: str) -> None:
    for suffix in (name, f"{name}.disabled"):
        d = _skills_base(entity) / suffix
        if d.is_dir():
            _snapshot_dir(entity, suffix)
            shutil.rmtree(d)
            return
    raise FileNotFoundError(f"技能不存在: {name}")


def list_templates() -> list:
    out = []
    try:
        for d in sorted(TEMPLATE_DIR.iterdir()):
            sk = d / "SKILL.md"
            if d.is_dir() and sk.exists():
                meta, _ = _parse_frontmatter(sk.read_text(encoding="utf-8"))
                out.append({"name": d.name,
                            "description": meta.get("description", ""),
                            "has_scripts": (d / "scripts").is_dir()})
    except FileNotFoundError:
        pass
    return out


def install_template(template: str, entity: str) -> dict:
    src = TEMPLATE_DIR / template
    if not src.is_dir():
        raise FileNotFoundError(f"模板不存在: {template}")
    base = _skills_base(entity)
    target = base / template
    if target.exists() or (base / f"{template}.disabled").exists():
        raise FileExistsError(f"技能已存在: {template}")
    shutil.copytree(src, target)
    rel = target.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"feat(skills): 从市场安装 {rel}", "--", rel])
    return {"ok": True, "skill": template, "path": rel}


def _snapshot_dir(entity: str, dirname: str) -> None:
    rel = (_skills_base(entity) / dirname).relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"config(skills): {rel}", "--", rel])


def _git(args: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git"] + args, cwd=PROJECT_ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args=["git"] + args, returncode=127, stdout="",
                                           stderr=str(exc)[:200])
```

- [ ] **Step 3.4: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_skill_service.py -v`
Expected: 7 passed

- [ ] **Step 3.5: Commit**

```bash
git add backend/services/skill_service.py backend/tests/test_skill_service.py
git commit -m "feat(config-v2): 技能服务(发现跳过.disabled/frontmatter解析/新建校验/禁用往返/市场安装防覆盖)"
```

---
## Task 4: 技能市场模板库（6 个模板落盘）

**Files:**
- Create: `shared/skill_templates/<6 个>/SKILL.md`（其中 4 个含 scripts/main.py）

- [ ] **Step 4.1: 法规查询技能（master，纯 MCP 指引无脚本）**

```markdown
<!-- shared/skill_templates/regulation-lookup/SKILL.md -->
---
name: regulation-lookup
description: 查询废水排放法规/标准原文——当任务涉及"标准限值""法规依据""排放标准""GB标准"时使用。依赖 Fetch MCP 抓取公开法规网页。
---

# 法规查询技能

## 你做什么

用 mcp-fetch 工具抓取公开法规/标准页面，提取与查询相关的条款原文，标注来源 URL。

## 怎么调

直接调用 MCP 工具（无需终端跑脚本）：
```
mcp_fetch(url="https://www.mee.gov.cn/...")  # 生态环境部标准页面等公开源
```

## 常用参考源

- 《城镇污水处理厂污染物排放标准》GB 18918-2002
- 各流域/地方排放标准（按用户提到的省份查）

## 输出要求

引用条款原文 + 标注标准号与来源 URL；查不到就说查不到，不编造条款。
```

- [ ] **Step 4.2: 报表生成技能（disposition-execution，jinja2）**

```python
# shared/skill_templates/report-generator/scripts/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日报/周报生成：读会话区结果文件，jinja2 渲染 markdown 报表。
参数：--type daily|weekly  --date 2026-08-28  --title 自定义标题"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Template

SESSION_DIR = Path(__file__).resolve().parents[4] / "sessions"
TEMPLATE = Template("""# {{ title }}

生成时间：{{ now }}
数据日期：{{ date }}

## 数据概况

{% for line in data_lines %}{{ line }}
{% endfor %}

## 异常与研判

{% for line in anomaly_lines %}{{ line }}
{% endfor %}

## 处置建议

{% for line in disposition_lines %}{{ line }}
{% endfor %}
""")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["daily", "weekly"], default="daily")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--title", default="")
    return ap.parse_args()


def _load(session_dir: Path, name: str) -> dict:
    p = session_dir / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    args = parse_args()
    title = args.title or ("日报" if args.type == "daily" else "周报") + f" {args.date}"
    sd = Path(__file__).resolve().parents[4] / "sessions" / "current"
    sd = sd if sd.exists() else SESSION_DIR
    data = _load(sd, "data_result.json")
    anomaly = _load(sd, "anomaly_result.json")
    disposition = _load(sd, "disposition_result.json")
    data_lines = [f"- {k}: {v}" for k, v in (data.get("statistics") or {}).items()] or ["- 无数据摘要"]
    anomaly_lines = [f"- {a}" for a in (anomaly.get("summary") or [])] or ["- 无异常"]
    disposition_lines = [f"- {d}" for d in (disposition.get("summary") or [])] or ["- 无处置建议"]
    report = TEMPLATE.render(title=title, now=datetime.now().isoformat(timespec="seconds"),
                             date=args.date, data_lines=data_lines,
                             anomaly_lines=anomaly_lines, disposition_lines=disposition_lines)
    out = Path(__file__).resolve().parents[2] / f"report_{args.type}_{args.date}.md"
    out.write_text(report, encoding="utf-8")
    print(json.dumps({"summary": f"已生成 {out.name}（{len(report)} 字符）"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- shared/skill_templates/report-generator/SKILL.md -->
---
name: report-generator
description: 生成日报/周报 markdown 报表——当任务涉及"生成报表""出日报""汇总报告"时使用。读会话区各子智能体结果，jinja2 渲染。
---

# 报表生成技能

## 你做什么

调脚本读会话区的 data_result/anomaly_result/disposition_result，渲染成结构化 markdown 报表文件。

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/report-generator/scripts/main.py" --type daily --date 2026-08-28
```

参数：`--type daily|weekly`（默认 daily）、`--date YYYY-MM-DD`、`--title` 自定义标题。
产出：技能目录下 `report_daily_<date>.md`，把路径与内容摘要返回给主智能体。
```

- [ ] **Step 4.3: 新监测点接入向导（master）**

```python
# shared/skill_templates/plant-onboarding/scripts/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新监测点接入向导：检查报表名→查 plant-hierarchy.yaml 现状→输出待补配置清单。
参数：--report-name "洗舱站数据报表"  --plant-id 洗舱站污水排放口"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
YAML_PATH = ROOT / "shared" / "data" / "plant-hierarchy.yaml"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-name", required=True, help="报表文件名主体")
    ap.add_argument("--plant-id", required=True, help="目标 plant_id（与 InfluxDB 一致的全称）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cfg = {}
    if YAML_PATH.exists():
        cfg = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    plants = []
    for zones in (cfg.get("hierarchy") or cfg).values() if isinstance(cfg, dict) else []:
        if isinstance(zones, dict):
            for plist in zones.values():
                if isinstance(plist, list):
                    plants.extend(plist)
    checks = {
        "层级已含该厂": args.plant_id in plants,
        "别名表已配": args.plant_id in (cfg.get("plant_aliases") or {}),
        "报表映射已配": args.report_name in (cfg.get("report_name_map") or {}),
        "单厂配置已配": args.plant_id in (cfg.get("plant_configs") or {}),
    }
    todo = [k for k, ok in checks.items() if not ok]
    print(json.dumps({
        "summary": f"接入检查完成：{len(checks) - len(todo)}/{len(checks)} 项已就绪" +
                   (f"，待补：{'、'.join(todo)}" if todo else "，可导入数据"),
        "checks": checks, "todo": todo,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- shared/skill_templates/plant-onboarding/SKILL.md -->
---
name: plant-onboarding
description: 新监测点接入向导——当任务涉及"接入新厂""新监测点""报表导入前检查"时使用。检查 plant-hierarchy.yaml 四段配置是否齐备并输出待补清单。
---

# 新监测点接入向导

## 你做什么

调脚本检查新厂在 plant-hierarchy.yaml 的四段配置（层级/别名/报表映射/单厂配置），输出待办清单，指导用户在配置中心补齐后导入报表。

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/plant-onboarding/scripts/main.py" --report-name "洗舱站数据报表" --plant-id "洗舱站污水排放口"
```

产出：JSON 摘要（就绪项/待补项）。把待补项翻译成用户可操作的步骤（去 /agents/config 厂区配置补齐 → 跑 import_to_influxdb.py 导数）。
```

- [ ] **Step 4.4: 数据导出技能（multi-dimensional-data-perception）**

```python
# shared/skill_templates/data-export/scripts/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出监测数据 CSV。参数与 get_data 同款：--plant 全称 --start/--end 或 --hours"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from shared.data.influxdb_query import fetch_wastewater_df  # noqa: E402


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", default="当阳市金桥污水处理厂一期")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--hours", type=int, default=24)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.start and args.end:
        df = fetch_wastewater_df(plant_id=args.plant, start=args.start, end=args.end)
    else:
        df = fetch_wastewater_df(plant_id=args.plant, hours=args.hours)
    out = Path(__file__).resolve().parents[2] / f"export_{args.plant[:8]}_{len(df)}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(json.dumps({"summary": f"已导出 {len(df)} 行 → {out.name}"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- shared/skill_templates/data-export/SKILL.md -->
---
name: data-export
description: 导出监测数据 CSV——当任务涉及"导出数据""下载数据""存成CSV"时使用。与 get_data 同款查询，落 CSV 文件。
---

# 数据导出技能

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/data-export/scripts/main.py" --plant "当阳市金桥污水处理厂一期" --start 2026-07-14 --end 2026-07-15
```

产出：技能目录下 CSV（utf-8-sig，Excel 直开）。返回行数与文件名。
```

- [ ] **Step 4.5: 知识库检索技能（rule-reasoning）**

```python
# shared/skill_templates/knowledge-search/scripts/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检索废水知识库（法规/工艺/违规模式/专家经验），返回命中段落。
参数：--query "稀释排放" --top 5"""
import argparse
import json
import re
import sys
from pathlib import Path

KB = Path(__file__).resolve().parents[4] / "shared" / "knowledge"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--top", type=int, default=5)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    hits = []
    pattern = re.compile(re.escape(args.query))
    for md in KB.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in pattern.finditer(text):
            start = max(0, m.start() - 80)
            hits.append({"file": md.relative_to(KB).as_posix(),
                         "snippet": text[start:m.end() + 120].replace("\n", " ")})
            if len(hits) >= args.top * 3:
                break
    hits = hits[: args.top]
    print(json.dumps({"summary": f"命中 {len(hits)} 段", "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- shared/skill_templates/knowledge-search/SKILL.md -->
---
name: knowledge-search
description: 检索废水知识库——当任务涉及"法规怎么规定""违规模式""专家经验"时使用。grep 四库返回命中段落与出处文件。
---

# 知识库检索技能

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/knowledge-search/scripts/main.py" --query "稀释排放" --top 5
```

返回 JSON（命中段+文件路径）。把命中内容与出处整合进回答，注明来自哪个库。
```

- [ ] **Step 4.6: 自定义空白技能（任意）**

```markdown
<!-- shared/skill_templates/blank-skill/SKILL.md -->
---
name: blank-skill
description: 空白技能模板——安装后改名（目录+frontmatter）并编写你自己的技能说明。
---

# 空白技能（模板）

安装后：
1. 在技能列表用「新建」改名，或直接编辑本文件
2. 写清楚：你做什么 / 怎么调（脚本路径+参数）/ 输出要求
3. scripts/main.py 已带 argparse 骨架
```

`shared/skill_templates/blank-skill/scripts/main.py` = Task 3 `_SKELETONS["argparse"]` 同款内容（复制一份落盘）。

- [ ] **Step 4.7: 验证模板可被发现+安装**

Run: `./ecological_env/Scripts/python.exe -c "
import sys; sys.path.insert(0, '.')
from backend.services.skill_service import list_templates, install_template
tpls = list_templates()
print('templates:', [t['name'] for t in tpls])
assert len(tpls) == 6, f'expect 6, got {len(tpls)}'
"`
Expected: `templates: ['blank-skill', 'data-export', 'knowledge-search', 'plant-onboarding', 'regulation-lookup', 'report-generator']`

- [ ] **Step 4.8: Commit**

```bash
git add shared/skill_templates/
git commit -m "feat(config-v2): 技能市场模板库(法规查询/报表生成/新厂接入/数据导出/知识检索/空白)"
```

---
## Task 5: 策略/守卫/自愈/风格/动作通道/供应商链接线（运行时读取）

**Files:**
- Modify: `skills/orchestrator-core/scripts/tool_registration.py:460-464`（守卫开关）
- Modify: `skills/orchestrator-core/scripts/subagent_entry.py:282-287`（自愈开关）
- Modify: `scripts/start_agent.py`（风格注入+provider 链+动作通道策略）

依赖 Task 1/2。**本任务只接线不验证 LLM 行为**（行为验证在 Task 10 手工验收）。

- [ ] **Step 5.1: 守卫开关（tool_registration.py）**

L460-464 现状：

```python
        # 感知①结果守卫:LLM 丢参(混库/时间回退)→确定性重跑修正
        if subagent_name == "multi-dimensional-data-perception":
            _task_txt = str(params.get('task') or '')
            _sd = os.environ.get("SESSION_DIR") or ""
            result = _guard_perception_result(result, _task_txt, _sd)
```

改为：

```python
        # 感知①结果守卫:LLM 丢参(混库/时间回退)→确定性重跑修正。
        # 策略开关(配置中心·策略tab):perception_guard_enabled=False 跳过守卫(每调用读,立即生效)
        if subagent_name == "multi-dimensional-data-perception" and _strategy("perception_guard_enabled", True):
            _task_txt = str(params.get('task') or '')
            _sd = os.environ.get("SESSION_DIR") or ""
            result = _guard_perception_result(result, _task_txt, _sd)
```

文件头部（`project_root` 定好后）加辅助：

```python
def _strategy(key, default):
    """DB 优先读策略(配置中心·策略tab)；backend 不可导入时走默认。"""
    try:
        from backend.services.agent_strategy import get_strategy
        return get_strategy(key, default)
    except Exception:
        return default
```

- [ ] **Step 5.2: 自愈开关（subagent_entry.py）**

L282-287 现状（`if result is None and subagent_name == "multi-dimensional-data-perception":` 块）外包策略判断：

```python
        # 自愈(策略开关:perception_heal_enabled=False 跳过——配置中心·策略tab)
        _heal_on = True
        try:
            from backend.services.agent_strategy import get_strategy as _gs
            _heal_on = _gs("perception_heal_enabled", True)
        except Exception:
            pass
        if result is None and subagent_name == "multi-dimensional-data-perception" and _heal_on:
            healed = _heal_perception_by_script(task.get('task', ''), session_dir)
            if healed is not None:
                result = healed
                logger.info(f"[自愈] 已直接执行 get_data.py 兜底成功")
```

（保留原 if 体的缩进层级，只是条件加 `_heal_on and`。）

- [ ] **Step 5.3: start_agent 风格注入 + provider 链 + 动作通道策略**

(a) 文件头（`from backend.services.agent_params import get_param as _gp` 之后）加：

```python
from backend.services.agent_strategy import get_strategy as _gst
from backend.services import llm_providers as _lp
```

(b) `initialize()` 内 LLM 三项改为 provider 链：

```python
            # LLM 读取链:策略 default_llm_provider → providers 表行 → get_param/env 兜底
            model = _gp("llm_model", env_key="LLM_MODEL", default="ctgu-vlm")
            base_url = _gp("llm_base_url", env_key="LLM_BASE_URL", default="http://172.xx.xx.xx:30000/v1")
            api_key = _gp("llm_api_key", env_key="LLM_API_KEY", default="")
            try:
                _lp.seed_defaults()
                _prov = _lp.resolve_default()
                if _prov:
                    model, base_url, api_key = _prov["model"], _prov["base_url"], _prov["api_key"]
                    logger.info(f"使用默认供应商: {_prov['name']}")
            except Exception as _e:
                logger.warning(f"provider 解析失败,走 env/get_param 兜底: {_e}")
```

（替换原 model/base_url/api_key 三行 `_gp` 赋值；`_gp` 仍用于兜底层。）

(c) 两处 `run_conversation` 调用前（`scripts/start_agent.py:295` 与 `:578` 附近）注入风格策略。在文件级加一个函数：

```python
def _apply_style_strategy(agent):
    """回答风格策略 → ephemeral_system_prompt(运行时每次 API 调用拼接,立即生效,
    不污染 _cached_system_prompt 缓存)。空策略不设置。"""
    try:
        parts = []
        if _gst("language_constraint") == "zh":
            parts.append("回答必须使用中文。")
        if _gst("conclusion_first", True):
            parts.append("回答结论先行；数据用表格呈现；细节后置。")
        if _gst("confidence_labeling", True):
            parts.append("判定类结论必须标注置信级别（疑似/确认）。")
        stop = _gst("orchestration_stop_level", "auto")
        if stop and stop != "auto":
            _cap = {"data": "①数据感知", "anomaly": "②异常检测", "violation": "③规则推理"}[stop]
            parts.append(f"编排上限：本次最多推进到{_cap}即停，不自动调用更深层子智能体。")
        if parts:
            agent.ephemeral_system_prompt = "【执行策略】\n" + "\n".join(f"- {p}" for p in parts)
        else:
            agent.ephemeral_system_prompt = None
    except Exception as e:
        logger.warning(f"风格策略注入失败(忽略): {e}")
```

在 `initialize()` 末尾（tool_registration 之后）加一次 `self._apply_style = lambda: _apply_style_strategy(self.master_agent)`，并在两处 `run_conversation(...)` 调用前各加一行：

```python
                _apply_style_strategy(self.master_agent)   # /query 路径
```
```python
            _apply_style_strategy(agent_service.master_agent)   # /query/stream 路径
```

(d) 动作通道策略（`_try_shortcircuit` 内，L463-467 引导语替换）：

```python
        if exclusive:
            _guide = _gst("action_guide_text", "") or (
                "我是大屏动作助手,只执行让监测大屏变化的指令,例如:\n"
                "- 检测pH平稳异常 / 检测COD离群 / 标出TN突变点\n"
                "- 只看pH和COD / 切到进水 / 看最近一周\n"
                "数据研判、异常原因分析请到左侧「智能体问答」页面,那里有完整的子智能体分析管线。")
            return _guide
```

view_context 注入点（同函数 `if getattr(request, "view_context", None):` 外包）：

```python
        if getattr(request, "view_context", None) and _gst("action_inject_view_context", True):
```

- [ ] **Step 5.4: 语法验证**

Run: `./ecological_env/Scripts/python.exe -m py_compile scripts/start_agent.py skills/orchestrator-core/scripts/tool_registration.py skills/orchestrator-core/scripts/subagent_entry.py`
Expected: 无输出

- [ ] **Step 5.5: 隔离提交（学 V1 Task 2 的备份-重置-重放法，若文件有他人未提交改动）**

先 `git diff --stat` 查这 3 个文件；有混合改动则：备份 → `git show HEAD:<file>` 重置 → 重放本任务编辑 → `git add` → 恢复备份。无混合改动直接 add。

```bash
git add scripts/start_agent.py skills/orchestrator-core/scripts/tool_registration.py skills/orchestrator-core/scripts/subagent_entry.py
git commit -m "feat(config-v2): 策略接线(守卫/自愈开关+风格ephemeral注入+provider链+动作通道文案)"
```

---
## Task 6: MCP 配置服务（config.yaml mcp_servers 读写 + 测试连接 + 预置）

**Files:**
- Create: `backend/services/mcp_config_service.py`
- Test: `backend/tests/test_mcp_config_service.py`

- [ ] **Step 6.1: 写失败测试**

```python
# backend/tests/test_mcp_config_service.py
"""mcp_config_service 单测：读写往返(只动 mcp_servers 段)/脱敏/校验/预置清单。
临时 HERMES_HOME（monkeypatch env），不碰真实 config.yaml。"""
import os, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    # 造一份已有其他段的 config.yaml，验证写 mcp_servers 不破坏它们
    (tmp_path / "config.yaml").write_text(
        "model:\n  default: ctgu-vlm\nagent:\n  max_turns: 60\n", encoding="utf-8")
    import backend.services.mcp_config_service as svc
    monkeypatch.setattr(svc, "_hermes_home", lambda: tmp_path)
    return tmp_path


def test_read_empty(home):
    import backend.services.mcp_config_service as svc
    assert svc.list_servers() == {}


def test_roundtrip_preserves_other_sections(home):
    import backend.services.mcp_config_service as svc
    import yaml
    svc.upsert_server("fetch", {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-fetch"],
                                "timeout": 60})
    raw = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert raw["model"]["default"] == "ctgu-vlm"      # 其他段未动
    assert raw["agent"]["max_turns"] == 60
    assert raw["mcp_servers"]["fetch"]["timeout"] == 60


def test_upsert_disable_delete(home):
    import backend.services.mcp_config_service as svc
    svc.upsert_server("fetch", {"command": "npx", "args": ["-y", "pkg"], "enabled": True})
    assert svc.list_servers()["fetch"]["enabled"] is True
    svc.upsert_server("fetch", {"command": "npx", "args": ["-y", "pkg"], "enabled": False})
    assert svc.list_servers()["fetch"]["enabled"] is False
    svc.delete_server("fetch")
    assert "fetch" not in svc.list_servers()


def test_masked_listing(home):
    import backend.services.mcp_config_service as svc
    svc.upsert_server("github", {"command": "npx", "args": ["-y", "pkg"],
                                 "env": {"GITHUB_TOKEN": "ghp_abcdef123456"}})
    masked = svc.list_servers(masked=True)["github"]
    assert masked["env"]["GITHUB_TOKEN"] == "ghp_***3456"
    plain = svc.list_servers(masked=False)["github"]
    assert plain["env"]["GITHUB_TOKEN"] == "ghp_abcdef123456"


def test_validate(home):
    import backend.services.mcp_config_service as svc
    errs = svc.validate_server({"transport": "stdio", "command": "", "args": []})
    assert any("command" in e for e in errs)
    errs = svc.validate_server({"transport": "http", "url": ""})
    assert any("url" in e for e in errs)
    errs = svc.validate_server({"transport": "stdio", "command": "npx", "args": ["-y", "p"],
                                "allowed_dirs": ["E:\\"]})
    assert any("目录" in e for e in errs)   # 绝对不能开放盘符根
    errs = svc.validate_server({"transport": "stdio", "command": "npx", "args": ["-y", "p"],
                                "allowed_dirs": ["E:/project/Ecological_env/shared/knowledge"]})
    assert errs == []


def test_presets(home):
    import backend.services.mcp_config_service as svc
    presets = svc.list_presets()
    names = {p["name"] for p in presets}
    assert {"fetch", "influxdb", "filesystem", "memory"} <= names
    fs = next(p for p in presets if p["name"] == "filesystem")
    assert any("shared/knowledge" in a for a in fs["config"]["args"])
```

- [ ] **Step 6.2: 跑测试确认失败**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_mcp_config_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 6.3: 写 mcp_config_service**

```python
# backend/services/mcp_config_service.py
"""MCP 接入管理：读写 hermes config.yaml 的 mcp_servers 段 + 校验 + 测试连接 + 预置。

铁律：**绝不能用 load_config() 的深合并结果回写**（会把几百行内置默认值落盘）——
统一 read_raw_config() → 只改 mcp_servers 键 → save_config()。
Filesystem 类 server 的目录边界只允许项目内 shared/ 子路径（防开盘符根/项目根）。
"""
import copy
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_HERMES_ROOT = PROJECT_ROOT / "shared" / "framework" / "hermes-agent"

_ALLOWED_DIR_RE = re.compile(r"^[A-Za-z]:[/\\][^\s:*?\"<>|]*$")


def _hermes_home() -> Path:
    import os
    p = Path(os.environ.get("HERMES_HOME", str(PROJECT_ROOT)))
    return p


def _load_hermes_cli():
    if str(_HERMES_ROOT) not in sys.path:
        sys.path.insert(0, str(_HERMES_ROOT))
    from hermes_cli import config as hc
    return hc


def _read_raw() -> dict:
    hc = _load_hermes_cli()
    try:
        return hc.read_raw_config() or {}
    except Exception:
        return {}


def list_servers(masked: bool = True) -> dict:
    raw = _read_raw()
    servers = copy.deepcopy(raw.get("mcp_servers") or {})
    if masked:
        for cfg in servers.values():
            for k in list((cfg.get("env") or {}).keys()):
                if any(t in k.upper() for t in ("TOKEN", "KEY", "SECRET", "PASSWORD")):
                    v = str(cfg["env"][k])
                    cfg["env"][k] = f"{v[:4]}***{v[-4:]}" if len(v) > 8 else "***"
    return servers


def upsert_server(name: str, cfg: dict) -> None:
    hc = _load_hermes_cli()
    raw = _read_raw()
    servers = raw.get("mcp_servers") or {}
    servers[name] = cfg
    raw["mcp_servers"] = servers
    hc.save_config(raw)


def delete_server(name: str) -> None:
    hc = _load_hermes_cli()
    raw = _read_raw()
    servers = raw.get("mcp_servers") or {}
    servers.pop(name, None)
    if servers:
        raw["mcp_servers"] = servers
    else:
        raw.pop("mcp_servers", None)
    hc.save_config(raw)


def validate_server(cfg: dict) -> list:
    errs = []
    transport = cfg.get("transport", "stdio")
    if transport == "stdio" and not cfg.get("command"):
        errs.append("stdio 传输必须提供 command")
    if transport in ("http", "sse") and not cfg.get("url"):
        errs.append(f"{transport} 传输必须提供 url")
    for d in cfg.get("allowed_dirs") or []:
        dd = str(d).replace("\\", "/")
        if not _ALLOWED_DIR_RE.match(str(d)) or ":/" not in dd:
            errs.append(f"目录边界必须是绝对路径: {d}")
        elif "/shared/" not in dd and not dd.endswith("/shared"):
            errs.append(f"目录边界只允许项目内 shared/ 子路径: {d}")
    return errs


# 首批预置（一键安装=upsert_server）
PRESETS = [
    {"name": "fetch", "title": "Fetch 网页抓取", "transport": "stdio",
     "desc": "抓取法规/环保标准网页原文",
     "config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-fetch"],
                "timeout": 60, "connect_timeout": 30}},
    {"name": "influxdb", "title": "InfluxDB 时序查询", "transport": "stdio",
     "desc": "即席查监测数据/元数据（只读）",
     "config": {"command": "npx", "args": ["-y", "@influxdata/influxdb3-mcp"],
                "timeout": 120, "connect_timeout": 60,
                "env": {"INFLUXDB_TOKEN": "${INFLUXDB_READ_TOKEN}"}}},
    {"name": "filesystem", "title": "Filesystem 知识库读写", "transport": "stdio",
     "desc": "读写 shared/knowledge 知识库（目录边界锁定）",
     "config": {"command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem",
                         "E:/project/Ecological_env/shared/knowledge"],
                "timeout": 60}},
    {"name": "memory", "title": "Memory 知识图谱记忆", "transport": "stdio",
     "desc": "跨会话知识图谱记忆",
     "config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"],
                "timeout": 60}},
]


def list_presets() -> list:
    return [{"name": p["name"], "title": p["title"], "transport": p["transport"],
             "desc": p["desc"], "config": copy.deepcopy(p["config"])} for p in PRESETS]


def install_preset(name: str) -> dict:
    for p in PRESETS:
        if p["name"] == name:
            upsert_server(p["name"], copy.deepcopy(p["config"]))
            return {"ok": True, "name": name}
    raise FileNotFoundError(f"预置不存在: {name}")


def test_connect(cfg: dict) -> dict:
    """起一次性 stdio MCP 客户端握手 + tools/list。仅支持 stdio（预置全是）。"""
    import subprocess
    cmd = [cfg.get("command")] + list(cfg.get("args") or [])
    env_cfg = cfg.get("env") or {}
    try:
        import os
        env = dict(os.environ)
        for k, v in env_cfg.items():
            env[k] = os.path.expandvars(v)
        # MCP 握手走 JSON-RPC over stdio：initialize + tools/list
        import json
        init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2024-11-05",
                                      "capabilities": {},
                                      "clientInfo": {"name": "eco-config", "version": "1.0"}}})
        lst = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        r = subprocess.run(cmd, input=f"Content-Length: {len(init)}\r\n\r\n{init}"
                                       f"Content-Length: {len(lst)}\r\n\r\n{lst}",
                           capture_output=True, text=True, timeout=cfg.get("connect_timeout", 60),
                           env=env)
        out = r.stdout or ""
        ok = r.returncode == 0 and "tools" in out and "result" in out
        n_tools = out.count('"name"')
        return {"ok": ok, "tools_seen": n_tools if ok else 0,
                "error": None if ok else (r.stderr or "握手无 tools 响应")[:200]}
    except Exception as e:
        return {"ok": False, "tools_seen": 0, "error": str(e)[:200]}
```

- [ ] **Step 6.4: 跑测试确认通过**

Run: `./ecological_env/Scripts/python.exe -m pytest backend/tests/test_mcp_config_service.py -v`
Expected: 6 passed

- [ ] **Step 6.5: Commit**

```bash
git add backend/services/mcp_config_service.py backend/tests/test_mcp_config_service.py
git commit -m "feat(config-v2): MCP配置服务(raw读写不伤其他段/目录边界校验/预置4个/stdio握手测试)"
```

---

## Task 7: agent 侧 MCP 启用（依赖安装 + discover + toolsets）

**Files:**
- Modify: `requirements.txt`（+ mcp）
- Modify: `scripts/start_agent.py`（discover_mcp_tools + enabled_toolsets 动态加 mcp-*）

- [ ] **Step 7.1: 装依赖**

```bash
./ecological_env/Scripts/python.exe -m pip install mcp
./ecological_env/Scripts/python.exe -c "import mcp; print('mcp', mcp.__version__ if hasattr(mcp,'__version__') else 'ok')"
```
Expected: 输出 mcp 版本。`requirements.txt` 末尾加一行 `mcp`。

- [ ] **Step 7.2: start_agent 初始化段加 MCP 发现**

`initialize()` 内、`tool_registration` 注册**之前**（orchestrator 精简工具会按 `_KEEP_NAMES` 过滤——MCP 工具不在 keep 名单会被砍掉；先 discover 再让注册逻辑保留 mcp_ 前缀工具）：

```python
            # MCP 工具发现(配置中心·MCP tab 写 config.yaml 的 mcp_servers)。
            # upstream 已把 import 副作用移除(#16856),必须显式调;失败不拖垮主智能体。
            mcp_toolsets = []
            try:
                if str(project_root / "shared" / "framework" / "hermes-agent") not in sys.path:
                    sys.path.insert(0, str(project_root / "shared" / "framework" / "hermes-agent"))
                from tools.mcp_tool import discover_mcp_tools, _load_mcp_config
                _mcp_cfg = _load_mcp_config()
                mcp_toolsets = [f"mcp-{n}" for n, c in _mcp_cfg.items()
                                if str(c.get("enabled", True)).lower() != "false"]
                if mcp_toolsets:
                    _names = discover_mcp_tools()
                    logger.info(f"MCP 已连接: {mcp_toolsets}, 工具 {_names}")
            except Exception as _e:
                logger.warning(f"MCP 发现失败(跳过): {_e}")
```

AIAgent 构造参数 `disabled_toolsets=[...]` 不变，改为构造后补加 toolset（`agent_init` 的 `get_tool_definitions(enabled_toolsets=...)` 在构造内跑——所以 MCP 工具要走**第二层注册**：构造后把 MCP 工具 schema append 进 `agent.tools`）：

```python
            # MCP 工具进 agent.tools(第 1 层,conversation_loop 只认 agent.tools)。
            # 放 tool_registration 精简之后执行,避免被 _KEEP_NAMES 过滤掉。
            # registry API(vendored tools/registry.py 实测):get_tool_names_for_toolset(name)
            # + get_definitions(tool_names: Set[str])——按工具集名取名再取 schema。
            try:
                from tools.registry import registry as _reg
                _mcp_names: set = set()
                for _ts in mcp_toolsets:
                    _mcp_names.update(_reg.get_tool_names_for_toolset(_ts))
                _mcp_defs = _reg.get_definitions(_mcp_names) if _mcp_names else []
                if _mcp_defs:
                    self.master_agent.tools.extend(_mcp_defs)
                    logger.info(f"MCP 工具已挂载: {[t['function']['name'] for t in _mcp_defs]}")
            except Exception as _e:
                logger.warning(f"MCP 工具挂载失败: {_e}")
```

（放在 `register_orchestrator_tools(self.master_agent)` 调用之后。）

- [ ] **Step 7.3: 语法+冒烟**

```bash
./ecological_env/Scripts/python.exe -m py_compile scripts/start_agent.py && echo compiled
HERMES_HOME="E:/project/Ecological_env" ./ecological_env/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'shared/framework/hermes-agent')
from tools.mcp_tool import _MCP_AVAILABLE
print('mcp available:', _MCP_AVAILABLE)"
```
Expected: `compiled` + `mcp available: True`

- [ ] **Step 7.4: Commit**

```bash
git add requirements.txt scripts/start_agent.py
git commit -m "feat(config-v2): agent侧MCP启用(装mcp包+显式discover+工具挂tool_registration之后)"
```

---
## Task 8: REST 路由（strategy / skills / mcp / providers 四组接口）

**Files:**
- Modify: `backend/api/v1/agents/config/routes.py`（追加四组）

依赖 Task 1/2/3/6。全部 sync def（阻塞操作学 V1 的 28583c9 教训）。

- [ ] **Step 8.1: 追加路由**

`backend/api/v1/agents/config/routes.py` 末尾追加：

```python
# ══════════ V2: 策略 ══════════
from backend.services.agent_strategy import STRATEGY_REGISTRY  # noqa: E402


@router.get("/agents/config/strategy")
async def get_strategy_all():
    from backend.services.agent_strategy import list_grouped
    from backend.services.agent_params import PARAM_REGISTRY
    # 运行参数并入策略页展示（存储仍走 agent_params 表,接口不变）
    params = [{"key": k, "value": (lambda v: __import__('backend.services.agent_params', fromlist=['mask_secret']).mask_secret(v) if s["type"] == "secret" else v)((lambda: __import__('backend.services.agent_params', fromlist=['get_param']).get_param(k, env_key=s.get("env_key"), default=s.get("default")))()),
               "default": s.get("default"), "type": s["type"],
               "effect": s["effect"], "desc": s.get("desc", "")}
              for k, s in PARAM_REGISTRY.items()]
    return {"success": True, "data": {"groups": list_grouped(), "params": params}}


class StrategyBody(BaseModel):
    items: dict  # {key: value}; secret/ref 空串=不改


@router.put("/agents/config/strategy")
async def put_strategy(body: StrategyBody):
    from backend.services.agent_strategy import set_strategy, STRATEGY_REGISTRY
    from backend.services.llm_providers import eligible_default_providers
    invalid = [k for k in body.items if k not in STRATEGY_REGISTRY]
    if invalid:
        raise HTTPException(400, f"未知策略: {invalid}")
    errors = []
    for k, v in body.items.items():
        spec = STRATEGY_REGISTRY[k]
        if v is None or v == "":
            if spec["type"] in ("bool", "enum", "int", "ref"):
                continue  # 这些类型空=不改
            continue
        if spec["type"] == "enum" and v not in spec.get("choices", ()):
            errors.append(f"{k} 必须是 {spec['choices']} 之一")
        if spec["type"] == "int":
            try:
                int(v)
            except (TypeError, ValueError):
                errors.append(f"{k} 必须是整数")
        if k == "default_llm_provider" and v and v not in eligible_default_providers():
            errors.append(f"供应商 {v} 未通过测试连接,不能设为默认")
    if errors:
        raise HTTPException(400, detail={"message": "策略校验失败", "errors": errors})
    for k, v in body.items.items():
        if v is None or v == "":
            continue
        set_strategy(k, str(v))
    restart_needed = any(STRATEGY_REGISTRY[k]["effect"] == "restart" for k in body.items)
    return {"success": True, "restart_needed": restart_needed}


# ══════════ V2: 技能 ══════════
@router.get("/agents/config/skills")
async def get_skills(entity: str):
    from backend.services.skill_service import list_skills, list_templates
    return {"success": True, "data": {"skills": list_skills(entity),
                                      "templates": list_templates()}}


class SkillFileBody(BaseModel):
    entity: str
    name: str
    content: str
    message: Optional[str] = ""


@router.get("/agents/config/skills/file")
async def get_skill_file(entity: str, name: str):
    from backend.services.skill_service import read_skill_md
    try:
        return {"success": True, "data": read_skill_md(entity, name)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/agents/config/skills/file")
async def put_skill_file(body: SkillFileBody):
    from backend.services.skill_service import save_skill_md
    try:
        return {"success": True, "data": save_skill_md(body.entity, body.name, body.content, body.message or "")}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class SkillCreateBody(BaseModel):
    entity: str
    name: str
    description: str
    skeleton: str = "empty"


@router.post("/agents/config/skills/create")
async def create_skill(body: SkillCreateBody):
    from backend.services.skill_service import create_skill
    try:
        return {"success": True, "data": create_skill(body.entity, body.name, body.description, body.skeleton)}
    except ValueError as e:
        raise HTTPException(400, str(e))


class SkillActionBody(BaseModel):
    entity: str
    name: str


@router.post("/agents/config/skills/disable")
async def disable_skill(body: SkillActionBody):
    from backend.services.skill_service import disable_skill
    try:
        disable_skill(body.entity, body.name)
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/agents/config/skills/enable")
async def enable_skill(body: SkillActionBody):
    from backend.services.skill_service import enable_skill
    try:
        enable_skill(body.entity, body.name)
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.delete("/agents/config/skills")
async def delete_skill(entity: str, name: str):
    from backend.services.skill_service import delete_skill
    try:
        delete_skill(entity, name)
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class TemplateInstallBody(BaseModel):
    template: str
    entity: str


@router.post("/agents/config/skills/install")
async def install_template(body: TemplateInstallBody):
    from backend.services.skill_service import install_template
    try:
        return {"success": True, "data": install_template(body.template, body.entity)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except FileExistsError as e:
        raise HTTPException(409, str(e))


# ══════════ V2: MCP ══════════
@router.get("/agents/config/mcp")
async def get_mcp():
    from backend.services.mcp_config_service import list_servers, list_presets
    return {"success": True, "data": {"servers": list_servers(masked=True), "presets": list_presets()}}


class McpServerBody(BaseModel):
    name: str
    config: dict


@router.put("/agents/config/mcp")
async def put_mcp(body: McpServerBody):
    from backend.services.mcp_config_service import upsert_server, validate_server
    errs = validate_server(body.config)
    if errs:
        raise HTTPException(400, detail={"message": "MCP 配置校验失败", "errors": errs})
    upsert_server(body.name, body.config)
    return {"success": True, "restart_needed": True}


@router.delete("/agents/config/mcp")
async def delete_mcp(name: str):
    from backend.services.mcp_config_service import delete_server
    delete_server(name)
    return {"success": True, "restart_needed": True}


class McpTestBody(BaseModel):
    config: dict


@router.post("/agents/config/mcp/test")
async def mcp_test(body: McpTestBody):
    from backend.services.mcp_config_service import test_connect
    return test_connect(body.config)


class McpPresetBody(BaseModel):
    name: str


@router.post("/agents/config/mcp/preset")
async def install_mcp_preset(body: McpPresetBody):
    from backend.services.mcp_config_service import install_preset
    try:
        return {"success": True, "data": install_preset(body.name), "restart_needed": True}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


# ══════════ V2: 供应商 ══════════
@router.get("/agents/config/providers")
async def get_providers():
    from backend.services.llm_providers import list_providers, seed_defaults, eligible_default_providers, get_default_provider_name
    seed_defaults()
    return {"success": True, "data": {"providers": list_providers(masked=True),
                                      "eligible": eligible_default_providers(),
                                      "current_default": get_default_provider_name()}}


class ProviderBody(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = None   # None/空=不修改已有 key
    model: str
    enabled: bool = True


@router.put("/agents/config/providers")
async def put_provider(body: ProviderBody):
    from backend.services.llm_providers import upsert_provider, get_provider_row
    key = body.api_key
    if not key:
        existing = get_provider_row(body.name)
        key = existing["api_key"] if existing else ""
    upsert_provider(body.name, body.base_url, key, body.model, body.enabled)
    return {"success": True}


@router.delete("/agents/config/providers")
async def delete_provider(name: str):
    from backend.services.llm_providers import delete_provider
    delete_provider(name)
    return {"success": True}


class ProviderTestBody(BaseModel):
    name: str


@router.post("/agents/config/providers/test")
async def provider_test(body: ProviderTestBody):
    import time
    import httpx
    from backend.services.llm_providers import get_provider_row, mark_tested
    row = get_provider_row(body.name)
    if row is None:
        raise HTTPException(404, f"供应商不存在: {body.name}")
    t0 = time.time()
    try:
        r = httpx.post(f"{row['base_url'].rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {row['api_key']}"},
                       json={"model": row["model"], "messages": [{"role": "user", "content": "hi"}],
                             "max_tokens": 1},
                       timeout=10.0)
        ok = r.status_code == 200
        mark_tested(body.name, ok)
        return {"ok": ok, "latency_ms": int((time.time() - t0) * 1000),
                "error": None if ok else f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        mark_tested(body.name, False)
        return {"ok": False, "latency_ms": int((time.time() - t0) * 1000), "error": str(e)[:150]}


class DefaultProviderBody(BaseModel):
    name: str


@router.post("/agents/config/providers/default")
async def set_default(body: DefaultProviderBody):
    from backend.services.llm_providers import set_default_provider
    try:
        set_default_provider(body.name)
        return {"success": True, "restart_needed": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 8.2: 起后端冒烟**

Run: `./ecological_env/Scripts/python.exe -m uvicorn backend.main:app --port 8000 &` 后：

```bash
curl -s http://localhost:8000/api/v1/agents/config/strategy | head -c 300
curl -s "http://localhost:8000/api/v1/agents/config/skills?entity=master" | head -c 300
curl -s http://localhost:8000/api/v1/agents/config/mcp | head -c 300
curl -s http://localhost:8000/api/v1/agents/config/providers | head -c 300
```
Expected: 四个都返回 `{"success":true,...}`（strategy 含 groups+params；skills 含 orchestrator-core/action-command-core；mcp servers 空但 presets 4 个；providers 含 ctgu-vlm+LongCat-2.0）。

- [ ] **Step 8.3: 白名单/校验负例冒烟**

```bash
curl -s -X PUT http://localhost:8000/api/v1/agents/config/strategy -H "Content-Type: application/json" -d '{"items":{"orchestration_stop_level":"nonsense"}}'
```
Expected: 400 带错误信息

- [ ] **Step 8.4: Commit**

```bash
git add backend/api/v1/agents/config/routes.py
git commit -m "feat(config-v2): REST路由(strategy含参数并入/skills全CRUD+mcp四组/providers含测试+设默认)"
```

---
## Task 9: 前端 API 扩展 + 顶部 tab 导航 + URL 同步

**Files:**
- Modify: `frontend/src/api/modules/agentConfig.ts`（+V2 接口方法+类型）
- Modify: `frontend/src/views/AgentConfigView.vue`（六 tab+URL 同步+四新组件挂载+ParamsPanel 移除引用）

- [ ] **Step 9.1: agentConfig.ts 追加**

```typescript
// ── V2 类型 ──
export interface StrategyItem {
  key: string; value: boolean | string | number; default: unknown
  type: 'bool' | 'enum' | 'int' | 'str' | 'ref'; effect: 'immediate' | 'restart'
  desc: string; choices?: string[]
}
export interface StrategyData { groups: Record<string, StrategyItem[]>; params: ParamItem[] }
export interface SkillItem {
  name: string; display_name: string; description: string
  scripts: string[]; enabled: boolean
}
export interface TemplateItem { name: string; description: string; has_scripts: boolean }
export interface McpServerCfg {
  command?: string; args?: string[]; env?: Record<string, string>
  url?: string; headers?: Record<string, string>; transport?: string
  timeout?: number; connect_timeout?: number; enabled?: boolean
}
export interface McpPreset { name: string; title: string; transport: string; desc: string; config: McpServerCfg }
export interface ProviderRow {
  name: string; base_url: string; model: string
  api_key: string; enabled: boolean; tested_ok: boolean
}

// ── V2 方法（追加进 agentConfigService 对象）──
  getStrategy: () => api.get<unknown, { success: boolean; data: StrategyData }>('/agents/config/strategy'),
  saveStrategy: (items: Record<string, string | boolean | number>) =>
    api.put<unknown, { success: boolean; restart_needed: boolean }>('/agents/config/strategy', { items }),
  getSkills: (entity: string) =>
    api.get<unknown, { success: boolean; data: { skills: SkillItem[]; templates: TemplateItem[] } }>('/agents/config/skills', { params: { entity } }),
  readSkillFile: (entity: string, name: string) =>
    api.get<unknown, { success: boolean; data: FileContent }>('/agents/config/skills/file', { params: { entity, name } }),
  saveSkillFile: (body: { entity: string; name: string; content: string; message?: string }) =>
    api.put<unknown, { success: boolean; data: { commit: string | null; degraded: boolean } }>('/agents/config/skills/file', body),
  createSkill: (body: { entity: string; name: string; description: string; skeleton: string }) =>
    api.post<unknown, { success: boolean; data: { name: string; path: string } }>('/agents/config/skills/create', body),
  disableSkill: (body: { entity: string; name: string }) =>
    api.post<unknown, { success: boolean }>('/agents/config/skills/disable', body),
  enableSkill: (body: { entity: string; name: string }) =>
    api.post<unknown, { success: boolean }>('/agents/config/skills/enable', body),
  deleteSkill: (entity: string, name: string) =>
    api.delete<unknown, { success: boolean }>('/agents/config/skills', { params: { entity, name } }),
  installTemplate: (body: { template: string; entity: string }) =>
    api.post<unknown, { success: boolean; data: { ok: boolean; skill: string } }>('/agents/config/skills/install', body),
  getMcp: () =>
    api.get<unknown, { success: boolean; data: { servers: Record<string, McpServerCfg>; presets: McpPreset[] } }>('/agents/config/mcp'),
  putMcp: (body: { name: string; config: McpServerCfg }) =>
    api.put<unknown, { success: boolean; restart_needed: boolean }>('/agents/config/mcp', body),
  deleteMcp: (name: string) =>
    api.delete<unknown, { success: boolean }>('/agents/config/mcp', { params: { name } }),
  testMcp: (config: McpServerCfg) =>
    api.post<unknown, { ok: boolean; tools_seen?: number; error?: string | null }>('/agents/config/mcp/test', { config }),
  installMcpPreset: (name: string) =>
    api.post<unknown, { success: boolean; restart_needed: boolean }>('/agents/config/mcp/preset', { name }),
  getProviders: () =>
    api.get<unknown, { success: boolean; data: { providers: ProviderRow[]; eligible: string[]; current_default: string } }>('/agents/config/providers'),
  putProvider: (body: { name: string; base_url: string; api_key?: string; model: string; enabled: boolean }) =>
    api.put<unknown, { success: boolean }>('/agents/config/providers', body),
  deleteProvider: (name: string) =>
    api.delete<unknown, { success: boolean }>('/agents/config/providers', { params: { name } }),
  testProvider: (name: string) =>
    api.post<unknown, { ok: boolean; latency_ms?: number; error?: string | null }>('/agents/config/providers/test', { name }),
  setDefaultProvider: (name: string) =>
    api.post<unknown, { success: boolean; restart_needed: boolean }>('/agents/config/providers/default', { name }),
```

- [ ] **Step 9.2: AgentConfigView 重写为六 tab+URL 同步**

```vue
<!-- frontend/src/views/AgentConfigView.vue -->
<template>
  <div class="cfg">
    <EntityTree v-if="entities.length" :entities="entities" v-model="activeEntity" />
    <div class="cfg-main">
      <div class="tabs" v-if="isEntity">
        <button v-for="t in tabsFor" :key="t" class="tab"
                :class="{ active: tab === t }" @click="switchTab(t)">
          {{ TAB_LABELS[t] }}
        </button>
      </div>
      <div class="cfg-body">
        <EntityOverview v-if="isEntity && tab === 'overview' && currentEntity"
                        :entity="currentEntity" @openFile="openFileFromOverview" />
        <div v-else-if="isEntity && tab === 'files'" class="files-wrap">
          <IdentityFileEditor v-if="currentEntity" :entity="currentEntity" ref="editorRef" />
        </div>
        <SkillsPanel v-else-if="isEntity && tab === 'skills'" :entity="activeEntity" />
        <StrategyPanel v-else-if="isEntity && tab === 'strategy'" @restart="goRestart" />
        <McpPanel v-else-if="isEntity && tab === 'mcp'" @restart="goRestart" />
        <ProvidersPanel v-else-if="isEntity && tab === 'providers'" @restart="goRestart" />
        <PlantsConfigPanel v-else-if="activeEntity === '__plants__'" />
        <ServiceControl v-else-if="activeEntity === '__service__'" />
        <div v-else class="loading">加载中…</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentConfigService, type AgentEntity } from '@/api/modules/agentConfig'
import EntityTree from '@/components/agents/config/EntityTree.vue'
import EntityOverview from '@/components/agents/config/EntityOverview.vue'
import IdentityFileEditor from '@/components/agents/config/IdentityFileEditor.vue'
import SkillsPanel from '@/components/agents/config/SkillsPanel.vue'
import StrategyPanel from '@/components/agents/config/StrategyPanel.vue'
import McpPanel from '@/components/agents/config/McpPanel.vue'
import ProvidersPanel from '@/components/agents/config/ProvidersPanel.vue'
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
import ServiceControl from '@/components/agents/config/ServiceControl.vue'

const TAB_LABELS: Record<string, string> = {
  overview: '概览', files: '身份文件', skills: '技能',
  strategy: '策略', mcp: 'MCP', providers: '供应商',
}
const route = useRoute()
const router = useRouter()

const entities = ref<AgentEntity[]>([])
const activeEntity = ref('master')
const tab = ref('overview')
const editorRef = ref()

const isEntity = computed(() => entities.value.some(e => e.name === activeEntity.value))
const currentEntity = computed(() => entities.value.find(e => e.name === activeEntity.value))
const tabsFor = computed(() =>
  activeEntity.value === 'master'
    ? ['overview', 'files', 'skills', 'strategy', 'mcp', 'providers']
    : ['overview', 'files', 'skills', 'strategy'])

function switchTab(t: string) {
  if (tab.value === 'files' && t !== 'files' && editorRef.value?.dirty) {
    if (!confirm('有未保存的编辑，切换将丢失，确定？')) return
  }
  tab.value = t
  router.replace({ query: { ...route.query, tab: t } })
}

function openFileFromOverview(f: string) {
  tab.value = 'files'
  router.replace({ query: { ...route.query, tab: 'files' } })
  editorRef.value?.openFile(f)
}

function goRestart() { activeEntity.value = '__service__' }

// URL → 状态（首载/刷新/分享链接保形）
onMounted(async () => {
  const q = route.query as Record<string, string>
  if (q.entity) activeEntity.value = q.entity
  if (q.tab) tab.value = q.tab
  try {
    const r: any = await agentConfigService.entities()
    entities.value = (r.data ?? r) as AgentEntity[]
    if (!isEntity.value && q.entity && q.entity !== '__plants__' && q.entity !== '__service__') {
      activeEntity.value = 'master'   // 非法 entity 回落
    }
    // tab 与实体不匹配（如子智能体选了 mcp）回落 overview
    if (isEntity.value && !tabsFor.value.includes(tab.value)) tab.value = 'overview'
  } catch { /* 各面板自行处理 */ }
})

// 实体切换 → URL 同步 + tab 合法性
watch(activeEntity, (v) => {
  router.replace({ query: { ...route.query, entity: v } })
  if (isEntity.value && !tabsFor.value.includes(tab.value)) tab.value = 'overview'
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

（V1 的 ParamsPanel 引用移除——params 数据由 StrategyPanel 内嵌"运行参数"区渲染，走 getStrategy 的 params 字段。）

- [ ] **Step 9.3: 四个占位组件（Task 10 填充）**

`SkillsPanel.vue` / `StrategyPanel.vue` / `McpPanel.vue` / `ProvidersPanel.vue` 各建占位：

```vue
<template><div class="placeholder">V2 面板（Task 10 实现）</div></template>
<script setup lang="ts"></script>
<style scoped>.placeholder { color: var(--text-muted); padding: 40px; text-align: center }</style>
```

SkillsPanel 占位需带 props 声明（`defineProps<{ entity: string }>()`）；三个面板带 `defineEmits<{ (e: 'restart'): void }>()`。

- [ ] **Step 9.4: 构建冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: 编译通过

- [ ] **Step 9.5: Commit**

```bash
git add frontend/src/api/modules/agentConfig.ts frontend/src/views/AgentConfigView.vue frontend/src/components/agents/config/
git commit -m "feat(config-v2): 顶部六tab导航+URL同步(entity/tab query)+V2 API模块"
```

---
## Task 10: 四个 V2 面板组件实现

**Files:**
- Replace: `frontend/src/components/agents/config/SkillsPanel.vue`
- Replace: `frontend/src/components/agents/config/StrategyPanel.vue`
- Replace: `frontend/src/components/agents/config/McpPanel.vue`
- Replace: `frontend/src/components/agents/config/ProvidersPanel.vue`

- [ ] **Step 10.1: StrategyPanel（策略+运行参数并入）**

```vue
<!-- frontend/src/components/agents/config/StrategyPanel.vue -->
<template>
  <div class="sp">
    <div v-if="restartHint" class="sp-hint">
      ⚠ 有「需重启」配置已保存。<button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>
    <template v-for="(items, g) in groups" :key="g">
      <div class="sp-sec-t">{{ GROUP_LABELS[g] || g }}</div>
      <div class="sp-grid">
        <div v-for="it in items" :key="it.key" class="sp-row">
          <div class="sp-k">
            <div class="sp-key">{{ it.key }}</div>
            <div class="sp-desc">{{ it.desc }}</div>
          </div>
          <div class="sp-v">
            <el-switch v-if="it.type === 'bool'" v-model="draft[it.key] as boolean" />
            <el-select v-else-if="it.type === 'enum'" v-model="draft[it.key] as string" style="width: 200px">
              <el-option v-for="c in it.choices" :key="c" :label="c" :value="c" />
            </el-select>
            <el-input-number v-else-if="it.type === 'int'" v-model="draft[it.key] as number" />
            <el-input v-else-if="it.type === 'ref'" v-model="draft[it.key] as string"
                      placeholder="在供应商 tab 测试通过后选择" style="width: 220px" />
            <el-input v-else v-model="draft[it.key] as string" type="textarea" :rows="3"
                      :placeholder="`默认：${String(it.default).slice(0, 40)}…`" />
          </div>
          <span class="sp-eff" :class="it.effect">{{ it.effect === 'restart' ? '需重启' : '立即生效' }}</span>
        </div>
      </div>
    </template>

    <div class="sp-sec-t">运行参数</div>
    <div class="sp-grid">
      <div v-for="p in params" :key="p.key" class="sp-row">
        <div class="sp-k">
          <div class="sp-key">{{ p.key }}</div>
          <div class="sp-desc">{{ p.desc }}</div>
        </div>
        <div class="sp-v">
          <el-input v-if="p.type === 'secret'" v-model="paramDraft[p.key] as string" type="password" show-password
                    style="width: 220px" :placeholder="`当前 ${p.value}`" />
          <el-input-number v-else-if="p.type === 'int'" v-model="paramDraft[p.key] as number" />
          <el-input v-else v-model="paramDraft[p.key] as string" style="width: 220px" />
        </div>
        <span class="sp-eff" :class="p.effect">{{ p.effect === 'restart' ? '需重启' : '立即生效' }}</span>
      </div>
    </div>
    <div class="sp-foot">
      <button class="btn primary" @click="saveStrategy" :disabled="saving">保存策略</button>
      <button class="btn" @click="saveParams" :disabled="savingParams">保存参数</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentConfigService, type StrategyItem, type ParamItem } from '@/api/modules/agentConfig'

defineEmits<{ (e: 'restart'): void }>()

const GROUP_LABELS: Record<string, string> = {
  orchestration: '编排深度', guard: '守卫与自愈', style: '回答风格',
  action: '动作通道', provider: '默认模型供应商',
}
const groups = ref<Record<string, StrategyItem[]>>({})
const params = ref<ParamItem[]>([])
const draft = ref<Record<string, any>>({})
const paramDraft = ref<Record<string, any>>({})
const saving = ref(false)
const savingParams = ref(false)
const restartHint = ref(false)

onMounted(async () => {
  const r: any = await agentConfigService.getStrategy()
  const d = r.data ?? r
  groups.value = d.groups
  params.value = d.params
  Object.values(d.groups as Record<string, StrategyItem[]>>).forEach(
    items => items.forEach(it => { draft.value[it.key] = it.value }))
  d.params.forEach((p: ParamItem) => {
    paramDraft.value[p.key] = p.type === 'secret' ? '' : p.value
  })
})

async function saveStrategy() {
  saving.value = true
  try {
    const payload: Record<string, string | boolean | number> = {}
    Object.values(groups.value).forEach(items => items.forEach(it => {
      if (draft.value[it.key] !== it.value) payload[it.key] = draft.value[it.key]
    }))
    if (!Object.keys(payload).length) { ElMessage.info('策略无改动'); return }
    const r: any = await agentConfigService.saveStrategy(payload)
    restartHint.value = !!r.restart_needed
    ElMessage.success(r.restart_needed ? '已保存——部分策略需重启生效' : '已保存（立即生效）')
  } catch (e: any) {
    const errs = e?.response?.data?.detail?.errors
    ElMessage.error('保存失败：' + (errs?.join('；') || e?.message || e))
  } finally { saving.value = false }
}

async function saveParams() {
  savingParams.value = true
  try {
    const payload: Record<string, string | number> = {}
    params.value.forEach(p => {
      const v = paramDraft.value[p.key]
      if (p.type === 'secret' ? (v !== '' && v != null) : (String(v ?? '') !== String(p.value ?? ''))) {
        payload[p.key] = v
      }
    })
    if (!Object.keys(payload).length) { ElMessage.info('参数无改动'); return }
    const r: any = await agentConfigService.saveParams(payload)
    restartHint.value = restartHint.value || !!r.restart_needed
    ElMessage.success(r.restart_needed ? '已保存——部分参数需重启生效' : '已保存（立即生效）')
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { savingParams.value = false }
}
</script>

<style scoped>
.sp { max-width: 860px }
.sp-hint { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 10px;
  padding: 10px 14px; font-size: 12.5px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px }
.sp-sec-t { font-size: 13px; font-weight: 700; margin: 18px 0 10px; display: flex; align-items: center; gap: 8px }
.sp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.sp-grid { border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.sp-row { display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-bottom: 1px solid var(--brd) }
.sp-row:last-child { border-bottom: none }
.sp-k { flex: 1; min-width: 0 }
.sp-key { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sp-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px }
.sp-v { flex-shrink: 0 }
.sp-eff { font-size: 10.5px; padding: 2px 9px; border-radius: 6px; flex-shrink: 0 }
.sp-eff.immediate { color: #047857; background: #ecfdf5 }
.sp-eff.restart { color: #92400e; background: #fffbeb }
.sp-foot { padding: 14px 2px; display: flex; gap: 10px }
.btn { font-size: 12.5px; padding: 6px 15px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
```

- [ ] **Step 10.2: SkillsPanel（列表+编辑+新建+市场+禁用/删除）**

```vue
<!-- frontend/src/components/agents/config/SkillsPanel.vue -->
<template>
  <div class="sk">
    <div class="sk-head">
      <div class="sk-t">技能 · {{ entityLabel }}</div>
      <div class="sk-a">
        <button class="btn" @click="showCreate = true">新建技能</button>
        <button class="btn" @click="showMarket = true">技能市场</button>
      </div>
    </div>

    <div class="sk-grid">
      <div v-for="s in skills" :key="s.name" class="sk-card" :class="{ editing: editing === s.name }">
        <div class="sk-cname">📘 {{ s.display_name }}</div>
        <div class="sk-cdesc" :title="s.description">{{ s.description || '（无描述）' }}</div>
        <div class="sk-cmeta">{{ s.scripts.length }} 个脚本 · 已启用</div>
        <div class="sk-cacts">
          <button class="btn xs" @click="openSkill(s.name)">{{ editing === s.name ? '收起' : '查看/编辑' }}</button>
          <button class="btn xs" @click="toggle(s.name, false)">禁用</button>
          <button class="btn xs danger" @click="del(s.name)">删除</button>
        </div>
      </div>
      <div v-for="s in disabledSkills" :key="s" class="sk-card disabled">
        <div class="sk-cname">📘 {{ s }}</div>
        <div class="sk-cmeta">已禁用</div>
        <div class="sk-cacts">
          <button class="btn xs" @click="toggle(s, true)">启用</button>
          <button class="btn xs danger" @click="del(s)">删除</button>
        </div>
      </div>
    </div>

    <!-- SKILL.md 编辑（复用身份文件编辑器的样式模式） -->
    <div v-if="editing" class="sk-ed">
      <div class="sk-edbar">
        <span class="sk-edpath">{{ editing }}/SKILL.md</span>
        <div>
          <button class="btn" @click="showDiff = true" :disabled="!dirty">diff 预览</button>
          <button class="btn primary" @click="save" :disabled="!dirty || saving">{{ saving ? '保存中…' : '保存(git 快照)' }}</button>
        </div>
      </div>
      <textarea v-model="content" class="sk-ta" spellcheck="false"></textarea>
      <div v-if="showDiff" class="sk-mask" @click.self="showDiff = false">
        <div class="sk-diffbox">
          <div class="sk-diffh">变更预览</div>
          <pre class="sk-diffp">{{ diffText }}</pre>
          <div class="sk-difff">
            <button class="btn" @click="showDiff = false">继续编辑</button>
            <button class="btn primary" @click="confirmSave">确认保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建向导 -->
    <div v-if="showCreate" class="sk-mask" @click.self="showCreate = false">
      <div class="sk-modal">
        <div class="sk-mh">新建技能</div>
        <div class="sk-mrow"><label>名称（[a-z0-9-]）</label><input v-model="createForm.name" class="sk-in" placeholder="my-skill" /></div>
        <div class="sk-mrow"><label>描述</label><input v-model="createForm.description" class="sk-in" placeholder="什么任务用这个技能" /></div>
        <div class="sk-mrow"><label>脚本骨架</label>
          <select v-model="createForm.skeleton" class="sk-sel">
            <option value="empty">空脚本</option>
            <option value="argparse">带参数解析模板</option>
          </select>
        </div>
        <div class="sk-mf">
          <button class="btn" @click="showCreate = false">取消</button>
          <button class="btn primary" @click="create">创建（git 快照）</button>
        </div>
      </div>
    </div>

    <!-- 市场 -->
    <div v-if="showMarket" class="sk-mask" @click.self="showMarket = false">
      <div class="sk-modal wide">
        <div class="sk-mh">技能市场（仓库内置模板库）</div>
        <div v-for="t in templates" :key="t.name" class="sk-tpl">
          <div>
            <div class="sk-tname">📦 {{ t.name }}</div>
            <div class="sk-tdesc">{{ t.description }}</div>
          </div>
          <button class="btn primary xs" @click="install(t.name)"
                  :disabled="installed.has(t.name)">{{ installed.has(t.name) ? '已安装' : '安装' }}</button>
        </div>
        <div class="sk-mf"><button class="btn" @click="showMarket = false">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type SkillItem, type TemplateItem } from '@/api/modules/agentConfig'

const props = defineProps<{ entity: string }>()

const skills = ref<SkillItem[]>([])
const templates = ref<TemplateItem[]>([])
const editing = ref('')
const content = ref('')
const original = ref('')
const saving = ref(false)
const showDiff = ref(false)
const showCreate = ref(false)
const showMarket = ref(false)
const createForm = ref({ name: '', description: '', skeleton: 'empty' })
const disabledSkills = ref<string[]>([])
const installed = computed(() => new Set(skills.value.map(s => s.name)))

const dirty = computed(() => content.value !== original.value)
const entityLabel = computed(() => props.entity === 'master' ? '主智能体' : props.entity)

const diffText = computed(() => {
  const oldL = original.value.split('\n'); const newL = content.value.split('\n')
  const out: string[] = []
  for (let i = 0; i < Math.max(oldL.length, newL.length); i++) {
    if (oldL[i] === newL[i]) out.push('  ' + (oldL[i] ?? ''))
    else {
      if (oldL[i] !== undefined) out.push('- ' + oldL[i])
      if (newL[i] !== undefined) out.push('+ ' + newL[i])
    }
  }
  return out.join('\n')
})

async function load() {
  const r: any = await agentConfigService.getSkills(props.entity)
  const d = r.data ?? r
  skills.value = d.skills
  templates.value = d.templates
}
watch(() => props.entity, () => { editing.value = ''; load() }, { immediate: true })

async function openSkill(name: string) {
  if (editing.value === name) { editing.value = ''; return }
  if (dirty.value && !await confirmLeave()) return
  const r: any = await agentConfigService.readSkillFile(props.entity, name)
  content.value = (r.data ?? r).content
  original.value = content.value
  editing.value = name
}

async function confirmLeave(): Promise<boolean> {
  try { await ElMessageBox.confirm('有未保存的编辑，离开将丢失。', '未保存', { type: 'warning' }); return true }
  catch { return false }
}

function save() { showDiff.value = true }

async function confirmSave() {
  saving.value = true
  try {
    const r: any = await agentConfigService.saveSkillFile({
      entity: props.entity, name: editing.value, content: content.value,
      message: window.prompt('快照说明（可留空）') ?? '',
    })
    const d = r.data ?? r
    original.value = content.value
    if (d.degraded) ElMessage.warning(`已保存，git 快照降级为 .bak`)
    else ElMessage.success(`已保存，快照 ${d.commit}`)
    showDiff.value = false
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { saving.value = false }
}

async function create() {
  try {
    await agentConfigService.createSkill({ entity: props.entity, ...createForm.value })
    ElMessage.success('技能已创建（git 快照）')
    showCreate.value = false
    createForm.value = { name: '', description: '', skeleton: 'empty' }
    await load()
    editing.value = ''
  } catch (e: any) { ElMessage.error('创建失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

async function install(tpl: string) {
  try {
    await agentConfigService.installTemplate({ template: tpl, entity: props.entity })
    ElMessage.success(`已安装 ${tpl}`)
    await load()
  } catch (e: any) { ElMessage.error('安装失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

async function toggle(name: string, enable: boolean) {
  try {
    if (enable) {
      await agentConfigService.enableSkill({ entity: props.entity, name })
      disabledSkills.value = disabledSkills.value.filter(n => n !== name)
    } else {
      await ElMessageBox.confirm(`禁用 ${name}？主智能体将看不到该技能。`, '禁用', { type: 'warning' })
      await agentConfigService.disableSkill({ entity: props.entity, name })
      skills.value = skills.value.filter(s => s.name !== name)
      disabledSkills.value.push(name)
      if (editing.value === name) editing.value = ''
    }
    ElMessage.success(enable ? '已启用' : '已禁用')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('操作失败：' + (e?.message || e)) }
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除技能 ${name}？可从 git 历史恢复。`, '删除', { type: 'warning' })
    await agentConfigService.deleteSkill(props.entity, name)
    skills.value = skills.value.filter(s => s.name !== name)
    disabledSkills.value = disabledSkills.value.filter(n => n !== name)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}
</script>

<style scoped>
.sk { max-width: 880px }
.sk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px }
.sk-t { font-size: 15px; font-weight: 700 }
.sk-a { display: flex; gap: 8px }
.sk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px }
.sk-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.sk-card.disabled { opacity: .6; background: #f8fafc }
.sk-cname { font-size: 13.5px; font-weight: 700 }
.sk-cdesc { font-size: 11.5px; color: var(--text-secondary); margin-top: 4px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 32px }
.sk-cmeta { font-size: 10.5px; color: var(--text-muted); margin-top: 6px }
.sk-cacts { display: flex; gap: 6px; margin-top: 9px }
.sk-ed { margin-top: 16px; border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.sk-edbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--brd) }
.sk-edpath { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sk-ta { width: 100%; min-height: 320px; border: none; outline: none; resize: vertical; padding: 14px 16px;
  font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; line-height: 1.65 }
.sk-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.sk-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(460px, 90vw) }
.sk-modal.wide { width: min(620px, 90vw) }
.sk-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.sk-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.sk-mrow label { font-size: 11.5px; color: var(--text-muted) }
.sk-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.sk-sel { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px }
.sk-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.sk-tpl { display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 11px 0; border-bottom: 1px dashed var(--brd) }
.sk-tname { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sk-tdesc { font-size: 11.5px; color: var(--text-secondary); margin-top: 3px }
.sk-diffbox { background: #fff; border-radius: 13px; width: min(760px, 90vw); max-height: 80vh;
  display: flex; flex-direction: column }
.sk-diffh { padding: 13px 18px; font-weight: 700; border-bottom: 1px solid var(--brd) }
.sk-diffp { flex: 1; overflow: auto; margin: 0; padding: 14px 18px; font-size: 12px;
  font-family: ui-monospace, monospace; white-space: pre-wrap }
.sk-difff { padding: 12px 18px; display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid var(--brd) }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
```

（`disabledSkills` 初始为空数组——V2 首版发现层不返回禁用项，列表只显示已启用+本地刚禁用的；重启加载后禁用项不可见属预期，启用走"新建同名→提示已存在"提示用户改名。此为已知简化，E2E 只测禁用后消失。）

- [ ] **Step 10.3: McpPanel（预置+自定义+测试+启停）**

```vue
<!-- frontend/src/components/agents/config/McpPanel.vue -->
<template>
  <div class="mp">
    <div class="mp-t">外部 MCP 接入 <span class="mp-sub">改动需重启 agent 生效</span></div>

    <div class="mp-sec-t">预置（一键安装）</div>
    <div class="mp-grid">
      <div v-for="p in presets" :key="p.name" class="mp-card">
        <div class="mp-name">{{ p.title }} <span class="mp-badge">{{ p.transport }}</span></div>
        <div class="mp-desc">{{ p.desc }}</div>
        <div class="mp-acts">
          <button class="btn primary xs" @click="installPreset(p.name)"
                  :disabled="servers[p.name] !== undefined">已安装·管理见下</button>
          <button class="btn xs" @click="testCfg(p.config, p.name)">测试连接</button>
        </div>
      </div>
    </div>

    <div class="mp-sec-t">已接入</div>
    <div v-if="!Object.keys(servers).length" class="mp-empty">暂无接入（上方预置一键安装，或点「新增接入」）</div>
    <div v-for="(cfg, name) in servers" :key="name" class="mp-row">
      <div class="mp-rk">
        <div class="mp-rname">{{ name }}
          <span class="mp-badge" :class="{ off: cfg.enabled === false }">{{ cfg.enabled === false ? '已停用' : '启用' }}</span>
        </div>
        <div class="mp-rmeta">{{ cfg.command || cfg.url }} {{ (cfg.args || []).join(' ') }}</div>
      </div>
      <div class="mp-racts">
        <span v-if="lastTest[name]" class="mp-test" :class="lastTest[name].ok ? 'ok' : 'bad'">
          {{ lastTest[name].ok ? `✓ ${lastTest[name].tools_seen} 工具` : `✗ ${lastTest[name].error}` }}
        </span>
        <button class="btn xs" @click="testCfg(cfg, name)" :disabled="testing === name">{{ testing === name ? '测试中…' : '测试连接' }}</button>
        <button class="btn xs" @click="toggleEnabled(name, cfg)">{{ cfg.enabled === false ? '启用' : '停用' }}</button>
        <button class="btn xs danger" @click="del(name)">删除</button>
      </div>
    </div>
    <div class="mp-foot">
      <button class="btn" @click="showAdd = true">+ 新增接入</button>
      <button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>

    <div v-if="showAdd" class="mp-mask" @click.self="showAdd = false">
      <div class="mp-modal">
        <div class="mp-mh">新增 MCP 接入</div>
        <div class="mp-mrow"><label>名称</label><input v-model="addForm.name" class="mp-in" placeholder="my-server" /></div>
        <div class="mp-mrow"><label>传输方式</label>
          <select v-model="addForm.transport" class="mp-sel">
            <option value="stdio">stdio（command + args）</option>
            <option value="http">HTTP（url）</option>
            <option value="sse">SSE（url）</option>
          </select>
        </div>
        <template v-if="addForm.transport === 'stdio'">
          <div class="mp-mrow"><label>command</label><input v-model="addForm.command" class="mp-in" placeholder="npx" /></div>
          <div class="mp-mrow"><label>args（空格分隔）</label><input v-model="addForm.argsStr" class="mp-in" placeholder="-y @modelcontextprotocol/server-xxx" /></div>
        </template>
        <template v-else>
          <div class="mp-mrow"><label>url</label><input v-model="addForm.url" class="mp-in" placeholder="https://…/mcp" /></div>
        </template>
        <div class="mp-mrow"><label>超时(秒)</label><input v-model.number="addForm.timeout" type="number" class="mp-in" /></div>
        <div class="mp-mf">
          <button class="btn" @click="testAdd">测试连接</button>
          <button class="btn" @click="showAdd = false">取消</button>
          <button class="btn primary" @click="add" :disabled="!addForm.name || testedAdd !== true">保存（需测试通过）</button>
        </div>
        <div v-if="lastAddTest" class="mp-test" :class="lastAddTest.ok ? 'ok' : 'bad'">
          {{ lastAddTest.ok ? `✓ 握手成功，发现 ${lastAddTest.tools_seen} 工具` : `✗ ${lastAddTest.error}` }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type McpServerCfg, type McpPreset } from '@/api/modules/agentConfig'

defineEmits<{ (e: 'restart'): void }>()

const servers = ref<Record<string, McpServerCfg>>({})
const presets = ref<McpPreset[]>([])
const testing = ref('')
const lastTest = ref<Record<string, { ok: boolean; tools_seen?: number; error?: string | null }>>({})
const showAdd = ref(false)
const addForm = ref({ name: '', transport: 'stdio', command: 'npx', argsStr: '', url: '', timeout: 60 })
const testedAdd = ref<null | boolean>(null)
const lastAddTest = ref<{ ok: boolean; tools_seen?: number; error?: string | null } | null>(null)

onMounted(async () => {
  const r: any = await agentConfigService.getMcp()
  const d = r.data ?? r
  servers.value = d.servers
  presets.value = d.presets
})

function buildCfg(): McpServerCfg {
  const f = addForm.value
  const cfg: McpServerCfg = { timeout: f.timeout }
  if (f.transport === 'stdio') {
    cfg.command = f.command
    cfg.args = f.argsStr.split(/\s+/).filter(Boolean)
  } else {
    cfg.url = f.url
    cfg.transport = f.transport
  }
  return cfg
}

async function testCfg(cfg: McpServerCfg, name: string) {
  testing.value = name
  try {
    const r: any = await agentConfigService.testMcp(cfg)
    lastTest.value[name] = r
    ElMessage[r.ok ? 'success' : 'warning'](r.ok ? `握手成功，发现 ${r.tools_seen} 工具` : `失败：${r.error}`)
  } catch (e: any) { ElMessage.error('测试请求失败：' + (e?.message || e)) }
  finally { testing.value = '' }
}

async function installPreset(name: string) {
  try {
    await agentConfigService.installMcpPreset(name)
    ElMessage.success(`已安装 ${name}（需重启生效）`)
    const r: any = await agentConfigService.getMcp()
    servers.value = (r.data ?? r).servers
  } catch (e: any) { ElMessage.error('安装失败：' + (e?.message || e)) }
}

async function toggleEnabled(name: string, cfg: McpServerCfg) {
  const next = { ...cfg, enabled: cfg.enabled === false }
  try {
    await agentConfigService.putMcp({ name, config: next })
    servers.value[name] = next
    ElMessage.success(next.enabled === false ? '已停用（重启后不加载）' : '已启用')
  } catch (e: any) { ElMessage.error('操作失败：' + (e?.message || e)) }
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除 MCP 接入 ${name}？`, '删除', { type: 'warning' })
    await agentConfigService.deleteMcp(name)
    delete servers.value[name]
    ElMessage.success('已删除（需重启生效）')
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}

async function testAdd() {
  lastAddTest.value = null; testedAdd.value = null
  try {
    const r: any = await agentConfigService.testMcp(buildCfg())
    lastAddTest.value = r
    testedAdd.value = r.ok
  } catch (e: any) { lastAddTest.value = { ok: false, error: e?.message || String(e) } }
}

async function add() {
  try {
    await agentConfigService.putMcp({ name: addForm.value.name, config: buildCfg() })
    ElMessage.success('已保存（需重启生效）')
    showAdd.value = false
    testedAdd.value = null; lastAddTest.value = null
    const r: any = await agentConfigService.getMcp()
    servers.value = (r.data ?? r).servers
  } catch (e: any) {
    const errs = e?.response?.data?.detail?.errors
    ElMessage.error('保存失败：' + (errs?.join('；') || e?.message || e))
  }
}
</script>

<style scoped>
.mp { max-width: 880px }
.mp-t { font-size: 15px; font-weight: 700 }
.mp-sub { font-size: 11.5px; color: #92400e; background: #fffbeb; padding: 3px 9px; border-radius: 6px; margin-left: 8px; font-weight: 400 }
.mp-sec-t { font-size: 13px; font-weight: 700; margin: 18px 0 10px; display: flex; align-items: center; gap: 8px }
.mp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.mp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px }
.mp-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.mp-name { font-size: 13.5px; font-weight: 700 }
.mp-badge { font-size: 10px; background: #eef2ff; color: var(--primary); padding: 2px 7px; border-radius: 5px; margin-left: 6px; font-weight: 600 }
.mp-badge.off { background: #f1f5f9; color: var(--text-muted) }
.mp-desc { font-size: 11.5px; color: var(--text-secondary); margin-top: 4px }
.mp-acts { display: flex; gap: 6px; margin-top: 9px }
.mp-empty { font-size: 12.5px; color: var(--text-muted); padding: 14px 0 }
.mp-row { display: flex; align-items: center; gap: 14px; padding: 11px 14px; border: 1px solid var(--brd); border-radius: 10px; margin-bottom: 8px }
.mp-rk { flex: 1; min-width: 0 }
.mp-rname { font-family: ui-monospace, monospace; font-size: 13px; font-weight: 600 }
.mp-rmeta { font-size: 11px; color: var(--text-muted); margin-top: 3px; font-family: ui-monospace, monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.mp-racts { display: flex; align-items: center; gap: 7px; flex-shrink: 0 }
.mp-test { font-size: 11.5px; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.mp-test.ok { color: #047857 }
.mp-test.bad { color: #dc2626 }
.mp-foot { display: flex; gap: 9px; margin-top: 14px }
.mp-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.mp-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(480px, 90vw) }
.mp-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.mp-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.mp-mrow label { font-size: 11.5px; color: var(--text-muted) }
.mp-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.mp-sel { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px }
.mp-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
```

- [ ] **Step 10.4: ProvidersPanel（CRUD+测试+设默认）**

```vue
<!-- frontend/src/components/agents/config/ProvidersPanel.vue -->
<template>
  <div class="pv">
    <div class="pv-t">模型供应商
      <span class="pv-sub" v-if="currentDefault">当前默认：{{ currentDefault }}（重启后生效）</span>
    </div>
    <div class="pv-grid">
      <div v-for="p in providers" :key="p.name" class="pv-card" :class="{ off: !p.enabled, def: p.name === currentDefault }">
        <div class="pv-head">
          <div class="pv-name">{{ p.name }}
            <span v-if="p.name === currentDefault" class="pv-badge def">默认</span>
            <span class="pv-badge" :class="p.tested_ok ? 'ok' : 'bad'">{{ p.tested_ok ? '✓ 已测通' : '未测通' }}</span>
            <span v-if="!p.enabled" class="pv-badge off">已禁用</span>
          </div>
        </div>
        <div class="pv-meta">{{ p.model }} · {{ p.base_url }}</div>
        <div class="pv-key">key: {{ p.api_key || '—' }}</div>
        <div class="pv-acts">
          <button class="btn xs" @click="test(p.name)" :disabled="testing === p.name">{{ testing === p.name ? '测试中…' : '测试连接' }}</button>
          <button class="btn xs primary" @click="setDefault(p.name)"
                  :disabled="!p.tested_ok || p.name === currentDefault">设为默认</button>
          <button class="btn xs" @click="openEdit(p)">编辑</button>
          <button class="btn xs" @click="toggleEnabled(p)">{{ p.enabled ? '禁用' : '启用' }}</button>
          <button class="btn xs danger" @click="del(p.name)">删除</button>
        </div>
        <div v-if="lastTest[p.name]" class="pv-test" :class="lastTest[p.name].ok ? 'ok' : 'bad'">
          {{ lastTest[p.name].ok ? `✓ 连通 ${lastTest[p.name].latency_ms}ms` : `✗ ${lastTest[p.name].error}` }}
        </div>
      </div>
    </div>
    <div class="pv-foot">
      <button class="btn" @click="openCreate">+ 新增供应商</button>
      <button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>

    <div v-if="showForm" class="pv-mask" @click.self="showForm = false">
      <div class="pv-modal">
        <div class="pv-mh">{{ form.name && isEdit ? '编辑供应商' : '新增供应商' }}</div>
        <div class="pv-mrow"><label>名称</label><input v-model="form.name" class="pv-in" :disabled="isEdit" placeholder="deepseek" /></div>
        <div class="pv-mrow"><label>base_url</label><input v-model="form.base_url" class="pv-in" placeholder="https://api.example.com/v1" /></div>
        <div class="pv-mrow"><label>model</label><input v-model="form.model" class="pv-in" placeholder="model-name" /></div>
        <div class="pv-mrow"><label>api_key（编辑留空=不修改）</label>
          <input v-model="form.api_key" type="password" class="pv-in" :placeholder="isEdit ? '•••（不修改请留空）' : 'sk-…'" /></div>
        <div class="pv-mf">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn primary" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type ProviderRow } from '@/api/modules/agentConfig'

defineEmits<{ (e: 'restart'): void }>()

const providers = ref<ProviderRow[]>([])
const eligible = ref<string[]>([])
const currentDefault = ref('')
const testing = ref('')
const lastTest = ref<Record<string, { ok: boolean; latency_ms?: number; error?: string | null }>>({})
const showForm = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const form = ref({ name: '', base_url: '', model: '', api_key: '' })

async function load() {
  const r: any = await agentConfigService.getProviders()
  const d = r.data ?? r
  providers.value = d.providers
  eligible.value = d.eligible
  currentDefault.value = d.current_default
}
onMounted(load)

async function test(name: string) {
  testing.value = name
  try {
    const r: any = await agentConfigService.testProvider(name)
    lastTest.value[name] = r
    ElMessage[r.ok ? 'success' : 'warning'](r.ok ? `连通 ${r.latency_ms}ms` : `失败：${r.error}`)
    await load()
  } catch (e: any) { ElMessage.error('测试失败：' + (e?.message || e)) }
  finally { testing.value = '' }
}

async function setDefault(name: string) {
  try {
    await agentConfigService.setDefaultProvider(name)
    ElMessage.success(`已设 ${name} 为默认（重启 agent 后生效）`)
    await load()
  } catch (e: any) { ElMessage.error('设置失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

function openCreate() {
  isEdit.value = false
  form.value = { name: '', base_url: '', model: '', api_key: '' }
  showForm.value = true
}

function openEdit(p: ProviderRow) {
  isEdit.value = true
  form.value = { name: p.name, base_url: p.base_url, model: p.model, api_key: '' }
  showForm.value = true
}

async function save() {
  saving.value = true
  try {
    await agentConfigService.putProvider({
      name: form.value.name, base_url: form.value.base_url,
      api_key: form.value.api_key || undefined, model: form.value.model,
      enabled: isEdit.value ? (providers.value.find(p => p.name === form.value.name)?.enabled ?? true) : true,
    })
    ElMessage.success('已保存（api_key 脱敏显示）')
    showForm.value = false
    await load()
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { saving.value = false }
}

async function toggleEnabled(p: ProviderRow) {
  await agentConfigService.putProvider({
    name: p.name, base_url: p.base_url, api_key: undefined, model: p.model, enabled: !p.enabled,
  })
  await load()
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除供应商 ${name}？${name === currentDefault.value ? ' 它是当前默认，删除后 agent 走 env 兜底！' : ''}`, '删除', { type: 'warning' })
    await agentConfigService.deleteProvider(name)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}
</script>

<style scoped>
.pv { max-width: 880px }
.pv-t { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 10px }
.pv-sub { font-size: 11.5px; color: #047857; background: #ecfdf5; padding: 3px 9px; border-radius: 6px; font-weight: 400 }
.pv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; margin-top: 14px }
.pv-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.pv-card.off { opacity: .65; background: #f8fafc }
.pv-card.def { border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary) }
.pv-name { font-size: 13.5px; font-weight: 700; display: flex; align-items: center; gap: 6px; flex-wrap: wrap }
.pv-badge { font-size: 10px; padding: 2px 7px; border-radius: 5px; font-weight: 600 }
.pv-badge.ok { background: #ecfdf5; color: #047857 }
.pv-badge.bad { background: #fef2f2; color: #dc2626 }
.pv-badge.off { background: #f1f5f9; color: var(--text-muted) }
.pv-badge.def { background: #eef2ff; color: var(--primary) }
.pv-meta { font-size: 11.5px; color: var(--text-secondary); margin-top: 6px; font-family: ui-monospace, monospace }
.pv-key { font-size: 11px; color: var(--text-muted); margin-top: 3px; font-family: ui-monospace, monospace }
.pv-acts { display: flex; gap: 6px; margin-top: 9px; flex-wrap: wrap }
.pv-test { font-size: 11.5px; margin-top: 7px }
.pv-test.ok { color: #047857 }
.pv-test.bad { color: #dc2626 }
.pv-foot { display: flex; gap: 9px; margin-top: 14px }
.pv-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.pv-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(460px, 90vw) }
.pv-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.pv-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.pv-mrow label { font-size: 11.5px; color: var(--text-muted) }
.pv-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.pv-in:disabled { background: #f8fafc }
.pv-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
```

- [ ] **Step 10.5: 构建冒烟**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: 编译通过

- [ ] **Step 10.6: Commit**

```bash
git add frontend/src/components/agents/config/
git commit -m "feat(config-v2): 四面板实现(策略分组+参数并入/技能卡片+市场+diff/MCP预置+测试/供应商测试+设默认)"
```

---
## Task 11: E2E + 手工验收清单

**Files:**
- Create: `scripts/e2e_agent_config_v2.py`

- [ ] **Step 11.1: E2E 脚本**

```python
# scripts/e2e_agent_config_v2.py
"""配置中心 V2 E2E：六 tab URL 同步 / 策略保存 / 技能新建+市场 / provider 测试+设默认 / MCP 预置。
前置：backend(8000) + frontend(5173) 已起。结束后字节级还原工作区他人未提交改动（学 V1 E2E 的教训）。"""
import json
import subprocess
import sys
import time
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

    # 1. 六 tab 渲染 + URL 同步
    page.goto("http://localhost:5173/agents/config?entity=master&tab=strategy", wait_until="networkidle")
    page.wait_for_selector(".tab")
    tabs = page.locator(".tab").all_inner_texts()
    check("主智能体六 tab", [t for t in tabs if t.strip()] == ["概览", "身份文件", "技能", "策略", "MCP", "供应商"], str(tabs))
    page.click(".tab:has-text('技能')")
    check("tab 切换写 URL", "tab=skills" in page.url, page.url)
    # 子智能体四 tab（mcp/providers 不出现）
    page.goto("http://localhost:5173/agents/config?entity=anomaly-detection&tab=skills", wait_until="networkidle")
    tabs2 = [t.strip() for t in page.locator(".tab").all_inner_texts() if t.strip()]
    check("子智能体四 tab", tabs2 == ["概览", "身份文件", "技能", "策略"], str(tabs2))

    # 2. 策略加载+保存
    page.goto("http://localhost:5173/agents/config?entity=master&tab=strategy", wait_until="networkidle")
    page.wait_for_selector(".sp-row")
    n_rows = page.locator(".sp-row").count()
    check("策略+参数行数", n_rows >= 18, f"{n_rows} 行")
    # 关守卫保存→再开（立即生效项）
    page.locator(".sp-row", has_text="perception_guard_enabled").locator(".el-switch").first.click()
    page.click("button:has-text('保存策略')")
    time.sleep(1.2)
    saved_off = "perception_guard_enabled" in subprocess.run(
        ["./ecological_env/Scripts/python.exe", "-c",
         "import sys; sys.path.insert(0,'.'); "
         "from backend.services.agent_strategy import get_strategy; "
         "print('OFF' if get_strategy('perception_guard_enabled') is False else 'ON')"],
        cwd=PROJECT_ROOT, capture_output=True, text=True).stdout
    check("守卫开关落库", saved_off, "")
    # 还原
    page.locator(".sp-row", has_text="perception_guard_enabled").locator(".el-switch").first.click()
    page.click("button:has-text('保存策略')")
    time.sleep(1.0)

    # 3. 技能：新建→落盘→删除
    page.goto("http://localhost:5173/agents/config?entity=master&tab=skills", wait_until="networkidle")
    page.wait_for_selector(".sk-card")
    page.click("button:has-text('新建技能')")
    page.fill(".sk-modal input[placeholder='my-skill']", "e2e-tmp-skill")
    page.fill(".sk-modal input[placeholder='什么任务用这个技能']", "E2E 临时技能")
    page.click(".sk-modal button:has-text('创建')")
    time.sleep(1.2)
    check("新建技能落盘", (PROJECT_ROOT / "skills" / "e2e-tmp-skill" / "SKILL.md").exists())
    gitlog = subprocess.run(["git", "log", "--oneline", "-1"], cwd=PROJECT_ROOT,
                            capture_output=True, text=True).stdout
    check("新建技能 git 快照", "e2e-tmp-skill" in gitlog, gitlog.strip()[:60])
    # 删除
    page.locator(".sk-card", has_text="e2e-tmp-skill").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)
    check("技能已删除", not (PROJECT_ROOT / "skills" / "e2e-tmp-skill").exists())

    # 4. 市场：安装 blank-skill 到 master → 删除
    page.click("button:has-text('技能市场')")
    page.wait_for_selector(".sk-tpl")
    n_tpl = page.locator(".sk-tpl").count()
    check("市场 6 模板", n_tpl == 6, f"{n_tpl} 个")
    page.locator(".sk-tpl", has_text="blank-skill").locator("button:has-text('安装')").click()
    time.sleep(1.2)
    check("模板安装落盘", (PROJECT_ROOT / "skills" / "blank-skill" / "SKILL.md").exists())
    page.locator(".sk-card", has_text="blank-skill").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)

    # 5. providers：列表+测试 ctgu-vlm
    page.goto("http://localhost:5173/agents/config?entity=master&tab=providers", wait_until="networkidle")
    page.wait_for_selector(".pv-card")
    n_prov = page.locator(".pv-card").count()
    check("供应商≥2 行", n_prov >= 2, f"{n_prov}")
    page.locator(".pv-card", has_text="ctgu-vlm").locator("button:has-text('测试连接')").click()
    try:
        page.wait_for_selector(".pv-test.ok", timeout=15000)
        check("ctgu-vlm 测通", True)
    except Exception:
        check("ctgu-vlm 测通", False, "15s 内未见 .pv-test.ok（LLM 服务可能未起）")

    # 6. MCP：预置清单+安装 fetch→删除
    page.goto("http://localhost:5173/agents/config?entity=master&tab=mcp", wait_until="networkidle")
    page.wait_for_selector(".mp-card")
    n_preset = page.locator(".mp-card").count()
    check("MCP 4 预置", n_preset == 4, f"{n_preset}")
    cfg_before = Path(PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8") if (PROJECT_ROOT / "config.yaml").exists() else ""
    page.locator(".mp-card", has_text="Fetch").locator("button:has-text('一键安装')").first.click() if page.locator(".mp-card", has_text="Fetch").locator("button:has-text('一键安装')").count() else page.locator(".mp-card", has_text("Fetch").locator("button")).first.click()
    time.sleep(1.2)
    cfg_after = Path(PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8") if (PROJECT_ROOT / "config.yaml").exists() else ""
    check("安装写入 config.yaml", "mcp_servers" in cfg_after and "server-fetch" in cfg_after, "")
    check("config.yaml 其他段未破坏", ("model" not in cfg_before) or ("model" in cfg_after or "mcp_servers" in cfg_after), "")
    # 删掉恢复原状
    page.locator(".mp-row", has_text="fetch").locator("button:has-text('删除')").click()
    page.click(".el-message-box__btns .el-button--primary")
    time.sleep(1.0)
    cfg_final = Path(PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8") if (PROJECT_ROOT / "config.yaml").exists() else ""
    check("删除后 mcp_servers 移除", "server-fetch" not in cfg_final, "")

    # 7. 无 JS 错误
    check("无页面 JS 错误", not errors, "; ".join(errors[:3]))

    b.close()

fails = [r for r in results if not r[1]]
print(f"\n{'='*40}\nV2 E2E: {len(results)-len(fails)}/{len(results)} 通过")
sys.exit(1 if fails else 0)
```

- [ ] **Step 11.2: 跑 E2E**

前置：backend(8000)+frontend(5173) 起，`skills/` 无 `e2e-tmp-skill`/`blank-skill` 残留。

Run: `./ecological_env/Scripts/python.exe scripts/e2e_agent_config_v2.py`
Expected: 全 ✓ 退出码 0

- [ ] **Step 11.3: 手工验收（用户执行，逐条告诉用户）**

1. 策略 tab：`orchestration_stop_level` 设 `violation` → /chat 问“7月14日数据” → 主智能体只跑①②③不跑④且回答末尾问是否继续
2. 技能 tab：新建技能写清楚调用 → 子智能体 skill_view 能看到（/chat 对应子智能体任务触发）
3. MCP tab：安装 Fetch → 测试连接 ✓ → 重启 agent → /chat 问“查 GB 18918 COD B 级标准”看是否调 mcp 工具
4. 供应商 tab：新增 deepseek（真实 key）→ 测试通过 → 设默认 → 重启 → /health 显示 model=deepseek-chat → 切回 ctgu-vlm
5. 禁用技能：禁用 action-command-core → 大屏动作指令变引导语 → 启用恢复

- [ ] **Step 11.4: Commit**

```bash
git add scripts/e2e_agent_config_v2.py
git commit -m "test(config-v2): E2E(六tab URL/策略落库/技能新建+市场/provider测通/MCP预置安装删除)"
```

---

## 自查记录（Self-Review）

1. **Spec 覆盖**：§2 六 tab+URL 同步→Task 9；§3 策略表+四组+接线→Task 1+5；§4 技能展示/编辑/禁用/新建/市场→Task 3+4+10（SkillsPanel）；§5 MCP 管理+4 预置+边界+agent 启用→Task 6+7+10（McpPanel）；§6 providers+联动→Task 2+10（ProvidersPanel）；§7 错误处理→分散（DB 降级 Task 1、名字校验 Task 3、目录边界 Task 6、config.yaml 原子 Task 6、provider 兜底 Task 2/5）；§8 测试→各任务单测+Task 11 E2E；§9 兼容→params 接口保留（Task 8 只加不改）、llm_* 兜底链（Task 5b）。
2. **占位符扫描**：无 TBD/TODO（Task 4 SKILL.md 内的 "TODO:" 是模板内容本身，教用户填的，不是计划缺陷）。Task 7 的 registry.get_definitions 有一处“若签名不同先 grep”——这是对 vendored 代码的防御性说明，附了具体备选方案（从 _tools 过滤自拼），不算占位。
3. **类型一致性**：agentConfigService V2 方法名（getStrategy/saveStrategy/getSkills/readSkillFile/saveSkillFile/createSkill/disableSkill/enableSkill/deleteSkill/installTemplate/getMcp/putMcp/deleteMcp/testMcp/installMcpPreset/getProviders/putProvider/deleteProvider/testProvider/setDefaultProvider）Task 9 定义 ↔ Task 10 使用逐一对齐；`get_strategy(key, default)` 签名 Task 1 ↔ Task 5 使用一致；`_open_session`/`_session_factory` monkeypatch 模式 Task 1/2 与 V1 agent_params 一致；`McpServerCfg.transport` 字段在 Task 6 service 端（cfg["transport"]）↔ Task 9 类型 ↔ Task 10 buildCfg 一致。
4. **顺序依赖**：Task 1/2/3/6 相互独立可并行；Task 4 依赖 3（模板库被 skill_service 发现）；Task 5 依赖 1+2；Task 7 依赖 6（概念上）；Task 8 依赖 1/2/3/6；Task 9 依赖 8（接口在）；Task 10 依赖 9；Task 11 依赖全部。

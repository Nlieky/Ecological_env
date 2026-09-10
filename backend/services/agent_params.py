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
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 参数目录：default=未配置时的值；type=int/str/secret；effect=立即生效|需重启；
# reader=哪里读它（页面展示用）；env_key=对应的 .env 变量名（兜底来源）
PARAM_REGISTRY: dict = {
    # ── 超时层级（2026-09-10 修正倒挂：外层必须层层大于内层）────────────
    # 层级: AGENT_TIMEOUT(外,backend→agent HTTP) > TOTAL(中,单轮研判墙钟)
    #       > SUBAGENT_TIMEOUT(内,单子智能体)。
    # 合理配比: SUBAGENT 300 → TOTAL 900(3个子智能体串行余量) → AGENT 960(+HTTP 余量)
    "hermes_total_timeout": {"default": 900, "type": "int", "effect": "restart",
        "reader": "scripts/start_agent.py", "env_key": "HERMES_TOTAL_TIMEOUT",
        "desc": "主智能体单次研判墙钟(秒)——start_agent 线程级强制执行(引擎不读此env,服务侧自实现)。必须 > subagent_timeout"},
    "subagent_timeout": {"default": 300, "type": "int", "effect": "restart",
        "reader": "call_subagent.py", "env_key": "SUBAGENT_TIMEOUT",
        "desc": "单个子智能体 subprocess 超时(秒)。实测最快子智能体<90s;300 留 LLM 慢轮余量。必须 < hermes_total_timeout"},
    "agent_timeout": {"default": 960, "type": "int", "effect": "immediate",
        "reader": "backend/api/routes/query.py", "env_key": "AGENT_TIMEOUT",
        "desc": "后端→agent 服务 HTTP 超时(秒)，每请求读取。必须 > hermes_total_timeout(留 agent 服务处理余量)"},
    "master_max_iterations": {"default": 15, "type": "int", "effect": "restart",
        "reader": "scripts/start_agent.py", "env_key": None,
        "desc": "主智能体最大迭代轮数"},
    "subagent_max_iterations": {"default": 6, "type": "int", "effect": "restart",
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


def _open_session():
    """取一个可用的 Session。

    _session_factory() 生产返回 sessionmaker（可调用，调之得新 Session）；
    测试 monkeypatch 可能直接塞一个已实例化的 Session（不可调用）。
    两者都归一到这里，get_param/set_param 只管 `with _open_session() as s`。
    """
    obj = _session_factory()
    return obj() if callable(obj) else obj


def _convert(raw: Optional[str], ptype: str):
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
        with _open_session() as s:
            row = s.get(AgentRuntimeParam, key)
            if row is not None:
                v = _convert(row.value, ptype)
                if v is not None:
                    return v
    except Exception as exc:
        logger.warning("get_param(%s): DB 层不可用，走 env 兜底: %s", key, exc)
    if env_key:
        v = _convert(os.getenv(env_key), ptype)
        if v is not None:
            return v
    return default if default is not None else spec.get("default")


def set_param(key: str, value: str) -> None:
    from backend.models.agent_config import AgentRuntimeParam
    from sqlalchemy.sql import func
    with _open_session() as s:
        row = s.get(AgentRuntimeParam, key)
        if row:
            row.value = value
            row.updated_at = func.now()
        else:
            s.add(AgentRuntimeParam(key=key, value=value))
        s.commit()


def mask_secret(v: Optional[str]) -> str:
    if not v:
        return ""
    return f"{v[:3]}***{v[-4:]}" if len(v) > 8 else "***"

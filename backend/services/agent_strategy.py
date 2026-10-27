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
        "effect": "immediate", "group": "action", "desc": "动作分类器超时(秒)",
        "read_timing": "每次分类读取并设置该次 HTTP 请求超时"},
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
        logger.debug("get_strategy: 未注册 key %s", key)
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
    """按注册表 group 返回保存值/默认值，不证明运行进程已加载。"""
    groups: dict = {}
    for key, spec in STRATEGY_REGISTRY.items():
        item = {"key": key, "value": get_strategy(key), "default": spec["default"],
                "type": spec["type"], "effect": spec["effect"], "desc": spec.get("desc", ""),
                "choices": spec.get("choices")}
        item["read_timing"] = spec.get("read_timing", "重启服务后读取" if spec["effect"] == "restart" else "下次相关操作读取")
        groups.setdefault(spec["group"], []).append(item)
    return groups

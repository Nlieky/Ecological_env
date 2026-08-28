# backend/services/llm_providers.py
"""LLM 供应商 CRUD + tested_ok 闸门 + 默认供应商解析。

api_key 明文存 SQLite（本地单机场景，与 .env 同级）；仅接口层脱敏显示。

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
    """预置 ctgu-vlm（启用）+ LongCat-2.0（禁用）。幂等。

    首启两进程并发 seed 时败者收 IntegrityError → rollback 吞掉（行已由胜者插入），
    不让它冒泡成 500。"""
    from sqlalchemy.exc import IntegrityError
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        for name, base_url, model, enabled in [
            ("ctgu-vlm", "http://172.16.12.41:30000/v1", "ctgu-vlm", True),
            ("LongCat-2.0", "https://api.longcat.chat/openai/v1", "LongCat-2.0", False),
        ]:
            if s.get(LLMProvider, name) is None:
                s.add(LLMProvider(name=name, base_url=base_url, model=model, enabled=enabled))
                try:
                    s.commit()
                except IntegrityError:
                    s.rollback()


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
    """记录测试连接结果。状态转换操作，拼错名不该静默 no-op → raise KeyError。"""
    from backend.models.agent_config import LLMProvider
    with _open_session() as s:
        row = s.get(LLMProvider, name)
        if row is None:
            raise KeyError(f"供应商不存在: {name}")
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
    """策略名 → 供应商行；名不存在/行被删/未启用 → None（调用方走 get_param/env）。

    返回连接四元组 {name, base_url, api_key, model}（不脱敏，运行时接线用）；
    enabled/tested_ok 是闸门字段，在此已消费，不外泄。"""
    name = get_default_provider_name()
    if not name:
        return None
    row = get_provider_row(name)
    if row is None or not row["enabled"]:
        logger.warning("默认供应商 %s 不存在或未启用，走 env/get_param 兜底", name)
        return None
    return {"name": row["name"], "base_url": row["base_url"],
            "api_key": row["api_key"], "model": row["model"]}

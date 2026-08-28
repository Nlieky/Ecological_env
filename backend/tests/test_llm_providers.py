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
    # set_default_provider → set_strategy 写 agent_strategy 表：必须同样进临时库，
    # 否则会写真实生产库（V2 Task 1 审查抓过的隔离坑）。
    import backend.services.agent_strategy as strat
    monkeypatch.setattr(strat, "_session_factory", sm)
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


def test_resolve_default_disabled_returns_none(db_session):
    """enabled=False 的默认供应商：eligible 只看 tested_ok，可被设默认；resolve 消费 enabled 闸门。"""
    from backend.services.llm_providers import upsert_provider, mark_tested, set_default_provider, resolve_default
    upsert_provider("deepseek", base_url="http://x/v1", api_key="k", model="m", enabled=False)
    mark_tested("deepseek", ok=True)
    set_default_provider("deepseek")            # tested_ok 达标即可设
    assert resolve_default() is None            # 但禁用行不可被解析使用


def test_mark_tested_unknown_name_raises(db_session):
    """状态转换操作拼错名不该静默 no-op。"""
    from backend.services.llm_providers import mark_tested
    with pytest.raises(KeyError, match="供应商不存在"):
        mark_tested("ghost", ok=True)

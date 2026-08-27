# backend/tests/test_agent_params.py
"""agent_params 单测：注册表完整性 / get_param DB优先 / env兜底 / 类型转换 / 脱敏。
用独立临时 DB,不碰 shared/data/ecological_logs.db。"""
import sys
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
    # DB 层必须不可用——否则会读到真实生产库（shared/data/ecological_logs.db），
    # 测的就不是 env 回退路径，还会把真实 SessionLocal 缓存进模块 _factory。
    def _no_db():
        raise RuntimeError("no db in env-fallback test")
    monkeypatch.setattr("backend.services.agent_params._session_factory", _no_db)
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

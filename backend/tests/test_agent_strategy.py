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


def test_get_strategy_default_when_empty(monkeypatch):
    # DB 层必须不可用——否则会读到真实生产库（shared/data/ecological_logs.db），
    # 一旦有人 init_db + 存了非默认值，测的就不是内置默认路径。
    def _no_db():
        raise RuntimeError("no db in default-path test")
    monkeypatch.setattr("backend.services.agent_strategy._session_factory", _no_db)
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

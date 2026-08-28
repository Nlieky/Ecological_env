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

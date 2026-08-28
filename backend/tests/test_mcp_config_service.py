# backend/tests/test_mcp_config_service.py
"""mcp_config_service 单测：读写往返(只动 mcp_servers 段)/脱敏/校验/预置清单/HERMES_HOME 钉死。
临时 HERMES_HOME + 临时 PROJECT_ROOT（monkeypatch），不碰真实 config.yaml。"""
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
    # 服务会把 HERMES_HOME 钉死到 PROJECT_ROOT——fixture 同步钉到 tmp，保证不碰真实根
    monkeypatch.setattr(svc, "PROJECT_ROOT", tmp_path)
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
    good = str(svc.PROJECT_ROOT / "shared" / "knowledge")
    errs = svc.validate_server({"transport": "stdio", "command": "npx", "args": ["-y", "p"],
                                "allowed_dirs": [good]})
    assert errs == []


def test_validate_rejects_foreign_shared(home):
    """/shared/ 纯子串检查会放过 D:/other/shared/x——必须 resolve 后前缀比对到项目内 shared/。"""
    import backend.services.mcp_config_service as svc
    errs = svc.validate_server({"transport": "stdio", "command": "npx", "args": ["-y", "p"],
                                "allowed_dirs": ["D:/other/shared/x"]})
    assert any("目录" in e for e in errs)
    # 前缀边界逃逸（shared_evil 不是 shared 子路径）也必须拒
    evil = str(svc.PROJECT_ROOT / "shared_evil")
    errs = svc.validate_server({"transport": "stdio", "command": "npx", "args": ["-y", "p"],
                                "allowed_dirs": [evil]})
    assert any("目录" in e for e in errs)


def test_pins_to_project_root_over_env(tmp_path, monkeypatch):
    """本机有持久 HKCU HERMES_HOME=D:\Hermes——写入必须钉死项目根，不能跟随 env 分裂。"""
    fake_home = tmp_path / "fake-hermes-home"      # 模拟 D:\Hermes
    fake_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    proj = tmp_path / "projroot"                   # 模拟项目根
    proj.mkdir()
    import backend.services.mcp_config_service as svc
    monkeypatch.setattr(svc, "PROJECT_ROOT", proj)
    svc.upsert_server("fetch", {"command": "npx", "args": ["-y", "pkg"]})
    assert (proj / "config.yaml").exists()             # 写进了项目根
    assert not (fake_home / "config.yaml").exists()    # 没有跟 env 跑去假 home
    assert "fetch" in svc.list_servers()               # 读回也走项目根


def test_presets(home):
    import backend.services.mcp_config_service as svc
    presets = svc.list_presets()
    names = {p["name"] for p in presets}
    assert {"fetch", "influxdb", "filesystem", "memory"} <= names
    fs = next(p for p in presets if p["name"] == "filesystem")
    assert any("shared/knowledge" in a for a in fs["config"]["args"])

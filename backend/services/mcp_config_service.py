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

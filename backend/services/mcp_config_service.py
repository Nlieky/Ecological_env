# backend/services/mcp_config_service.py
"""MCP 接入管理：读写 hermes config.yaml 的 mcp_servers 段 + 校验 + 测试连接 + 预置。

铁律：**绝不能用 load_config() 的深合并结果回写**（会把几百行内置默认值落盘）——
统一 read_raw_config() → 只改 mcp_servers 键 → save_config()。
Filesystem 类 server 的目录边界只允许项目内 shared/ 子路径（防开盘符根/项目根）。
"""
import copy
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_HERMES_ROOT = PROJECT_ROOT / "shared" / "framework" / "hermes-agent"


def _load_hermes_cli():
    # 钉死 HERMES_HOME 到项目根：本机可能有持久用户级 HERMES_HOME（如 D:\Hermes），
    # 不钉死则 backend 进程读写用户目录、而 agent 服务（start_agent.py 显式设项目根）
    # 读项目根——写入/读取完全分裂，功能静默失效。backend 的 config 管理
    # 语义上就是管理 agent 的项目根配置，此钉死与 start_agent 保持一致。
    # 必须在 import hermes_cli 之前设置；get_hermes_home() 每次调用时读 env，故后续同样生效。
    os.environ["HERMES_HOME"] = str(PROJECT_ROOT)
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
    # 目录边界：resolve 后按路径组件前缀比对到项目内 shared/（纯子串检查会放过
    # D:/other/shared/x；纯字符串前缀会放过 …/shared_evil）。
    allowed_root = (PROJECT_ROOT / "shared").resolve()
    for d in cfg.get("allowed_dirs") or []:
        try:
            dd = Path(str(d)).resolve()
        except Exception:
            errs.append(f"目录边界必须是绝对路径: {d}")
            continue
        if dd.is_absolute() and dd.is_relative_to(allowed_root):
            continue
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
    """起一次性 stdio MCP 客户端握手 + tools/list。仅支持 stdio（预置全是）。

    MCP stdio 传输是换行分隔 JSON-RPC（NDJSON），不是 LSP 的 Content-Length 帧；
    必须先发 notifications/initialized 再 tools/list；用 bytes 模式避免 Windows CRLF 转换。
    """
    import json as _json
    import shutil
    import subprocess
    # Windows 下 npx/npm 是 .cmd 批处理，subprocess 不经 shell 时报 WinError 2——
    # 用 shutil.which 把 command 解析成磁盘真实路径（含 .cmd/.exe 扩展）。
    _raw = cfg.get("command") or ""
    _resolved = shutil.which(_raw) or _raw
    cmd = [_resolved] + list(cfg.get("args") or [])
    try:
        env = dict(os.environ)
        for k, v in (cfg.get("env") or {}).items():
            env[k] = os.path.expandvars(v)
        init = _json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                       "clientInfo": {"name": "eco-config", "version": "1.0"}}})
        ready = _json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        lst = _json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        payload = init + "\n" + ready + "\n" + lst + "\n"
        r = subprocess.run(cmd, input=payload.encode("utf-8"), capture_output=True,
                           timeout=cfg.get("connect_timeout", 120), env=env)
        out = (r.stdout or b"").decode("utf-8", errors="replace")
        ok = '"tools"' in out and '"result"' in out
        n = out.count('"name"')
        return {"ok": ok, "tools_seen": n if ok else 0,
                "error": None if ok else ((r.stderr or b"").decode("utf-8", "replace") or "握手无 tools 响应")[:200]}
    except Exception as e:
        return {"ok": False, "tools_seen": 0, "error": str(e)[:200]}

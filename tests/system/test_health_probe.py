# tests/system/test_health_probe.py
"""六服务健康探测 + 10s 缓存单测：mock 网络/文件系统，不碰真实服务。

get_system_status 是 async 路由但本仓库未装 pytest-asyncio，统一用
asyncio.run(...) 驱动（to_thread 在每次 run 的新事件环里正常工作）。
mock 面：httpx.head/get（默认 200=全 up，按 url 关键字配异常/状态码）、
settings.AGENT_SERVICE_URL/FRONTEND_URL、env LLM_BASE_URL、
discover_plants / influxdb_query.get_client_and_bucket、_LOGS_DB_PATH。
"""
import asyncio
import sqlite3

import httpx
import pytest

from backend.api.v1.system import routes as sys_routes

_SIX = ["backend", "agent", "influxdb", "frontend", "llm", "sqlite_logs"]


class _ClosingClient:
    def close(self):
        pass


@pytest.fixture(autouse=True)
def _reset_status_cache():
    """模块级探测缓存：每个用例前后清零，防跨用例串味。"""
    sys_routes._STATUS_CACHE["ts"] = 0.0
    sys_routes._STATUS_CACHE["data"] = None
    yield
    sys_routes._STATUS_CACHE["ts"] = 0.0
    sys_routes._STATUS_CACHE["data"] = None


@pytest.fixture
def env(monkeypatch, tmp_path):
    """隔离探测环境：mock httpx 与外部依赖，返回可编程规则表。"""
    state = {"rules": {}, "head_calls": 0, "get_calls": 0}

    class _Resp:
        def __init__(self, code):
            self.status_code = code

    def _resolve(url):
        for kw, outcome in state["rules"].items():
            if kw in url:
                if isinstance(outcome, Exception):
                    raise outcome
                return _Resp(outcome)
        return _Resp(200)  # 默认 up

    def fake_head(url, timeout=None):
        state["head_calls"] += 1
        return _resolve(url)

    def fake_get(url, timeout=None):
        state["get_calls"] += 1
        return _resolve(url)

    monkeypatch.setattr(httpx, "head", fake_head)
    monkeypatch.setattr(httpx, "get", fake_get)

    # settings 是 import 期实例化的单例，setenv 不生效——直接改对象属性
    from backend.core.config import settings
    monkeypatch.setattr(settings, "AGENT_SERVICE_URL", "http://agent.test")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://frontend.test")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")

    monkeypatch.setattr("shared.data.discover_plants.discover_plants",
                        lambda: [])
    monkeypatch.setattr("shared.data.influxdb_query.get_client_and_bucket",
                        lambda: (_ClosingClient(), "monitoring-data"))
    monkeypatch.setattr(sys_routes, "_LOGS_DB_PATH", tmp_path / "logs.db")
    return state


def _make_logs_db(path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS t(x)")
    conn.commit()
    conn.close()


def _svc_map(resp) -> dict:
    return {s["name"]: s["status"] for s in resp["data"]["services"]}


def test_six_services_all_up(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    resp = asyncio.run(sys_routes.get_system_status())
    assert resp["success"] is True
    assert [s["name"] for s in resp["data"]["services"]] == _SIX
    assert set(_svc_map(resp).values()) == {"up"}
    assert resp["data"]["generated_at"]
    assert resp["data"]["plants"] == []


def test_agent_and_llm_down(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    env["rules"] = {"/health": httpx.ConnectError("refused"),
                    "/models": 502}
    resp = asyncio.run(sys_routes.get_system_status())
    m = _svc_map(resp)
    assert m["agent"] == "down" and m["llm"] == "down"
    assert m["backend"] == "up" and m["influxdb"] == "up"
    assert m["frontend"] == "up" and m["sqlite_logs"] == "up"


def test_frontend_unreachable(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    env["rules"] = {"frontend.test": httpx.ConnectError("refused")}
    resp = asyncio.run(sys_routes.get_system_status())
    assert _svc_map(resp)["frontend"] == "down"


def test_influxdb_down_isolated(env, tmp_path, monkeypatch):
    _make_logs_db(tmp_path / "logs.db")

    def _boom():
        raise RuntimeError("influx unreachable")

    monkeypatch.setattr("shared.data.influxdb_query.get_client_and_bucket", _boom)
    resp = asyncio.run(sys_routes.get_system_status())
    m = _svc_map(resp)
    assert m["influxdb"] == "down"
    assert m["agent"] == "up" and m["sqlite_logs"] == "up"  # 单探失败不拖垮别的


def test_sqlite_logs_missing_file(env):
    # 不建 logs.db 文件 → down，其余 up
    resp = asyncio.run(sys_routes.get_system_status())
    m = _svc_map(resp)
    assert m["sqlite_logs"] == "down"
    assert m["backend"] == "up" and m["agent"] == "up"


def test_cache_hit_probes_once(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    r1 = asyncio.run(sys_routes.get_system_status())
    assert env["get_calls"] == 2  # agent /health + llm /models 各一次
    assert env["head_calls"] == 1  # frontend
    r2 = asyncio.run(sys_routes.get_system_status())
    assert env["get_calls"] == 2  # 缓存命中，未再探测
    assert env["head_calls"] == 1
    assert r1["data"]["services"] == r2["data"]["services"]


def test_cache_returns_deepcopy(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    r1 = asyncio.run(sys_routes.get_system_status())
    r1["data"]["services"][0]["status"] = "MUTATED"
    r2 = asyncio.run(sys_routes.get_system_status())
    assert r2["data"]["services"][0]["status"] == "up"  # 缓存原件未被污染


def test_cache_expiry_reprobes(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    asyncio.run(sys_routes.get_system_status())
    assert env["get_calls"] == 2
    # 模拟 TTL 过期：回拨缓存时间戳
    sys_routes._STATUS_CACHE["ts"] -= sys_routes._STATUS_TTL + 1.0
    asyncio.run(sys_routes.get_system_status())
    assert env["get_calls"] == 4  # 重新探测

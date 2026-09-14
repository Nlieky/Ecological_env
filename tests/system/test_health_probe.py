# tests/system/test_health_probe.py
"""六服务健康探测 + 10s 缓存单测：mock 网络/文件系统，不碰真实服务。

get_system_status 是 async 路由但本仓库未装 pytest-asyncio，统一用
asyncio.run(...) 驱动（to_thread 在每次 run 的新事件环里正常工作）。
mock 面：httpx.head/get（默认 200=全 up，按 url 关键字配异常/状态码）、
settings.AGENT_SERVICE_URL/FRONTEND_URL、agent_params.get_param（llm 探测
走配置中心链路）、discover_plants / influxdb_query.get_client_and_bucket
（假 client 用 health().status 表达连接语义）、_LOGS_DB_PATH。
"""
import asyncio
import sqlite3
import threading
import time
import types

import httpx
import pytest

from backend.api.v1.system import routes as sys_routes

_SIX = ["backend", "agent", "influxdb", "frontend", "llm", "sqlite_logs"]


class _FakeInfluxClient:
    """带 health() 的假 InfluxDBClient——连接语义由 health().status 承载。

    旧版 _ClosingClient（只有 close()）掩盖了「构造是惰性的、close 是空操作」
    这一事实，导致探测空转也报 up。假 client 同构暴露
    api_client.configuration.timeout：探测应在调 health() 前把默认 30_000ms
    收紧为 (1_000, 3_000)（connect/read 毫秒二元组），health() 时记录看到的
    值供断言。
    """

    def __init__(self, status="pass"):
        self.status = status
        self.health_calls = 0
        self.seen_timeout = None
        self.closed = False
        self.api_client = types.SimpleNamespace(
            configuration=types.SimpleNamespace(timeout=30_000))

    def health(self):
        self.health_calls += 1
        self.seen_timeout = self.api_client.configuration.timeout
        return types.SimpleNamespace(status=self.status)

    def close(self):
        self.closed = True


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
    state = {"rules": {}, "head_calls": 0, "get_calls": 0, "get_urls": [],
             "param_calls": [], "llm_base_url": "http://llm.test/v1",
             "influx": _FakeInfluxClient()}

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
        state["get_urls"].append(url)
        return _resolve(url)

    monkeypatch.setattr(httpx, "head", fake_head)
    monkeypatch.setattr(httpx, "get", fake_get)

    # settings 是 import 期实例化的单例，setenv 不生效——直接改对象属性
    from backend.core.config import settings
    monkeypatch.setattr(settings, "AGENT_SERVICE_URL", "http://agent.test")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://frontend.test")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")

    # llm 探测应走配置中心链路 get_param（DB 优先→env→默认），mock 之
    def fake_get_param(key, env_key=None, default=None):
        state["param_calls"].append(key)
        if key == "llm_base_url":
            return state["llm_base_url"]
        import os
        return os.environ.get(env_key or "", default)

    monkeypatch.setattr("backend.services.agent_params.get_param", fake_get_param)

    monkeypatch.setattr("shared.data.discover_plants.discover_plants",
                        lambda: [])
    monkeypatch.setattr("shared.data.influxdb_query.get_client_and_bucket",
                        lambda: (state["influx"], "monitoring-data"))
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


def test_influxdb_probe_calls_health(env, tmp_path):
    """InfluxDB 探测必须真调 health()（status=pass→up），而非构造+close 空转。"""
    _make_logs_db(tmp_path / "logs.db")
    resp = asyncio.run(sys_routes.get_system_status())
    assert _svc_map(resp)["influxdb"] == "up"
    fake = env["influx"]
    assert fake.health_calls == 1       # 调了 health()，不是只 close()
    assert fake.seen_timeout == (1_000, 3_000)  # 收紧超时(默认 30s 太长)：connect 1s/read 3s
    assert fake.closed


def test_influxdb_health_fail_is_down(env, tmp_path):
    """health().status != "pass"（挂了/网络失败）→ down，且不拖垮其余探测。"""
    _make_logs_db(tmp_path / "logs.db")
    env["influx"].status = "fail"
    resp = asyncio.run(sys_routes.get_system_status())
    m = _svc_map(resp)
    assert m["influxdb"] == "down"
    assert m["agent"] == "up" and m["backend"] == "up"
    assert env["influx"].health_calls == 1


def test_influxdb_down_isolated(env, tmp_path, monkeypatch):
    _make_logs_db(tmp_path / "logs.db")

    def _boom():
        raise RuntimeError("influx unreachable")

    monkeypatch.setattr("shared.data.influxdb_query.get_client_and_bucket", _boom)
    resp = asyncio.run(sys_routes.get_system_status())
    m = _svc_map(resp)
    assert m["influxdb"] == "down"
    assert m["agent"] == "up" and m["sqlite_logs"] == "up"  # 单探失败不拖垮别的


def test_llm_probe_reads_config_center(env, tmp_path):
    """llm 探测 URL 来自 get_param("llm_base_url")（配置中心链路），非裸 env。"""
    _make_logs_db(tmp_path / "logs.db")
    env["llm_base_url"] = "http://from-param.test/v1"
    resp = asyncio.run(sys_routes.get_system_status())
    assert _svc_map(resp)["llm"] == "up"
    assert "llm_base_url" in env["param_calls"]                 # 走了 get_param
    assert "http://from-param.test/v1/models" in env["get_urls"]  # URL 用它的值


def test_llm_probe_empty_url_down(env, tmp_path):
    _make_logs_db(tmp_path / "logs.db")
    env["llm_base_url"] = ""
    resp = asyncio.run(sys_routes.get_system_status())
    assert _svc_map(resp)["llm"] == "down"
    assert not any(u.endswith("/models") for u in env["get_urls"])  # 没发请求


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


def test_probes_run_in_parallel(env, tmp_path, monkeypatch):
    """冷缓存探测并行：两探用 barrier 对齐——串行会撞 barrier 超时。"""
    _make_logs_db(tmp_path / "logs.db")
    barrier = threading.Barrier(2, timeout=2.0)

    def wrap(orig):
        def probe():
            try:
                barrier.wait()  # 并行：两探同时到齐立即过；串行：2s 超时 broken
            except threading.BrokenBarrierError:
                pass
            return orig()
        return probe

    monkeypatch.setattr(sys_routes, "_probe_agent",
                        wrap(sys_routes._probe_agent))
    monkeypatch.setattr(sys_routes, "_probe_llm",
                        wrap(sys_routes._probe_llm))
    t0 = time.monotonic()
    resp = asyncio.run(sys_routes.get_system_status())
    elapsed = time.monotonic() - t0
    m = _svc_map(resp)
    assert m["agent"] == "up" and m["llm"] == "up"  # 包装不影响结果
    assert elapsed < 2.0  # 串行探测会 ≥2s（barrier 超时）

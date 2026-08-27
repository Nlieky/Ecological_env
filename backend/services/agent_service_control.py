# backend/services/agent_service_control.py
"""agent 服务(8642)生命周期：kill + detached 重启 + health 轮询。

Windows：DETACHED_PROCESS|CREATE_NEW_CONSOLE 开独立控制台窗口（日志可见），
venv python 跑 scripts/start_agent.py。绝不 kill backend 自身。
"""
import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_PORT = 8642
VENV_PY = PROJECT_ROOT / "ecological_env" / "Scripts" / "python.exe"


def _pids_by_port(port: int) -> list:
    try:
        import psutil
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == "LISTEN" and c.pid:
                return [c.pid]
    except ImportError:
        pass
    # netstat 兜底（psutil 未装）
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    return [int(l.split()[-1]) for l in out.splitlines()
            if f":{port}" in l and "LISTENING" in l]


def get_status() -> dict:
    try:
        import httpx
        r = httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=3)
        alive, detail = r.status_code == 200, r.json()
    except Exception as e:
        alive, detail = False, str(e)[:120]
    pids = _pids_by_port(AGENT_PORT)
    return {"alive": alive, "port": AGENT_PORT, "pids": pids, "detail": detail,
            "model": os.getenv("LLM_MODEL", "")}


def restart_agent(confirm: bool) -> dict:
    if not confirm:
        return {"ok": False, "error": "需 confirm=true 才执行重启"}
    old_pids = _pids_by_port(AGENT_PORT)
    for pid in old_pids:
        try:
            import psutil
            p = psutil.Process(pid)
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        except ImportError:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        except Exception:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(1)
    # detached 新进程：独立控制台窗口，继承当前 env（含 .env 变量）
    env = dict(os.environ)
    flags = 0
    if os.name == "nt":
        flags = 0x00000008 | 0x00000010  # DETACHED_PROCESS | CREATE_NEW_CONSOLE
    subprocess.Popen([str(VENV_PY), str(PROJECT_ROOT / "scripts" / "start_agent.py")],
                     cwd=str(PROJECT_ROOT), env=env, creationflags=flags)
    # 轮询 health 最多 60s（LLM 客户端初始化要几秒）
    for _ in range(60):
        time.sleep(1)
        try:
            import httpx
            if httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=2).status_code == 200:
                return {"ok": True, "old_pids": old_pids, "new_alive": True}
        except Exception:
            pass
    return {"ok": True, "old_pids": old_pids, "new_alive": False,
            "warn": "进程已启动但 60s 内 health 未就绪——请看 agent 控制台窗口日志"}

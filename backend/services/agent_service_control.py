# backend/services/agent_service_control.py
"""agent 服务(8642)生命周期：kill + detached 重启 + health 轮询。

Windows：CREATE_NO_WINDOW 在后台启动，不打开控制台窗口。venv
python 跑 scripts/start_agent.py。绝不 kill backend 自身。
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
    except Exception:
        pass  # psutil 未装 / Linux AccessDenied 等，一律走 netstat 兜底
    # netstat 兜底：分列解析，本地地址列（第2列，形如 0.0.0.0:8642 / [::]:8642）
    # 按最后一段精确匹配端口——防 18642 这类后缀包含式误杀；PID 在最后一列。
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        cols = line.split()
        if len(cols) < 5 or "LISTENING" not in line:
            continue
        addr = cols[1]  # Local Address
        if addr.rsplit(":", 1)[-1] == str(port):
            pid = cols[-1]
            if pid.isdigit():
                pids.append(int(pid))
    return list(dict.fromkeys(pids))  # IPv4/IPv6 同端口同 PID 去重


def get_status() -> dict:
    try:
        import httpx
        r = httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=3)
        alive, detail = r.status_code == 200, r.json()
    except Exception as e:
        alive, detail = False, str(e)[:120]
    pids = _pids_by_port(AGENT_PORT)
    from backend.services.agent_params import get_param
    ready = alive and isinstance(detail, dict) and detail.get("agent_initialized") is True
    saved_model = get_param("llm_model", env_key="LLM_MODEL", default="")
    return {"alive": alive, "port": AGENT_PORT, "pids": pids, "detail": detail,
            "ready": ready, "model": saved_model, "saved_model": saved_model}


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
        except Exception:
            # psutil 未装/进程已消失等：taskkill 兜底。单个 PID 失败不中断其余。
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(1)
    # 后台新进程，继承当前 env（含 .env 变量），不创建可见控制台。
    env = dict(os.environ)
    flags = 0
    if os.name == "nt":
        flags = 0x08000000  # CREATE_NO_WINDOW
    try:
        subprocess.Popen([str(VENV_PY), str(PROJECT_ROOT / "scripts" / "start_agent.py")],
                         cwd=str(PROJECT_ROOT), env=env, creationflags=flags)
    except OSError as exc:
        return {"ok": False, "error": f"启动 agent 进程失败: {exc}",
                "old_pids": old_pids}
    # 轮询 health 最多 60s（LLM 客户端初始化要几秒）
    new_alive = False
    for _ in range(60):
        time.sleep(1)
        try:
            import httpx
            response = httpx.get(f"http://localhost:{AGENT_PORT}/health", timeout=2)
            new_alive = response.status_code == 200
            if new_alive and response.json().get("agent_initialized") is True:
                return {"ok": True, "old_pids": old_pids, "new_alive": True, "new_ready": True}
        except Exception:
            new_alive = False
    return {"ok": False, "old_pids": old_pids, "new_alive": new_alive, "new_ready": False,
            "warn": "进程已启动但 60s 内智能体未就绪，请检查 agent 服务日志"}

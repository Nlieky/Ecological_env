"""Prometheus server 子进程托管。

把 Prometheus 二进制当作后端的子进程拉起，避免依赖项目外路径（如 D:\\prometheus...）。
后端启动时调用 :func:`start_prometheus`，它：

1. 若 ``PROMETHEUS_ENABLED != 1`` 则跳过。
2. 若 :9090 已有 Prometheus 在响应（health 200），跳过（不重复拉起/抢端口）。
3. 否则按优先级找二进制：``PROMETHEUS_BIN`` 环境变量 → 项目内 ``prometheus/prometheus.exe``
   → 旧的外部路径兜底；用 ``grafana/prometheus.yml``（抓 :8000）启动，TSDB 落在
   ``prometheus/prom_data``。

子进程为 daemon，随父进程退出而被回收。/metrics 端点本身不依赖此模块——即使
Prometheus 未拉起，后端仍照常暴露 :8000/metrics。
"""
import logging
import os
import socket
import subprocess
from pathlib import Path
from typing import Optional

import urllib.request

logger = logging.getLogger(__name__)

_proc: Optional[subprocess.Popen] = None
_REPO = Path(__file__).resolve().parents[2]


def _find_binary() -> Optional[Path]:
    candidates = []
    env_bin = os.getenv("PROMETHEUS_BIN")
    if env_bin:
        candidates.append(Path(env_bin))
    candidates.append(_REPO / "prometheus" / "prometheus.exe")
    # 旧外部路径兜底（迁移前）
    candidates.append(Path("D:/prometheus-3.10.0.windows-amd64/prometheus-3.10.0.windows-amd64/prometheus.exe"))
    for c in candidates:
        if c.exists():
            return c
    return None


def _port_in_use(port: int) -> bool:
    """先看端口是否监听，再看是不是 Prometheus（health 接口）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) != 0:
            return False
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/-/healthy", timeout=2) as r:
            return r.status == 200
    except Exception:
        # 端口被别的进程占着（非 prometheus），也视为"已占用"，不抢
        return True


def start_prometheus() -> None:
    global _proc
    if os.getenv("PROMETHEUS_ENABLED", "1") != "1":
        logger.info("prometheus auto-spawn disabled (PROMETHEUS_ENABLED!=1)")
        return
    if _proc and _proc.poll() is None:
        return  # 已在本进程拉起且活着

    port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    if _port_in_use(port):
        logger.info("port :%s already serving prometheus — skip spawn", port)
        return

    binary = _find_binary()
    if not binary:
        logger.warning(
            "prometheus binary not found (set PROMETHEUS_BIN or copy to prometheus/prometheus.exe); "
            "skip spawn. /metrics still exposed at :8000."
        )
        return

    cfg = _REPO / "grafana" / "prometheus.yml"
    tsdb = _REPO / "prometheus" / "prom_data"
    tsdb.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        f"--config.file={cfg}",
        f"--storage.tsdb.path={tsdb}",
        f"--web.listen-address=:{port}",
    ]
    try:
        _proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        logger.info("prometheus spawned (pid=%s) on :%s, config=%s", _proc.pid, port, cfg)
    except Exception as e:
        logger.warning("failed to spawn prometheus: %s", e)


def stop_prometheus() -> None:
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()
    _proc = None

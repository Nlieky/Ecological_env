#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anomaly-detection 子智能体 - 入口（确定性：直接跑 canonical 脚本）。

该子智能体的工作是确定性的（多算子异常检测），直接运行 canonical 脚本即可，不需要 LLM 会话。
早期版本起完整 AIAgent 会话，导致 ctgu-vlm 用 terminal/execute_code 瞎逛几十轮、上下文滚到数万
token，一轮研判十几分钟。改为直接跑脚本后秒级完成。本脚本只负责与主智能体的通信协议。
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = AGENT_DIR.parent.parent

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s - %(message)s',
                    stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

DEFAULT_SUBAGENT_NAME = "anomaly-detection"
RESULT_FILE_NAMES = {
    "anomaly-detection": "anomaly_result.json",
    "multi-dimensional-data-perception": "data_result.json",
    "rule-reasoning": "rule_reasoning_result.json",
    "disposition-execution": "disposition_result.json",
}
# 该子智能体的 canonical 脚本（确定性算子，不经 LLM）
CANONICAL_SCRIPT = AGENT_DIR / "skills" / "anomaly-detection-core" / "scripts" / "run_anomaly_detection_simple.py"
SCRIPT_TIMEOUT = 300


def load_task(session_dir):
    if not session_dir:
        return None
    task_file = Path(session_dir) / "task.json"
    if not task_file.exists():
        return None
    try:
        return json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[LOAD] task 解析失败: {e}")
        return None


def run_canonical_script(session_dir, subagent_name):
    """直接运行 canonical 脚本（不经 LLM 会话）。"""
    env = os.environ.copy()
    env["SESSION_DIR"] = session_dir or ""
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, str(CANONICAL_SCRIPT)]
    if subagent_name == "multi-dimensional-data-perception":
        cmd += ["--hours", "24"]
    elif session_dir:
        cmd += ["--session-dir", session_dir]
    logger.info(f"[RUN] {CANONICAL_SCRIPT.name} {' '.join(cmd[2:])}")
    try:
        r = subprocess.run(cmd, cwd=str(AGENT_DIR), env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=SCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error(f"[RUN] 脚本超时 ({SCRIPT_TIMEOUT}s)")
        return -1
    if r.returncode != 0:
        logger.error(f"[RUN] 脚本失败 exit={r.returncode} stderr={(r.stderr or '')[-400:]}")
    else:
        logger.info(f"[RUN] 脚本完成")
    return r.returncode


def main():
    session_dir = os.getenv("SESSION_DIR")
    subagent_name = os.getenv("SUBAGENT_NAME", DEFAULT_SUBAGENT_NAME)
    logger.info(f"[START] 子智能体={subagent_name} SESSION_DIR={session_dir}")

    task = load_task(session_dir)
    task_id = (task or {}).get("task_id", "unknown")

    rc = run_canonical_script(session_dir, subagent_name)

    result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
    result_file = Path(session_dir) / result_filename if session_dir else None
    if result_file and result_file.exists():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        except Exception as e:
            result = {"task_id": task_id, "status": "failed", "error": f"结果解析失败: {e}"}
    else:
        result = {"task_id": task_id, "status": "failed",
                  "error": f"脚本未产出 {result_filename} (exit={rc})"}

    result["task_id"] = task_id
    if result_file:
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[WRITE] {result_file}")
    return result


if __name__ == "__main__":
    _r = main()
    sys.exit(0 if (isinstance(_r, dict) and _r.get("status") != "failed") else 1)

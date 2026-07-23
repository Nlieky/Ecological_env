#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anomaly-detection 子智能体入口（LLM 驱动）。

设计：子智能体是独立 LLM 智能体——LLM 读自己的技能说明(SKILL.md)、据任务选择并调用
对应脚本，脚本（调 shared 算子/知识）干真正的数据处理，结果写回公共会话区。本脚本只
负责与主智能体的通信协议。

防瞎逛（早期 LLM 子智能体会 skill_view/terminal 乱翻几十轮）：SKILL.md 预加载进 prompt
（不用 skill_view 翻）+ 仅开 terminal 工具（无法 skill_view/memory 探索）+ 低迭代上限。
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

AGENT_DIR = Path(__file__).parent.resolve()
os.environ['HERMES_HOME'] = str(AGENT_DIR)
project_root = AGENT_DIR.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
try:
    from shared.framework.hermes_agent.run_agent import AIAgent
except ImportError as e:
    print(f"[ERROR] Failed to import Hermes AIAgent: {e}", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)], force=True)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
logger = logging.getLogger(__name__)

RESULT_FILE_NAMES = {
    "anomaly-detection": "anomaly_result.json",
    "multi-dimensional-data-perception": "data_result.json",
    "rule-reasoning": "rule_reasoning_result.json",
    "disposition-execution": "disposition_result.json",
}
DEFAULT_SUBAGENT_NAME = "anomaly-detection"


def load_task(session_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    if not session_dir:
        return None
    task_file = Path(session_dir) / "task.json"
    if not task_file.exists():
        return None
    try:
        return json.loads(task_file.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"[LOAD] task 解析失败: {e}")
        return None


def write_result(session_dir: str, result: Dict[str, Any], filename: str) -> bool:
    try:
        result_file = Path(session_dir).resolve() / filename
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[WRITE] 已写入结果: {result_file}")
        return True
    except Exception as e:
        logger.error(f"[WRITE] 写入结果失败: {e}")
        return False


def _preload_skill_md() -> str:
    for p in AGENT_DIR.glob("skills/*/SKILL.md"):
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            continue
    return ""


def _read_script_result(session_dir, result_filename):
    if not session_dir:
        return None
    session_path = Path(session_dir).resolve()
    candidates = [session_path / result_filename]
    try:
        candidates += list(session_path.glob("*_result.json"))
    except Exception:
        pass
    seen = set()
    for p in candidates:
        key = str(p)
        if key in seen or not p.exists():
            continue
        seen.add(key)
        try:
            loaded = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(loaded, dict) or loaded.get("status") == "failed":
            continue
        inner = loaded.get("result")
        if isinstance(inner, dict) or "data" in loaded or "statistics" in loaded:
            return loaded
    return None


def run_subagent() -> Dict[str, Any]:
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', DEFAULT_SUBAGENT_NAME)
    logger.info(f"[START] 子智能体={subagent_name} SESSION_DIR={session_dir}")

    task = load_task(session_dir)
    if not task:
        error_result = {"task_id": "unknown", "status": "failed",
                        "error": "Failed to load task", "timestamp": datetime.now().isoformat()}
        if session_dir:
            write_result(session_dir, error_result, RESULT_FILE_NAMES.get(subagent_name, "result.json"))
        return error_result
    task_id = task.get('task_id', 'unknown')

    skill_md = _preload_skill_md()
    user_message = (
        f"任务：{task.get('task', '')}\n\n"
        f"以下是你（{subagent_name} 子智能体）的技能说明，请严格按它执行：\n"
        f"---\n{skill_md}\n---\n\n"
        "执行要求：\n"
        "- 第一步就用 terminal 工具运行上述技能指定的脚本（如 `python skills/.../xxx.py`），"
        "不要 skills_list/skill_view/memory 等探索。\n"
        "- 脚本跑完、确认产出了结果文件即可停止，不要多做。"
    )

    try:
        llm_base_url = os.environ.get('LLM_BASE_URL') or os.environ.get('OPENAI_BASE_URL')
        llm_api_key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENAI_API_KEY')
        llm_model = os.environ.get('LLM_MODEL', 'LongCat-2.0')
        if not llm_api_key:
            raise ValueError("LLM_API_KEY 或 OPENAI_API_KEY 环境变量未设置")

        logger.info(f"[LLM] 开始处理任务: {task_id}")
        agent = AIAgent(
            base_url=llm_base_url, api_key=llm_api_key, model=llm_model,
            load_soul_identity=True, skip_context_files=False, skip_memory=False,
            enabled_toolsets=["terminal"], session_id=task_id, max_iterations=4,
        )
        response = agent.run_conversation(user_message)
        logger.info(f"[LLM] 任务完成")

        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
        result = _read_script_result(session_dir, result_filename)
        if result is None:
            result = response.get('final_response', response)
            logger.info(f"[LLM] 未找到脚本结构化结果，回退 final_response")
        else:
            logger.info(f"[LLM] 回传脚本结构化结果")

    except Exception as e:
        logger.error(f"[LLM] 执行失败: {e}", exc_info=True)
        result = {"task_id": task_id, "status": "failed", "error": str(e),
                  "timestamp": datetime.now().isoformat()}

    if session_dir:
        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
        if not isinstance(result, dict):
            result = {"task_id": task_id, "status": "completed", "result": result,
                      "timestamp": datetime.now().isoformat()}
        result["task_id"] = task_id
        write_result(session_dir, result, result_filename)
    return result


if __name__ == "__main__":
    _r = run_subagent()
    sys.exit(0 if (isinstance(_r, dict) and _r.get("status") != "failed") else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi-dimensional-data-perception 子智能体 - 统一入口点

原则：能由 LLM 做的就不要用硬编码脚本做。
此脚本只处理与主智能体的通信协议。

使用方式：
    由主智能体通过 subprocess 调用，环境变量设置：
    - HERMES_HOME: 子智能体目录
    - SESSION_DIR: 会话目录
    - SUBAGENT_NAME: 子智能体名称
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# === 步骤 1: 设置 HERMES_HOME ===
AGENT_DIR = Path(__file__).parent.resolve()
os.environ['HERMES_HOME'] = str(AGENT_DIR)

# === 步骤 2: 导入 Hermes AIAgent（与主智能体同款路径） ===
project_root = AGENT_DIR.parent.parent  # 项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from shared.framework.hermes_agent.run_agent import AIAgent
except ImportError as e:
    print(f"[ERROR] Failed to import Hermes AIAgent: {e}", file=sys.stderr)
    sys.exit(1)

# === 步骤 3: 配置日志 ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
logger = logging.getLogger(__name__)

# === 步骤 4: 定义结果文件名（与 call_subagent.py 一致） ===
RESULT_FILE_NAMES = {
    "anomaly-detection": "anomaly_result.json",
    "multi-dimensional-data-perception": "data_result.json",
    "rule-reasoning": "rule_result.json",
    "disposition-execution": "disposition_result.json"
}


def load_task(session_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    """从会话目录加载任务"""
    if not session_dir:
        logger.warning("[LOAD] SESSION_DIR 环境变量未设置")
        return None

    session_path = Path(session_dir).resolve()
    task_file = session_path / "task.json"
    if not task_file.exists():
        logger.error(f"[LOAD] 任务文件不存在: {task_file}")
        return None

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            task = json.load(f)
        logger.info(f"[LOAD] 已加载任务: {task.get('task_id', 'unknown')}")
        return task
    except Exception as e:
        logger.error(f"[LOAD] 加载任务失败: {e}")
        return None


def write_result(session_dir: str, result: Dict[str, Any], filename: str) -> bool:
    """将结果写入会话目录"""
    try:
        session_path = Path(session_dir).resolve()
        result_file = session_path / filename

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"[WRITE] 已写入结果: {result_file}")
        return True
    except Exception as e:
        logger.error(f"[WRITE] 写入结果失败: {e}")
        return False


def build_user_message(task: Dict[str, Any]) -> str:
    """构建用户消息"""
    task_description = task.get('task', '')
    context = task.get('context', {})

    if context:
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        return f"""任务：{task_description}

上下文信息：
```json
{context_str}
```

请处理此任务并返回结果。"""
    else:
        return task_description


def _read_script_result(session_dir, result_filename):
    """读取 skill 脚本在会话目录里写的结构化结果。

    SKILL.md 要求子智能体"只调用脚本、传递结果，不要生成报告"。脚本（如 get_data.py）
    会把结构化 dict 写到 *_result.json。本函数优先取 result_filename，兜底扫描会话目录
    其它 *_result.json。区分脚本结构化产物 vs LLM 文字报告的判据：顶层 result 是 dict、
    或顶层含 data/statistics 视为结构化；result 是 str 视为 LLM 文字报告（跳过）。
    返回 dict 或 None。
    """
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
    """子智能体主入口"""
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', 'multi-dimensional-data-perception')

    logger.info(f"[START] 启动子智能体: {subagent_name}")
    logger.info(f"[START] HERMES_HOME: {os.environ.get('HERMES_HOME')}")
    logger.info(f"[START] SESSION_DIR: {session_dir}")

    # 1. 读取任务
    task = load_task(session_dir)
    if not task:
        error_result = {
            "task_id": "unknown",
            "status": "failed",
            "error": "Failed to load task",
            "timestamp": datetime.now().isoformat()
        }
        if session_dir:
            result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
            write_result(session_dir, error_result, result_filename)
        return error_result

    task_id = task.get('task_id', 'unknown')

    # 2. 启动 AIAgent
    try:
        user_message = build_user_message(task)

        logger.info(f"[LLM] 开始处理任务: {task_id}")

        # 获取 LLM 配置
        llm_base_url = os.environ.get('LLM_BASE_URL') or os.environ.get('OPENAI_BASE_URL')
        llm_api_key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENAI_API_KEY')
        llm_model = os.environ.get('LLM_MODEL', 'LongCat-2.0')

        if not llm_api_key:
            raise ValueError("LLM_API_KEY 或 OPENAI_API_KEY 环境变量未设置")

        agent = AIAgent(
            base_url=llm_base_url,
            api_key=llm_api_key,
            model=llm_model,
            load_soul_identity=True,
            skip_context_files=False,
            skip_memory=False,
            enabled_toolsets=["skills", "terminal"],
            session_id=task_id,
            max_iterations=10
        )

        response = agent.run_conversation(user_message)
        logger.info(f"[LLM] 任务完成")

        # 优先回传 skill 脚本写的结构化结果（SKILL.md：只调用脚本、传递结果，不要生成报告）。
        # 找不到结构化产物时才回退到 LLM 的 final_response（文字）。
        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
        result = _read_script_result(session_dir, result_filename)
        if result is None:
            result = response.get('final_response', response)
            logger.info(f"[LLM] 未找到脚本结构化结果，回退 final_response")
        else:
            logger.info(f"[LLM] 回传脚本结构化结果")

    except Exception as e:
        logger.error(f"[LLM] 执行失败: {e}", exc_info=True)
        result = {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

    # 3. 写入结果
    if session_dir:
        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")

        # 如果结果不是 dict，包装一下
        if not isinstance(result, dict):
            result = {
                "task_id": task_id,
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

        # 强制对齐 task_id：脚本/子智能体自带的 task_id 可能与 call_subagent 写入 task.json 的
        # 不一致（格式/生成方式不同）→ call_subagent 的防串台校验会报 "Task ID mismatch"。
        result["task_id"] = task_id

        write_result(session_dir, result, result_filename)

    return result


if __name__ == "__main__":
    result = run_subagent()

    # 返回适当的退出码
    if isinstance(result, dict) and result.get("status") == "failed":
        sys.exit(1)
    else:
        sys.exit(0)

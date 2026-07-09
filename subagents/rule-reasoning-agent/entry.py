#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则推理子智能体 - 统一入口点

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

# === 步骤 2: 导入 Hermes AIAgent ===
# 从本地化框架导入
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


def run_subagent() -> Dict[str, Any]:
    """子智能体主入口"""
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', 'rule-reasoning')

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
        result = response.get('final_response', response)

        logger.info(f"[LLM] 任务完成")

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

        # 确保 task_id 存在
        if "task_id" not in result:
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

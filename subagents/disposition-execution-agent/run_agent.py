#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研判预警与处置执行子智能体 - 简化入口

原则：能由 LLM 做的就不要用硬编码脚本做。

此脚本只处理与主智能体的通信协议（无法由 LLM 做）：
- 读取任务文件 (task.json)
- 写入结果文件 (result.json)

其他所有逻辑由 LLM 通过技能系统处理。

注意：hermes-agent 已安装在虚拟环境中，无需额外路径配置
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 设置 HERMES_HOME 指向子智能体目录
AGENT_DIR = Path(__file__).parent.resolve()
os.environ['HERMES_HOME'] = str(AGENT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # 覆盖任何之前的配置
)
# 确保 stdout 使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
logger = logging.getLogger(__name__)


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


def write_result(session_dir: str, result: Any, filename: str = "llm_result.json") -> bool:
    """将结果写入会话目录"""
    try:
        session_path = Path(session_dir).resolve()
        result_file = session_path / filename

        if isinstance(result, str):
            output = {
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            output = result

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

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
    subagent_name = os.getenv('SUBAGENT_NAME', 'disposition-execution')

    logger.info(f"[START] 启动子智能体: {subagent_name}")
    logger.info(f"[START] HERMES_HOME: {os.environ.get('HERMES_HOME')}")
    logger.info(f"[START] SESSION_DIR: {session_dir}")

    # 1. 读取任务
    task = load_task(session_dir)
    if not task:
        error_result = {
            "status": "failed",
            "error": "Failed to load task",
            "timestamp": datetime.now().isoformat()
        }
        if session_dir:
            write_result(session_dir, error_result)
        return error_result

    task_id = task.get('task_id', 'unknown')

    # 2. 启动 AIAgent
    try:
        from run_agent import AIAgent

        user_message = build_user_message(task)

        logger.info(f"[LLM] 开始处理任务: {task_id}")

        agent = AIAgent(
            base_url=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL", "LongCat-2.0"),
            load_soul_identity=True,
            skip_context_files=False,
            skip_memory=False,
            enabled_toolsets=["skills", "terminal"],
            session_id=task_id,
            max_iterations=3
        )

        response = agent.run_conversation(user_message)
        result = response.get('final_response', response)

        logger.info(f"[LLM] 任务完成")

    except Exception as e:
        logger.error(f"[LLM] 执行失败: {e}", exc_info=True)
        result = {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

    # 3. 写入结果 - 优先使用脚本输出文件
    if session_dir:
        # 检查是否有脚本输出文件
        script_output_file = Path(session_dir) / "disposition_result.json"
        if script_output_file.exists():
            try:
                with open(script_output_file, 'r', encoding='utf-8') as f:
                    script_result = json.load(f)
                # 使用脚本输出，但添加任务 ID
                if isinstance(script_result, dict):
                    script_result["task_id"] = task_id
                logger.info(f"[WRITE] 使用脚本输出文件: {script_output_file}")
                # 写入 result.json 作为最终结果
                write_result(session_dir, script_result, "result.json")
                return script_result
            except Exception as e:
                logger.warning(f"[WRITE] 无法读取脚本输出文件: {e}，使用 LLM 输出")

        # 只有脚本输出不存在时才写入 LLM 输出
        write_result(session_dir, result, "llm_result.json")

    return result if isinstance(result, dict) else {"result": result}


if __name__ == "__main__":
    if not os.environ.get("SUBAGENT_NAME"):
        os.environ["SUBAGENT_NAME"] = "disposition-execution"

    result = run_subagent()

    if isinstance(result, dict) and result.get("status") == "failed":
        sys.exit(1)
    else:
        sys.exit(0)

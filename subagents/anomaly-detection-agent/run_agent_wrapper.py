#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子智能体运行包装器 - 连接 Hermes 框架和子智能体实现

这个包装器负责：
1. 读取 SESSION_DIR 中的 task.json
2. 创建子智能体的 AIAgent 实例（LLM 驱动）
3. 让 AIAgent 处理任务并返回结果
4. 将结果写入 result.json
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_identity_files(agent_dir: Path) -> Dict[str, str]:
    """
    加载子智能体的身份文件

    Args:
        agent_dir: 子智能体目录

    Returns:
        身份文件内容字典
    """
    identity_files = {}

    # 定义要加载的身份文件
    files_to_load = [
        ('IDENTITY.md', 'identity'),
        ('SOUL.md', 'soul'),
        ('AGENTS.md', 'agents'),
        ('MEMORY.md', 'memory'),
        ('TOOLS.md', 'tools')
    ]

    for filename, key in files_to_load:
        file_path = agent_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    identity_files[key] = f.read()
                logger.info(f"[IDENTITY] 已加载: {filename}")
            except Exception as e:
                logger.warning(f"[IDENTITY] 加载 {filename} 失败: {e}")
        else:
            logger.debug(f"[IDENTITY] 文件不存在: {filename}")

    return identity_files


def load_task(session_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    从会话目录加载任务

    Args:
        session_dir: 会话目录路径

    Returns:
        任务对象，如果失败返回 None
    """
    if not session_dir:
        logger.error("[TASK] SESSION_DIR 环境变量未设置")
        return None

    # 转换为绝对路径（相对于项目根目录）
    session_path = Path(session_dir).resolve()
    task_file = session_path / "task.json"
    if not task_file.exists():
        logger.error(f"[TASK] task.json 不存在: {task_file}")
        return None

    try:
        with open(task_file, 'r', encoding='utf-8') as f:
            task = json.load(f)
        logger.info(f"[TASK] 已加载任务: {task.get('task_id', 'unknown')}")
        return task
    except Exception as e:
        logger.error(f"[TASK] 加载 task.json 失败: {e}")
        return None


def write_result(session_dir: str, result: Dict[str, Any], result_filename: str = "result.json") -> bool:
    """
    将结果写入会话目录

    Args:
        session_dir: 会话目录路径
        result: 结果对象
        result_filename: 结果文件名

    Returns:
        是否成功写入
    """
    try:
        # 转换为绝对路径（相对于项目根目录）
        session_path = Path(session_dir).resolve()
        result_file = session_path / result_filename
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[RESULT] 结果已写入: {result_file}")
        return True
    except Exception as e:
        logger.error(f"[RESULT] 写入结果失败: {e}")
        return False


def run_hermes_agent() -> Dict[str, Any]:
    """
    运行 Hermes 智能体（使用 AIAgent，真正的 LLM 驱动）

    这是子智能体的主入口点，负责：
    1. 获取环境变量
    2. 读取任务
    3. 创建 AIAgent 实例并加载身份文件
    4. 让 AIAgent 处理任务
    5. 写入结果

    Returns:
        执行结果
    """
    # 获取环境变量
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', 'unknown')
    hermes_home = os.getenv('HERMES_HOME')

    logger.info("=" * 60)
    logger.info(f"[HERMES_AGENT] 启动子智能体: {subagent_name}")
    logger.info(f"[HERMES_AGENT] SESSION_DIR: {session_dir}")
    logger.info(f"[HERMES_AGENT] HERMES_HOME: {hermes_home}")
    logger.info("=" * 60)

    # 获取子智能体目录
    if hermes_home:
        agent_dir = Path(hermes_home)
    else:
        # 回退到当前目录
        agent_dir = Path(__file__).parent

    logger.info(f"[HERMES_AGENT] 子智能体目录: {agent_dir}")

    # 读取任务
    task = load_task(session_dir)
    if not task:
        return {
            "status": "failed",
            "error": "Failed to load task",
            "task_id": "unknown",
            "timestamp": datetime.now().isoformat()
        }

    task_id = task.get('task_id', 'unknown')
    task_description = task.get('task', '')
    context = task.get('context', {})

    logger.info(f"[HERMES_AGENT] 任务描述: {task_description}")

    # 使用 AIAgent 处理任务
    try:
        result = execute_with_aiagent(
            agent_dir=agent_dir,
            task_description=task_description,
            context=context,
            task_id=task_id,
            subagent_name=subagent_name
        )

        # 确定结果文件名
        result_filenames = {
            "anomaly-detection": "anomaly_result.json",
            "multi-dimensional-data-perception": "data_result.json",
            "rule-reasoning": "rule_result.json",
            "disposition-execution": "disposition_result.json",
            "data-perception": "data_result.json",
            "anomaly": "anomaly_result.json",
            "rule": "rule_result.json",
            "disposition": "disposition_result.json"
        }

        result_filename = result_filenames.get(subagent_name, "result.json")

        # 写入结果
        if session_dir:
            write_result(session_dir, result, result_filename)

        return result

    except Exception as e:
        logger.error(f"[HERMES_AGENT] 执行失败: {e}")
        import traceback
        traceback.print_exc()

        error_result = {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

        if session_dir:
            result_filename = result_filenames.get(subagent_name, "result.json")
            write_result(session_dir, error_result, result_filename)

        return error_result


def execute_with_aiagent(
    agent_dir: Path,
    task_description: str,
    context: Dict[str, Any],
    task_id: str,
    subagent_name: str
) -> Dict[str, Any]:
    """
    使用 AIAgent 执行任务（真正的 LLM 驱动）

    Args:
        agent_dir: 子智能体目录（HERMES_HOME）
        task_description: 任务描述
        context: 上下文信息
        task_id: 任务ID
        subagent_name: 子智能体名称

    Returns:
        执行结果
    """
    # 导入 AIAgent（hermes-agent 已安装在虚拟环境中）
    try:
        from run_agent import AIAgent
    except ImportError as e:
        raise ImportError(
            f"无法导入 run_agent：{e}\n"
            "请确保 hermes-agent 已安装在虚拟环境中：pip install hermes-agent"
        )

    # 获取 LLM 配置
    # 尝试从多个环境变量中获取
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("LLM_BASE_URL", "http://172.16.12.41:30000/v1")
    model = os.environ.get("LLM_MODEL", "ctgu-vlm")
    provider = os.environ.get("LLM_PROVIDER", "custom")
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")

    logger.info(f"[AIAgent] 配置参数:")
    logger.info(f"[AIAgent]   base_url: {base_url}")
    logger.info(f"[AIAgent]   model: {model}")
    logger.info(f"[AIAgent]   provider: {provider}")
    logger.info(f"[AIAgent]   api_key: {api_key[:20]}...")

    # 设置临时 HERMES_HOME 指向子智能体目录
    original_hermes_home = os.environ.get('HERMES_HOME')
    os.environ['HERMES_HOME'] = str(agent_dir)

    try:
        logger.info(f"[AIAgent] 创建 AIAgent 实例")
        logger.info(f"[AIAgent] HERMES_HOME: {agent_dir}")
        logger.info(f"[AIAgent] 检查 SOUL.md: {(agent_dir / 'SOUL.md').exists()}")

        # 创建 AIAgent 实例
        # AIAgent 会自动加载 HERMES_HOME/SOUL.md 和其他身份文件
        agent = AIAgent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            provider=provider,
            load_soul_identity=True,      # 加载 SOUL.md
            skip_context_files=False,     # 加载其他身份文件（AGENTS.md, MEMORY.md 等）
            enabled_toolsets=["skills"],  # 启用 skills toolset，让子智能体可以调用自己的 skill
            max_iterations=10,            # 允许足够的迭代来调用 skill
            quiet_mode=False,
            session_id=task_id
        )

        # 构建给 AIAgent 的消息
        # 包含任务描述和上下文
        message_parts = [f"任务：{task_description}"]

        if context:
            context_json = json.dumps(context, ensure_ascii=False, indent=2)
            message_parts.append(f"\n前置结果：\n```json\n{context_json}\n```")

        # 添加输出格式要求
        message_parts.append("""
请以 JSON 格式返回分析结果，必须包含：
- task_id: 任务ID
- status: "completed" 或 "failed"
- result: 分析结果
- metadata: 包含 subagent 和 timestamp
""")

        user_message = "\n".join(message_parts)

        logger.info(f"[AIAgent] 调用 AIAgent.run_conversation()")
        logger.info(f"[AIAgent] 消息长度: {len(user_message)} 字符")

        # 调用 AIAgent
        response = agent.run_conversation(
            user_message=user_message,
            conversation_history=None
        )

        logger.info(f"[AIAgent] AIAgent 响应类型: {type(response)}")
        logger.info(f"[AIAgent] 响应内容长度: {len(str(response))} 字符")

        # 解析响应
        result = parse_aiagent_response(response, task_id, subagent_name)

        return result

    finally:
        # 恢复原始 HERMES_HOME
        if original_hermes_home:
            os.environ['HERMES_HOME'] = original_hermes_home
        elif 'HERMES_HOME' in os.environ:
            del os.environ['HERMES_HOME']


def parse_aiagent_response(response: Any, task_id: str, subagent_name: str) -> Dict[str, Any]:
    """
    解析 AIAgent 的响应

    Args:
        response: AIAgent 返回的响应
        task_id: 任务ID
        subagent_name: 子智能体名称

    Returns:
        标准化的结果字典
    """
    # AIAgent 可能返回字符串或字典
    response_text = str(response) if response else ""

    # 尝试解析为 JSON
    import re
    try:
        # 直接尝试解析
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取花括号内容
    brace_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # 如果无法解析为 JSON，构建一个包含原始响应的结果
    logger.warning(f"[AIAgent] 无法解析响应为 JSON，返回包含原始响应的结果")
    return {
        "task_id": task_id,
        "status": "completed",
        "result": {
            "raw_response": response_text,
            "message": "无法解析为结构化结果，请查看 raw_response"
        },
        "metadata": {
            "subagent": subagent_name,
            "timestamp": datetime.now().isoformat(),
            "parse_error": True
        }
    }


# 保留旧的 execute 函数用于向后兼容
def execute_subagent_task(
    subagent_name: str,
    agent_dir: Path,
    task: Dict[str, Any],
    identity: Dict[str, str]
) -> Dict[str, Any]:
    """
    执行子智能体任务（兼容接口）

    Args:
        subagent_name: 子智能体名称
        agent_dir: 子智能体目录
        task: 任务对象
        identity: 身份文件内容

    Returns:
        执行结果
    """
    task_id = task.get('task_id', 'unknown')
    task_description = task.get('task', '')
    context = task.get('context', {})

    return execute_with_aiagent(
        agent_dir=agent_dir,
        task_description=task_description,
        context=context,
        task_id=task_id,
        subagent_name=subagent_name
    )


if __name__ == "__main__":
    # 测试模式
    import tempfile

    # 创建临时会话目录
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['SESSION_DIR'] = temp_dir
        os.environ['SUBAGENT_NAME'] = 'anomaly-detection'
        os.environ['HERMES_HOME'] = str(Path(__file__).parent.resolve())

        # 创建测试任务
        test_task = {
            "task_id": "test_001",
            "task": "检测最近24小时的异常",
            "context": {}
        }

        test_task_file = Path(temp_dir) / "task.json"
        with open(test_task_file, 'w') as f:
            json.dump(test_task, f)

        # 运行测试
        result = run_hermes_agent()
        print(json.dumps(result, indent=2, ensure_ascii=False))

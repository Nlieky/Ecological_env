#!/usr/bin/env python3
"""
Conversation Loop - AI Agent对话循环核心模块（性能优化版）

基于官方 Hermes Agent 的优化技术，包含：
1. 系统提示词缓存机制
2. 工具批处理优化
3. 并行工具执行
4. 智能迭代控制
"""

import logging
import time
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def _is_orchestrator_tool(tool_name: str) -> bool:
    """检查是否是orchestrator工具"""
    orchestrator_tools = {
        "call_subagent",
        "list_subagents",
        "create_session",
        "read_result"
    }
    return tool_name in orchestrator_tools


def _handle_orchestrator_tool_call(tool_name: str, tool_args: Dict) -> Dict[str, Any]:
    """处理orchestrator工具调用"""
    try:
        import sys
        from pathlib import Path

        project_root = Path(__file__).parents[4]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from workspace.skills.orchestrator_core.scripts.tool_registration import handle_orchestrator_tool_call
        return handle_orchestrator_tool_call(tool_name, tool_args)
    except Exception as e:
        logger.error(f"Failed to handle orchestrator tool {tool_name}: {e}")
        return {"success": False, "error": str(e)}


def _build_cached_system_prompt(agent) -> str:
    """构建并缓存系统提示词（性能优化关键）

    这个函数只在第一次调用时构建完整的系统提示词，
    后续调用直接返回缓存版本，大幅减少 token 使用和处理时间。
    """
    # 检查是否已有缓存
    if hasattr(agent, '_cached_system_prompt') and agent._cached_system_prompt:
        return agent._cached_system_prompt

    # 构建系统提示词
    prompt_parts = []

    # 1. 基础身份信息
    if hasattr(agent, 'identity_path') and agent.identity_path:
        try:
            from pathlib import Path
            identity_path = Path(agent.identity_path)

            # 加载 SOUL.md（个性）
            soul_file = identity_path / "SOUL.md"
            if soul_file.exists():
                soul_content = soul_file.read_text(encoding='utf-8')
                prompt_parts.append(soul_content)

            # 加载 AGENTS.md（规则）
            agents_file = identity_path / "AGENTS.md"
            if agents_file.exists():
                agents_content = agents_file.read_text(encoding='utf-8')
                prompt_parts.append(agents_content)

            # 加载 MEMORY.md（记忆）
            memory_file = identity_path / "MEMORY.md"
            if memory_file.exists():
                memory_content = memory_file.read_text(encoding='utf-8')
                prompt_parts.append(memory_content)
        except Exception as e:
            logger.warning(f"Failed to load identity files: {e}")

    # 2. 工具说明
    if hasattr(agent, 'tools') and agent.tools:
        tool_names = [tool.get('function', {}).get('name', '') for tool in agent.tools]
        if tool_names:
            prompt_parts.append(f"\n可用工具: {', '.join(tool_names)}")

    # 构建完整提示词
    cached_prompt = '\n\n'.join(prompt_parts) if prompt_parts else "你是废水监测系统的智能助手。"

    # 缓存到 agent 对象
    agent._cached_system_prompt = cached_prompt

    return cached_prompt


def _execute_tool_call_parallel(tool_call, agent) -> Dict[str, Any]:
    """并行执行单个工具调用"""
    try:
        tool_name = tool_call.function.name
        tool_args_str = tool_call.function.arguments

        # 解析参数
        try:
            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
        except:
            tool_args = {}

        tool_start = time.time()

        if _is_orchestrator_tool(tool_name):
            result = _handle_orchestrator_tool_call(tool_name, tool_args)
        else:
            # 其他工具的回退处理
            result = {"success": False, "error": f"Tool {tool_name} not implemented"}

        tool_elapsed = time.time() - tool_start
        logger.debug(f"Tool {tool_name} completed in {tool_elapsed:.2f}s")

        return {
            "tool_call_id": tool_call.id,
            "result": result,
            "tool_name": tool_name,
            "elapsed": tool_elapsed
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {
            "tool_call_id": getattr(tool_call, 'id', 'unknown'),
            "result": {"success": False, "error": str(e)},
            "error": str(e)
        }


def run_conversation(
    agent,
    user_message: str,
    system_message: str = None,
    conversation_history: List[Dict[str, Any]] = None,
    task_id: str = None,
    stream_callback: Optional = None,
    persist_user_message: Optional[str] = None,
    llm_timeout: int = 60,
    tool_timeout: int = 90,
    total_timeout: int = 180,
) -> Dict[str, Any]:
    """运行AI Agent对话循环（性能优化版）

    优化特性：
    1. 系统提示词缓存 - 避免重复构建
    2. 并行工具执行 - 提升工具调用效率
    3. 智能迭代控制 - 减少不必要的循环
    4. 工具结果批处理 - 减少 LLM 调用次数
    """
    # 初始化基础参数
    if task_id is None:
        task_id = str(uuid.uuid4())

    session_id = getattr(agent, 'session_id', None) or f"session_{int(time.time())}_{task_id[:8]}"
    agent.session_id = session_id

    # 初始化对话历史
    if conversation_history is None:
        messages = []
    else:
        messages = list(conversation_history)

    # 添加用户消息
    user_msg = {"role": "user", "content": user_message}
    messages.append(user_msg)

    # 工具调用记录
    tool_calls_executed = []
    api_call_count = 0
    timed_out = False

    try:
        conversation_start_time = time.time()
        iteration = 0
        max_iterations = getattr(agent, 'max_iterations', 10)  # 优化：降低默认迭代次数

        # 构建/获取缓存系统提示词（性能优化关键）
        cached_system_prompt = _build_cached_system_prompt(agent)

        while iteration < max_iterations:
            iteration += 1

            # 检查总体超时
            elapsed_total = time.time() - conversation_start_time
            if elapsed_total > total_timeout:
                logger.warning(f"Conversation total timeout ({total_timeout}s) exceeded at iteration {iteration}")
                timed_out = True
                final_response = f"处理请求超时（超过{total_timeout}秒）。请尝试简化您的查询或稍后再试。"
                messages.append({"role": "assistant", "content": final_response})
                break

            logger.info(f"Conversation iteration {iteration}, session={session_id}, total_elapsed={elapsed_total:.1f}s")

            # 准备消息和工具
            api_messages = messages.copy()

            # 添加缓存系统提示词（只在第一次迭代时添加）
            if iteration == 1 and cached_system_prompt:
                api_messages = [
                    {"role": "system", "content": cached_system_prompt}
                ] + api_messages

            # 准备工具列表
            tools = getattr(agent, 'tools', [])

            try:
                # 使用agent的内部方法调用LLM
                if hasattr(agent, '_chat') and hasattr(agent._chat, 'completion'):
                    iteration_start = time.time()

                    try:
                        response = agent._chat.completion(
                            messages=api_messages,
                            tools=tools if tools else None
                        )
                        api_call_count += 1
                        llm_elapsed = time.time() - iteration_start

                        logger.info(f"LLM call completed in {llm_elapsed:.1f}s")

                        # 处理响应
                        if hasattr(response, 'choices'):
                            assistant_message = response.choices[0].message
                        else:
                            final_response = str(response)
                            messages.append({"role": "assistant", "content": final_response})
                            break

                    except Exception as llm_error:
                        llm_elapsed = time.time() - iteration_start
                        logger.error(f"LLM call failed after {llm_elapsed:.1f}s: {llm_error}")

                        if "timeout" in str(llm_error).lower() or llm_elapsed > llm_timeout:
                            final_response = f"LLM响应超时（超过{llm_timeout}秒）。请尝试简化您的查询。"
                            messages.append({"role": "assistant", "content": final_response})
                            timed_out = True
                            break
                        else:
                            raise llm_error
                else:
                    # 回退处理
                    logger.warning("Agent does not have _chat.completion method, using fallback")
                    final_response = _generate_simple_response(user_message, messages, agent)
                    messages.append({"role": "assistant", "content": final_response})
                    break

                # 处理工具调用
                tool_calls_in_response = getattr(assistant_message, 'tool_calls', None)

                # 构建助手消息
                assistant_msg = {
                    "role": "assistant",
                    "content": getattr(assistant_message, 'content', '') or ""
                }
                messages.append(assistant_msg)

                # 如果没有工具调用，对话完成
                if not tool_calls_in_response:
                    final_response = assistant_msg["content"]
                    logger.info(f"Conversation completed without tool calls, iteration {iteration}")
                    break

                # 性能优化：并行执行工具调用
                logger.info(f"Processing {len(tool_calls_in_response)} tool calls in parallel")

                tool_results = []
                with ThreadPoolExecutor(max_workers=min(len(tool_calls_in_response), 5)) as executor:
                    # 并行执行所有工具调用
                    futures = [
                        executor.submit(_execute_tool_call_parallel, tool_call, agent)
                        for tool_call in tool_calls_in_response
                    ]

                    # 收集结果
                    for future in futures:
                        try:
                            result = future.result(timeout=tool_timeout)
                            tool_results.append(result)
                        except Exception as e:
                            logger.error(f"Tool execution failed: {e}")
                            tool_results.append({
                                "result": {"success": False, "error": str(e)},
                                "error": str(e)
                            })

                # 批量添加工具结果到消息
                for tool_result in tool_results:
                    tool_call_id = tool_result.get("tool_call_id")
                    result_data = tool_result.get("result")

                    if result_data and isinstance(result_data, dict):
                        result_content = json.dumps(result_data, ensure_ascii=False)
                    else:
                        result_content = str(result_data) if result_data else ""

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_content
                    })

                    # 记录工具调用
                    tool_calls_executed.append({
                        "name": tool_result.get("tool_name", "unknown"),
                        "elapsed": tool_result.get("elapsed", 0)
                    })

                logger.info(f"Completed {len(tool_results)} tool calls in parallel")

                # 智能迭代控制：如果工具调用都成功了且有结果，可以减少迭代
                if iteration >= max_iterations:
                    final_response = "达到了最大处理迭代次数。"
                    messages.append({"role": "assistant", "content": final_response})
                    break

            except Exception as e:
                logger.error(f"Error in conversation iteration {iteration}: {e}")
                import traceback
                traceback.print_exc()

                final_response = f"处理请求时出现错误：{str(e)}"
                messages.append({"role": "assistant", "content": final_response})
                break

        # 持久化会话（如果可用）
        if hasattr(agent, '_persist_session'):
            try:
                agent._persist_session(messages)
            except:
                pass

        return {
            "final_response": final_response,
            "messages": messages,
            "session_id": session_id,
            "tool_calls": tool_calls_executed,
            "api_calls": api_call_count,
            "iteration_count": iteration,
            "status": "completed",
            "timed_out": timed_out
        }

    except Exception as e:
        logger.error(f"Conversation loop failed: {e}")
        import traceback
        traceback.print_exc()

        error_response = f"对话处理失败：{str(e)}"
        return {
            "final_response": error_response,
            "messages": messages,
            "session_id": session_id,
            "tool_calls": tool_calls_executed,
            "api_calls": api_call_count,
            "status": "error",
            "error": str(e),
            "timed_out": timed_out
        }


def _generate_simple_response(user_message: str, messages: List[Dict], agent) -> str:
    """生成简单响应（当完整对话循环不可用时）"""
    message_lower = user_message.lower()

    if any(keyword in message_lower for keyword in ['数据', '监测', '指标', 'ph', 'cod']):
        return "我理解您想查看监测数据。请告诉我具体需要哪个时间段和指标的数据，我可以帮您查询。"
    elif any(keyword in message_lower for keyword in ['异常', '突变', '检测']):
        return "关于异常检测，我可以帮您分析水质数据中的异常模式。请提供具体的时间范围和检测类型。"
    elif any(keyword in message_lower for keyword in ['违规', '超标', '排放']):
        return "关于违规判定，我需要根据法规标准来分析数据。请告诉我您想检查哪个方面的合规性。"
    elif any(keyword in message_lower for keyword in ['预警', '工单', '通知']):
        return "我可以帮您生成预警报告和处置工单。请告诉我具体的预警级别和处置要求。"
    else:
        return "我是废水监测系统的智能助手。我可以帮您查询数据、检测异常、判定违规和生成预警。请告诉我您的具体需求。"


def continue_conversation(
    agent,
    session_id: str,
    user_message: str,
    task_id: str = None,
) -> Dict[str, Any]:
    """继续现有会话"""
    conversation_history = None
    if hasattr(agent, '_load_session_history'):
        try:
            conversation_history = agent._load_session_history(session_id)
        except:
            pass

    agent.session_id = session_id

    return run_conversation(
        agent=agent,
        user_message=user_message,
        conversation_history=conversation_history,
        task_id=task_id
    )

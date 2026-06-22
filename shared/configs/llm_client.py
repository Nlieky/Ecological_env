#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端模块 - 废水虚假排放智能监测系统

提供统一的LLM API接口，主智能体和子智能体共享使用。

支持 OpenAI 兼容的 API 格式（如本地部署的 ctgu-vlm 模型）

配置加载：
- 敏感信息（API密钥）从项目根目录 .env 加载
- 非敏感配置从 shared/configs/llm_config.yaml 加载

使用方式：
    from shared.configs.llm_client import get_llm_client

    client = get_llm_client()
    response = client.chat("你好", model_type="primary")
"""

import os
import yaml
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    import warnings
    warnings.warn("OpenAI SDK not installed. Install with: pip install openai")

# 导入错误类
from shared.configs.llm_errors import (
    LLMError, LLMTimeoutError, LLMQuotaError,
    LLMServiceError, LLMConfigError, LLMContentError
)

# Prometheus 指标（可选，如果 prometheus_client 不可用则跳过）
try:
    from prometheus_client import Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None

# 定义 Prometheus 指标
if PROMETHEUS_AVAILABLE:
    llm_requests_total = Counter(
        'llm_requests_total',
        'LLM 请求总数',
        ['model_type', 'status']
    )

    llm_request_duration = Histogram(
        'llm_request_duration_seconds',
        'LLM 请求耗时',
        ['model_type']
    )

    llm_tokens_total = Counter(
        'llm_tokens_total',
        'LLM Token 使用总数',
        ['model_type', 'token_type']  # token_type: input/output/completion
    )
else:
    llm_requests_total = None
    llm_request_duration = None
    llm_tokens_total = None

# 不配置logging，由主应用统一配置
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置"""
    # 模型配置
    primary_model: str = "ctgu-vlm"
    fast_model: str = "ctgu-vlm"
    analysis_model: str = "ctgu-vlm"

    # 模型参数
    max_tokens: int = 4096
    temperature: float = 0.7

    # API配置
    api_key: str = ""
    base_url: str = "http://172.16.12.41:30000/v1"

    # 性能配置
    timeout: int = 120
    max_retries: int = 3

    # 提示词
    system_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "primary_model": self.primary_model,
            "fast_model": self.fast_model,
            "analysis_model": self.analysis_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key": "***" if self.api_key else "",
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }


class LLMClient:
    """LLM客户端（OpenAI 兼容格式）"""

    def __init__(self, config: LLMConfig):
        """
        初始化LLM客户端

        Args:
            config: LLM配置
        """
        self.config = config

        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK not installed")

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )

        print(f"[LLM_CLIENT] Initialized with model: {config.primary_model}")
        print(f"[LLM_CLIENT] Base URL: {config.base_url}")

    def chat(
        self,
        message: str,
        model_type: str = "primary",
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        发送聊天请求（带重试和错误分类）

        Args:
            message: 用户消息
            model_type: 模型类型（primary/fast/analysis）
            system_prompt: 系统提示词（覆盖配置）
            max_tokens: 最大token数（覆盖配置）
            temperature: 温度参数（覆盖配置）
            **kwargs: 其他参数

        Returns:
            str: LLM响应

        Raises:
            LLMTimeoutError: LLM响应超时
            LLMQuotaError: API调用频率超限
            LLMServiceError: LLM服务不可用
            LLMConfigError: API配置错误
            LLMContentError: 响应格式错误
            LLMError: 其他LLM错误
        """
        # 选择模型
        model_map = {
            "primary": self.config.primary_model,
            "fast": self.config.fast_model,
            "analysis": self.config.analysis_model
        }
        model = model_map.get(model_type, self.config.primary_model)

        # 使用配置的系统提示词，除非提供覆盖
        if system_prompt is None:
            system_prompt = self.config.system_prompt

        # 使用配置的参数，除非提供覆盖
        if max_tokens is None:
            max_tokens = self.config.max_tokens
        if temperature is None:
            temperature = self.config.temperature

        # 构建消息列表
        messages = [{"role": "user", "content": message}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # 记录开始时间
        start_time = time.time()

        # 重试循环
        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    **kwargs
                )

                # 检查响应内容
                if not response.choices or len(response.choices) == 0:
                    logger.warning(f"[LLM] Empty response from model: {model}")
                    if PROMETHEUS_AVAILABLE and llm_requests_total:
                        llm_requests_total.labels(model_type=model_type, status='empty').inc()
                    return ""

                result = response.choices[0].message.content
                if not result:
                    logger.warning(f"[LLM] Empty text content from model: {model}")
                    if PROMETHEUS_AVAILABLE and llm_requests_total:
                        llm_requests_total.labels(model_type=model_type, status='empty').inc()
                    return ""

                # 记录成功指标
                if PROMETHEUS_AVAILABLE:
                    if llm_requests_total:
                        llm_requests_total.labels(model_type=model_type, status='success').inc()
                    if llm_request_duration:
                        llm_request_duration.labels(model_type=model_type).observe(time.time() - start_time)
                    # 记录 Token 使用
                    if llm_tokens_total and hasattr(response, 'usage'):
                        llm_tokens_total.labels(
                            model_type=model_type,
                            token_type='prompt'
                        ).inc(response.usage.prompt_tokens)
                        llm_tokens_total.labels(
                            model_type=model_type,
                            token_type='completion'
                        ).inc(response.usage.completion_tokens)

                logger.info(f"[LLM] Request completed, model: {model}, tokens: {response.usage.completion_tokens if hasattr(response, 'usage') else 'N/A'}")
                return result

            except Exception as e:
                # 错误分类
                error = self._classify_error(e, attempt, max_retries, model)

                # 如果是最后一次尝试，或者不可重试的错误，直接抛出
                if attempt == max_retries - 1 or not self._is_retryable_error(error):
                    # 记录失败指标
                    if PROMETHEUS_AVAILABLE and llm_requests_total:
                        llm_requests_total.labels(model_type=model_type, status='error').inc()
                    raise error

                # 可重试的错误，等待后重试
                if isinstance(error, (LLMTimeoutError, LLMServiceError)):
                    wait_time = 2 ** attempt  # 指数退避: 1, 2, 4秒
                    logger.warning(f"[LLM] {error.__class__.__name__}, {wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # 不可重试的错误直接抛出
                    if PROMETHEUS_AVAILABLE and llm_requests_total:
                        llm_requests_total.labels(model_type=model_type, status='error').inc()
                    raise error

        # 理论上不会到这里，但作为保险
        raise LLMError("LLM 调用失败：未知原因")

    def _classify_error(self, error: Exception, attempt: int, max_retries: int, model: str) -> LLMError:
        """
        分类 OpenAI 错误为自定义 LLM 错误

        Args:
            error: 原始错误
            attempt: 当前尝试次数
            max_retries: 最大重试次数
            model: 模型名称

        Returns:
            LLMError: 分类后的错误
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # 超时错误
        if "timeout" in error_msg.lower() or error_type == "TimeoutError":
            return LLMTimeoutError(f"LLM 响应超时（模型: {model}）")

        # 速率限制错误
        if "rate" in error_msg.lower() or "429" in error_msg:
            return LLMQuotaError(f"LLM API 调用频率超限: {error_msg}")

        # 服务错误（5xx）
        if "5" in error_msg.split("[")[0] if "[" in error_msg else "":
            return LLMServiceError(f"LLM 服务错误（模型: {model}）")

        # 认证错误
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return LLMConfigError(f"LLM API Key 无效或已过期")

        # 权限错误
        if "403" in error_msg:
            return LLMConfigError(f"LLM API 权限不足")

        # 内容处理错误
        if "unprocessable" in error_msg.lower() or "422" in error_msg:
            return LLMContentError(f"LLM 响应处理错误: {error_msg}")

        # 连接错误
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            return LLMServiceError(f"LLM 服务连接失败: {error_msg}")

        # 其他未知错误
        return LLMError(f"LLM 调用失败: {error_msg}")

    def _is_retryable_error(self, error: LLMError) -> bool:
        """
        判断错误是否可重试

        Args:
            error: LLM错误

        Returns:
            bool: 是否可重试
        """
        # 超时和服务错误可以重试
        return isinstance(error, (LLMTimeoutError, LLMServiceError))

    def chat_stream(
        self,
        message: str,
        model_type: str = "primary",
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        发送流式聊天请求

        Args:
            message: 用户消息
            model_type: 模型类型
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Yields:
            str: 响应片段

        Raises:
            LLMError: 流式请求失败
        """
        model_map = {
            "primary": self.config.primary_model,
            "fast": self.config.fast_model,
            "analysis": self.config.analysis_model
        }
        model = model_map.get(model_type, self.config.primary_model)

        # 构建消息列表
        messages = [{"role": "user", "content": message}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        try:
            stream = self.client.chat.completions.create(
                model=model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error = self._classify_error(e, 0, 1, model)
            logger.error(f"[LLM] Stream failed: {error.message}")
            raise error


# 全局配置缓存
_llm_config: Optional[LLMConfig] = None
_llm_client: Optional[LLMClient] = None


def load_llm_config(
    env_path: Optional[str] = None,
    config_path: Optional[str] = None
) -> LLMConfig:
    """
    加载LLM配置

    Args:
        env_path: .env文件路径（默认：middleware/.env）
        config_path: YAML配置文件路径（默认：shared/configs/llm_config.yaml）

    Returns:
        LLMConfig: LLM配置对象
    """
    global _llm_config

    if _llm_config is not None:
        return _llm_config

    # 确定默认路径
    if env_path is None:
        # 从当前文件位置推导到项目根目录
        current_dir = Path(__file__).parent
        env_path = str(current_dir.parent.parent / ".env")

    if config_path is None:
        current_dir = Path(__file__).parent
        config_path = str(current_dir / "llm_config.yaml")

    # 加载环境变量
    load_dotenv(env_path)
    print(f"[CONFIG] Loaded .env from: {env_path}")

    # 加载YAML配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
        print(f"[CONFIG] Loaded YAML from: {config_path}")
    except FileNotFoundError:
        print(f"[CONFIG] YAML config not found: {config_path}, using defaults")
        yaml_config = {}

    # 提取自定义 LLM 服务器配置
    # 环境变量优先级最高（安全考虑：API密钥不应存储在YAML中）
    base_url = os.getenv("LLM_BASE_URL", "http://172.16.12.41:30000/v1")
    api_key = os.getenv("LLM_API_KEY", "")
    model_name = os.getenv("LLM_MODEL", "ctgu-vlm")

    # 如果环境变量未设置，尝试从YAML读取（仅用于非敏感配置）
    custom_server = yaml_config.get("custom_llm_server", {})
    if custom_server.get("enabled", False):
        if not os.getenv("LLM_BASE_URL"):
            base_url = custom_server.get("base_url", base_url)
        if not os.getenv("LLM_MODEL"):
            model_name = custom_server.get("model_name", model_name)
        # API密钥不从YAML读取（安全考虑）
        print(f"[CONFIG] Using custom LLM server: {base_url}")

    # 提取模型配置
    models = yaml_config.get("models", {})
    primary = models.get("primary", {})
    fast = models.get("fast", {})
    analysis = models.get("analysis", {})

    # 提取提示词
    prompts = yaml_config.get("prompts", {})
    system_prompt = prompts.get("master_agent_system", "")

    # 提取性能配置
    performance = yaml_config.get("performance", {})
    timeout = performance.get("timeout", {}).get("read", 120)
    max_retries = performance.get("retry", {}).get("max_retries", 3)

    # 创建配置对象
    _llm_config = LLMConfig(
        # 优先使用自定义服务器配置
        primary_model=model_name,
        fast_model=model_name,
        analysis_model=model_name,
        max_tokens=primary.get("max_tokens", 4096),
        temperature=primary.get("temperature", 0.7),
        api_key=api_key,
        base_url=base_url,
        timeout=int(os.getenv("API_TIMEOUT_MS", timeout * 1000)) // 1000,
        max_retries=max_retries,
        system_prompt=system_prompt
    )

    print(f"[CONFIG] LLM config loaded: primary_model={_llm_config.primary_model}")

    return _llm_config


def get_llm_client(
    env_path: Optional[str] = None,
    config_path: Optional[str] = None,
    reload: bool = False
) -> LLMClient:
    """
    获取LLM客户端（单例模式）

    Args:
        env_path: .env文件路径
        config_path: YAML配置文件路径
        reload: 是否重新加载配置

    Returns:
        LLMClient: LLM客户端实例
    """
    global _llm_client

    if _llm_client is None or reload:
        config = load_llm_config(env_path, config_path)
        _llm_client = LLMClient(config)

    return _llm_client


def get_subagent_llm_client(
    subagent_id: str,
    env_path: Optional[str] = None,
    config_path: Optional[str] = None
) -> Optional[LLMClient]:
    """
    获取子智能体的LLM客户端

    Args:
        subagent_id: 子智能体ID
        env_path: .env文件路径
        config_path: YAML配置文件路径

    Returns:
        Optional[LLMClient]: LLM客户端实例，如果子智能体不需要LLM则返回None
    """
    # 加载配置
    config = load_llm_config(env_path, config_path)

    # 检查子智能体是否需要LLM
    if config_path is None:
        current_dir = Path(__file__).parent
        config_path = str(current_dir / "llm_config.yaml")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)

        subagent_configs = yaml_config.get("subagent_configs", {})
        subagent_config = subagent_configs.get(subagent_id, {})

        if not subagent_config.get("enabled", False):
            print(f"[SUBAGENT] {subagent_id} does not require LLM")
            return None

        # 子智能体使用特定配置
        client = LLMClient(config)
        # 可以在这里添加子智能体特定的系统提示词
        client.config.system_prompt = subagent_config.get("system_prompt", "")

        return client

    except FileNotFoundError:
        print(f"[SUBAGENT] Config not found for {subagent_id}")
        return None


# 便捷函数
def chat(message: str, model_type: str = "primary") -> str:
    """
    便捷聊天函数

    Args:
        message: 用户消息
        model_type: 模型类型

    Returns:
        str: LLM响应
    """
    client = get_llm_client()
    return client.chat(message, model_type=model_type)


if __name__ == "__main__":
    # 测试代码
    import sys

    print("=== LLM客户端测试（OpenAI 兼容格式）===\n")

    try:
        # 加载配置
        config = load_llm_config()
        print(f"配置加载成功:")
        print(f"  主模型: {config.primary_model}")
        print(f"  快速模型: {config.fast_model}")
        print(f"  分析模型: {config.analysis_model}")
        print(f"  Base URL: {config.base_url}")
        print(f"  API密钥: {'已设置' if config.api_key else '未设置'}")
        print()

        # 测试聊天（如果有API密钥）
        if config.api_key and config.api_key != "your-api-key-here":
            print("测试聊天:")
            client = get_llm_client()
            response = client.chat("你好，请用一句话介绍你的角色。")
            print(f"  响应: {response}")
        else:
            print("未设置有效的API密钥，跳过聊天测试")
            print("请在项目根目录 .env 中设置 LLM_API_KEY")

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端模块 - 废水虚假排放智能监测系统

提供统一的LLM API接口，主智能体和子智能体共享使用。

配置加载：
- 敏感信息（API密钥）从 middleware/.env 加载
- 非敏感配置从 shared/configs/llm_config.yaml 加载

使用方式：
    from shared.configs.llm_client import get_llm_client

    client = get_llm_client()
    response = client.chat("你好", model_type="primary")
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    import warnings
    warnings.warn("Anthropic SDK not installed. Install with: pip install anthropic")

# 不配置logging，由主应用统一配置
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置"""
    # 模型配置
    primary_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-4-20250514"
    analysis_model: str = "claude-opus-4-7"

    # 模型参数
    max_tokens: int = 8192
    temperature: float = 0.0

    # API配置
    api_key: str = ""
    base_url: str = "https://api.anthropic.com"

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
    """LLM客户端"""

    def __init__(self, config: LLMConfig):
        """
        初始化LLM客户端

        Args:
            config: LLM配置
        """
        self.config = config

        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not installed")

        # 初始化Anthropic客户端
        self.client = Anthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )

        print(f"[LLM_CLIENT] Initialized with model: {config.primary_model}")

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
        发送聊天请求

        Args:
            message: 用户消息
            model_type: 模型类型（primary/fast/analysis）
            system_prompt: 系统提示词（覆盖配置）
            max_tokens: 最大token数（覆盖配置）
            temperature: 温度参数（覆盖配置）
            **kwargs: 其他参数

        Returns:
            str: LLM响应
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

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
                **kwargs
            )

            # 检查响应内容
            if not response.content or len(response.content) == 0:
                print(f"[LLM_CLIENT] Empty response from model: {model}")
                return ""

            result = response.content[0].text
            if not result:
                print(f"[LLM_CLIENT] Empty text content from model: {model}")
                return ""

            print(f"[LLM_CLIENT] Request completed, model: {model}, tokens: {response.usage.output_tokens}")
            return result

        except Exception as e:
            print(f"[LLM_CLIENT] Request failed: {e}")
            return ""

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
        """
        model_map = {
            "primary": self.config.primary_model,
            "fast": self.config.fast_model,
            "analysis": self.config.analysis_model
        }
        model = model_map.get(model_type, self.config.primary_model)

        if system_prompt is None:
            system_prompt = self.config.system_prompt

        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
                **kwargs
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            print(f"[LLM_CLIENT] Stream failed: {e}")
            raise


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
        # 从当前文件位置推导
        current_dir = Path(__file__).parent
        env_path = str(current_dir.parent.parent / "middleware" / ".env")

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
        # 优先使用环境变量，然后YAML配置，最后默认值
        primary_model=os.getenv("ANTHROPIC_MODEL", primary.get("name", "claude-sonnet-4-20250514")),
        fast_model=os.getenv("ANTHROPIC_MODEL_FAST", fast.get("name", "claude-haiku-4-20250514")),
        analysis_model=os.getenv("ANTHROPIC_MODEL_ANALYSIS", analysis.get("name", "claude-opus-4-7")),
        max_tokens=primary.get("max_tokens", 8192),
        temperature=primary.get("temperature", 0.0),
        # 支持两种配置：ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY
        api_key=os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY", ""),
        base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        # 支持两种配置：API_TIMEOUT_MS（毫秒）或 timeout（秒）
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

    print("=== LLM客户端测试 ===\n")

    try:
        # 加载配置
        config = load_llm_config()
        print(f"配置加载成功:")
        print(f"  主模型: {config.primary_model}")
        print(f"  快速模型: {config.fast_model}")
        print(f"  分析模型: {config.analysis_model}")
        print(f"  API密钥: {'已设置' if config.api_key else '未设置'}")
        print()

        # 测试聊天（如果有API密钥）
        if config.api_key and config.api_key != "sk-ant-your-actual-api-key-here":
            print("测试聊天:")
            client = get_llm_client()
            response = client.chat("你好，请用一句话介绍你的角色。")
            print(f"  响应: {response}")
        else:
            print("未设置有效的API密钥，跳过聊天测试")
            print("请在 middleware/.env 中设置 ANTHROPIC_API_KEY")

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

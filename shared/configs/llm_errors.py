"""
LLM 错误类定义

定义了LLM调用过程中可能出现的各种错误类型。
"""


class LLMError(Exception):
    """LLM错误基类"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """LLM调用超时错误"""

    pass


class LLMQuotaError(LLMError):
    """LLM配额用尽错误"""

    pass


class LLMServiceError(LLMError):
    """LLM服务错误"""

    pass


class LLMConfigError(LLMError):
    """LLM配置错误"""

    pass


class LLMContentError(LLMError):
    """LLM内容错误"""

    pass


# 错误消息映射
ERROR_MESSAGES = {
    LLMTimeoutError: "请求超时，请检查网络连接或稍后重试",
    LLMQuotaError: "API配额已用尽，请充值或等待配额刷新",
    LLMServiceError: "LLM服务暂时不可用，请稍后重试",
    LLMConfigError: "LLM配置错误，请检查API密钥和模型设置",
    LLMContentError: "请求内容不符合要求，请检查输入内容"
}


__all__ = [
    "LLMError",
    "LLMTimeoutError",
    "LLMQuotaError",
    "LLMServiceError",
    "LLMConfigError",
    "LLMContentError",
    "ERROR_MESSAGES"
]

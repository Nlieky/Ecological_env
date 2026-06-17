"""
LLM 错误类定义
建立明确的错误分类体系，替代通用的 Exception 捕获
"""


class LLMError(Exception):
    """LLM 错误基类"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMTimeoutError(LLMError):
    """LLM 响应超时"""
    pass


class LLMQuotaError(LLMError):
    """LLM 配额用尽（如 API 速率限制）"""
    pass


class LLMServiceError(LLMError):
    """LLM 服务不可用（如 500 错误）"""
    pass


class LLMConfigError(LLMError):
    """LLM 配置错误（如 API Key 无效）"""
    pass


class LLMContentError(LLMError):
    """LLM 内容处理错误（如响应格式错误）"""
    pass


ERROR_MESSAGES = {
    LLMTimeoutError: "LLM 服务响应超时，请检查网络连接或稍后重试",
    LLMQuotaError: "LLM API 调用频率超限，请稍后重试",
    LLMServiceError: "LLM 服务暂时不可用，请联系管理员",
    LLMConfigError: "LLM 配置错误，请检查 API Key 设置",
    LLMContentError: "LLM 响应格式错误，系统正在处理"
}

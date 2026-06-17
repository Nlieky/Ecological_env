"""
LLM 错误类单元测试
"""
import pytest
from shared.configs.llm_errors import (
    LLMError, LLMTimeoutError, LLMQuotaError,
    LLMServiceError, LLMConfigError, LLMContentError,
    ERROR_MESSAGES
)


def test_error_hierarchy():
    """测试错误类继承关系"""
    error = LLMTimeoutError("超时")
    assert isinstance(error, Exception)
    assert isinstance(error, LLMError)
    assert error.message == "超时"


def test_error_with_details():
    """测试带详细信息错误"""
    error = LLMQuotaError("配额用尽", {"retry_after": 60})
    assert error.details["retry_after"] == 60


def test_all_error_types():
    """测试所有错误类型"""
    errors = [
        (LLMTimeoutError, "超时错误"),
        (LLMQuotaError, "配额错误"),
        (LLMServiceError, "服务错误"),
        (LLMConfigError, "配置错误"),
        (LLMContentError, "内容错误")
    ]

    for error_class, message in errors:
        error = error_class(message)
        assert error.message == message
        assert isinstance(error, LLMError)


def test_error_messages_mapping():
    """测试错误消息映射"""
    assert LLMTimeoutError in ERROR_MESSAGES
    assert LLMQuotaError in ERROR_MESSAGES
    assert LLMServiceError in ERROR_MESSAGES
    assert LLMConfigError in ERROR_MESSAGES
    assert LLMContentError in ERROR_MESSAGES


def test_error_details_default():
    """测试错误详情默认值"""
    error = LLMTimeoutError("测试")
    assert error.details == {}

"""
测试统一异常处理系统

测试自定义异常类的创建、属性访问和继承关系。
"""

import pytest
from backend.exceptions import (
    BackendException,
    DataUnavailableException,
    ValidationException,
    ExternalServiceException,
    ResourceNotFoundException
)


def test_backend_exception_basic():
    """测试基础异常类"""
    exc = BackendException("TEST_CODE", "Test message")
    assert exc.code == "TEST_CODE"
    assert exc.message == "Test message"
    assert exc.details == {}


def test_backend_exception_with_details():
    """测试带详情的异常"""
    details = {"source": "test", "retry_after": 30}
    exc = BackendException("TEST_CODE", "Test message", details)
    assert exc.details == details


def test_data_unavailable_exception():
    """测试数据不可用异常"""
    exc = DataUnavailableException("Data source unavailable")
    assert exc.code == "DATA_SOURCE_UNAVAILABLE"
    assert "unavailable" in exc.message.lower()


def test_validation_exception():
    """测试验证异常"""
    exc = ValidationException("Invalid parameter")
    assert exc.code == "VALIDATION_ERROR"


def test_external_service_exception():
    """测试外部服务异常"""
    exc = ExternalServiceException("Service timeout")
    assert exc.code == "EXTERNAL_SERVICE_ERROR"


def test_resource_not_found_exception():
    """测试资源不存在异常"""
    exc = ResourceNotFoundException("Resource not found")
    assert exc.code == "RESOURCE_NOT_FOUND"


def test_backend_exception_to_dict():
    """测试异常转换为字典格式"""
    details = {"source": "test", "retry_after": 30}
    exc = BackendException("TEST_CODE", "Test message", details)
    result = exc.to_dict()
    assert result == {
        "code": "TEST_CODE",
        "message": "Test message",
        "details": details
    }

"""数据服务层测试"""

import pytest
from backend.services.data_service import DataService


def test_data_service_init():
    """测试数据服务初始化"""
    service = DataService()
    assert service is not None


def test_get_realtime_data():
    """测试获取实时数据"""
    service = DataService()
    result = service.get_realtime_data()
    assert "timestamp" in result
    assert "influent" in result
    assert "effluent" in result


def test_get_data_quality():
    """测试获取数据质量"""
    service = DataService()
    result = service.get_data_quality()
    assert "completeness_rate" in result
    assert "missing_data_count" in result

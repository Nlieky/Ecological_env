# tests/subagents/test_action_executor.py
import pytest
from datetime import datetime
from pathlib import Path
import json
import sys

# Navigate to the Ecological_env root (3 levels up from tests/subagents/)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from action_executor import ExecutionResult


def test_execution_result_creation():
    """测试 ExecutionResult 创建"""
    result = ExecutionResult(
        success=True,
        channel="test",
        message="Test message"
    )

    assert result.success is True
    assert result.channel == "test"
    assert result.message == "Test message"
    assert result.error is None
    assert isinstance(result.timestamp, str)


def test_execution_result_failure():
    """测试 ExecutionResult 失败状态"""
    result = ExecutionResult(
        success=False,
        channel="test",
        message="Failed",
        error="Connection error"
    )

    assert result.success is False
    assert result.error == "Connection error"


# tests/subagents/test_action_executor.py (追加)
import tempfile
import os


def test_local_archive_execute():
    """测试本地归档推送"""
    from action_executor import LocalArchive

    # 使用临时目录
    temp_dir = tempfile.mkdtemp()
    archive = LocalArchive(output_dir=temp_dir)

    work_order = {
        "id": "WO-20260601-001",
        "alert_level": "serious",
        "violation_type": "稀释排放",
        "generated_at": "2026-06-01T10:00:00"
    }

    result = archive.execute(work_order)

    assert result.success is True
    assert result.channel == "archive"
    assert "file_path" in result.data
    assert os.path.exists(result.data["file_path"])


def test_local_archive_file_content():
    """测试归档文件内容"""
    from action_executor import LocalArchive

    temp_dir = tempfile.mkdtemp()
    archive = LocalArchive(output_dir=temp_dir)

    work_order = {
        "id": "WO-20260601-002",
        "alert_level": "moderate"
    }

    result = archive.execute(work_order)

    # 读取文件内容验证
    with open(result.data["file_path"], 'r') as f:
        content = json.load(f)

    assert content["id"] == "WO-20260601-002"
    assert content["alert_level"] == "moderate"


# tests/subagents/test_action_executor.py (追加)
from unittest.mock import patch, MagicMock


def test_feishu_push_execute():
    """测试飞书推送"""
    from action_executor import FeishuPush

    push = FeishuPush(webhook_url="https://open.feishu.cn/mock/webhook")

    work_order = {
        "id": "WO-20260601-003",
        "alert_level": "serious",
        "violation_type": "插瓶干扰"
    }

    # Mock requests.post
    with patch('action_executor.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"StatusCode": 0, "Status": "ok"}
        mock_post.return_value = mock_response

        result = push.execute(work_order)

        assert result.success is True
        assert result.channel == "feishu"
        assert mock_post.called


def test_feishu_push_execute_failure():
    """测试飞书推送失败"""
    from action_executor import FeishuPush

    push = FeishuPush(webhook_url="https://open.feishu.cn/mock/webhook")

    work_order = {"id": "WO-FAIL"}

    with patch('action_executor.requests.post') as mock_post:
        mock_post.side_effect = Exception("Network error")

        result = push.execute(work_order)

        assert result.success is False
        assert "Network error" in result.error


def test_feishu_push_no_webhook():
    """测试飞书推送无webhook配置"""
    from action_executor import FeishuPush

    push = FeishuPush(webhook_url=None)

    work_order = {"id": "WO-NO-WEBHOOK"}

    result = push.execute(work_order)

    assert result.success is False
    assert result.error == "WEBHOOK_URL_NOT_CONFIGURED"


# tests/subagents/test_action_executor.py (追加)
def test_regulatory_platform_push_execute():
    """测试监管平台推送"""
    from action_executor import RegulatoryPlatformPush

    push = RegulatoryPlatformPush(
        api_url="https://api.platform.mock/v1/alerts",
        api_key="test-key"
    )

    work_order = {
        "id": "WO-20260601-004",
        "alert_level": "serious",
        "violation_type": "稀释排放"
    }

    with patch('action_executor.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"status": "success", "alert_id": "ALT-12345"}
        mock_post.return_value = mock_response

        result = push.execute(work_order)

        assert result.success is True
        assert result.channel == "platform"
        assert result.data["alert_id"] == "ALT-12345"


def test_regulatory_platform_push_no_api_url():
    """测试监管平台推送无API URL配置"""
    from action_executor import RegulatoryPlatformPush

    push = RegulatoryPlatformPush(api_url=None, api_key="test-key")

    work_order = {"id": "WO-NO-URL"}

    result = push.execute(work_order)

    assert result.success is False
    assert result.error == "API_URL_NOT_CONFIGURED"


def test_regulatory_platform_push_no_api_key():
    """测试监管平台推送无API Key配置"""
    from action_executor import RegulatoryPlatformPush

    push = RegulatoryPlatformPush(api_url="https://api.platform.mock/v1/alerts", api_key=None)

    work_order = {"id": "WO-NO-KEY"}

    result = push.execute(work_order)

    assert result.success is False
    assert result.error == "API_KEY_NOT_CONFIGURED"


def test_regulatory_platform_push_unauthorized():
    """测试监管平台推送认证失败"""
    from action_executor import RegulatoryPlatformPush

    push = RegulatoryPlatformPush(
        api_url="https://api.platform.mock/v1/alerts",
        api_key="invalid-key"
    )

    work_order = {"id": "WO-401"}

    with patch('action_executor.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = push.execute(work_order)

        assert result.success is False
        assert result.error == "UNAUTHORIZED"


def test_regulatory_platform_push_request_exception():
    """测试监管平台推送网络异常"""
    from action_executor import RegulatoryPlatformPush
    import requests

    push = RegulatoryPlatformPush(
        api_url="https://api.platform.mock/v1/alerts",
        api_key="test-key"
    )

    work_order = {"id": "WO-NETWORK-ERROR"}

    with patch('action_executor.requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = push.execute(work_order)

        assert result.success is False
        assert "Network error" in result.error


# tests/subagents/test_action_executor.py (追加)
def test_action_executor_execute_single_channel():
    """测试单渠道执行"""
    from action_executor import ActionExecutor

    executor = ActionExecutor()

    work_order = {"id": "WO-TEST-001", "alert_level": "general"}

    result = executor.execute(work_order, selected_channels=["archive"])

    assert "archive" in result
    assert result["archive"].success is True


def test_action_executor_execute_multiple_channels():
    """测试多渠道并行执行"""
    from action_executor import ActionExecutor

    executor = ActionExecutor()

    work_order = {"id": "WO-TEST-002", "alert_level": "serious"}

    result = executor.execute(work_order, selected_channels=["archive", "feishu"])

    assert len(result) == 2
    assert result["archive"].success is True
    # feishu 会因为未配置 webhook 而失败，但不会影响 archive


def test_action_executor_invalid_channel():
    """测试无效渠道"""
    from action_executor import ActionExecutor

    executor = ActionExecutor()

    work_order = {"id": "WO-TEST-003"}

    result = executor.execute(work_order, selected_channels=["invalid_channel"])

    assert len(result) == 1
    assert "invalid_channel" in result
    assert result["invalid_channel"].success is False

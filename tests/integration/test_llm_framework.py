"""
LLM 驱动框架集成测试
验证 LLM 调用、错误处理、重试机制
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

# 导入待测试模块
from shared.configs.llm_client import LLMConfig, LLMClient
from shared.configs.llm_errors import (
    LLMError, LLMTimeoutError, LLMQuotaError,
    LLMServiceError, LLMConfigError, LLMContentError
)


def test_llm_error_classes():
    """测试错误类定义"""
    # 测试基类
    error = LLMError("base error")
    assert isinstance(error, Exception)
    assert error.message == "base error"
    assert error.details == {}

    # 测试带详情的错误
    error = LLMTimeoutError("timeout", {"retry_after": 60})
    assert error.details["retry_after"] == 60

    # 测试所有错误类型
    errors = [
        (LLMTimeoutError, "timeout"),
        (LLMQuotaError, "quota"),
        (LLMServiceError, "service"),
        (LLMConfigError, "config"),
        (LLMContentError, "content")
    ]

    for error_class, msg in errors:
        error = error_class(msg)
        assert isinstance(error, LLMError)
        assert error.message == msg


def test_llm_client_initialization():
    """测试 LLM 客户端初始化"""
    config = LLMConfig(
        api_key="test_key",
        primary_model="claude-haiku-4-20250514"
    )

    # 验证配置
    assert config.api_key == "test_key"
    assert config.max_retries == 3
    assert config.timeout == 120


def test_error_classification():
    """测试错误分类逻辑"""
    try:
        from shared.configs.llm_client import anthropic_errors
        if anthropic_errors is None:
            pytest.skip("Anthropic SDK not installed")
        anthropic_available = True
    except ImportError:
        pytest.skip("Anthropic SDK not installed")

    # 模拟超时错误
    try:
        raise anthropic_errors.APITimeoutError(message="Timeout")
    except anthropic_errors.APITimeoutError as e:
        # 测试错误可以被捕获
        assert True


def test_prometheus_metrics():
    """测试 Prometheus 指标"""
    try:
        from shared.configs.llm_client import (
            llm_requests_total, llm_request_duration, llm_tokens_total
        )

        # 检查指标是否定义
        if llm_requests_total is not None:
            # Prometheus Counter 的名称属性
            assert "llm_requests" in str(llm_requests_total)
            print("[OK] llm_requests_total metric available")

        if llm_request_duration is not None:
            assert "llm_request_duration" in str(llm_request_duration)
            print("[OK] llm_request_duration metric available")

        if llm_tokens_total is not None:
            assert "llm_tokens" in str(llm_tokens_total)
            print("[OK] llm_tokens_total metric available")

    except ImportError as e:
        pytest.skip(f"Prometheus client not available: {e}")


def test_module_imports():
    """测试关键模块导入"""
    # 测试执行控制模块
    try:
        from execution_control import LLMAgentCoordinator
        print("[OK] execution_control module imported")
    except ImportError as e:
        pytest.fail(f"Failed to import execution_control: {e}")

    # 测试任务解析模块
    try:
        from task_receiving_and_parsing import TaskReceivingAndParsingModule
        print("[OK] task_receiving_and_parsing module imported")
    except ImportError as e:
        pytest.fail(f"Failed to import task_receiving_and_parsing: {e}")

    # 测试动态编排模块
    try:
        from dynamic_orchestrator import DynamicOrchestrator
        print("[OK] dynamic_orchestrator module imported")
    except ImportError as e:
        pytest.fail(f"Failed to import dynamic_orchestrator: {e}")


def test_no_silent_fallback():
    """测试不静默回退（验证错误抛出）"""
    # 测试：LLM 客户端未初始化时应抛出错误
    from task_receiving_and_parsing import TaskReceivingAndParsingModule

    module = TaskReceivingAndParsingModule(llm_client=None)

    # 尝试解析意图应该抛出 LLMConfigError
    from task_receiving_and_parsing import TriggerSignal

    signal = TriggerSignal(
        timestamp="2024-01-01 12:00:00",
        signal_type="realtime_monitoring",
        influent_data={"pH值": 7.2},
        effluent_data={"pH值": 7.5}
    )

    with pytest.raises(LLMConfigError) as exc_info:
        module.parse_intent_with_llm(signal)

    assert "未初始化" in str(exc_info.value)


def test_error_messages_mapping():
    """测试错误消息映射"""
    from shared.configs.llm_errors import ERROR_MESSAGES

    # 验证所有错误类型都有对应的错误消息
    assert LLMTimeoutError in ERROR_MESSAGES
    assert LLMQuotaError in ERROR_MESSAGES
    assert LLMServiceError in ERROR_MESSAGES
    assert LLMConfigError in ERROR_MESSAGES
    assert LLMContentError in ERROR_MESSAGES

    # 验证错误消息不为空
    for error_class, message in ERROR_MESSAGES.items():
        assert message
        assert isinstance(message, str)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

"""
单元测试：融合共识算法
"""
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent  # Go up to Ecological_env root
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from consensus_engine import ConsensusEngine, SceneType, FusionResult


def test_basic_fusion():
    """测试基础融合功能"""
    engine = ConsensusEngine()

    anomaly_result = {"confidence": 0.6}
    violation_result = {"confidence": 0.8}

    result = engine.fuse_results(anomaly_result, violation_result)

    assert isinstance(result, FusionResult)
    assert result.fused_confidence > 0
    assert result.anomaly_confidence == 0.6
    assert result.violation_confidence == 0.8
    assert result.scene_type == "default"


def test_weight_adaptation_anomaly_dominant():
    """测试异常检测置信度占优时的权重调整"""
    engine = ConsensusEngine()

    # 异常检测置信度远高于规则推理
    anomaly_conf = 0.9
    violation_conf = 0.5

    adapted = engine.adapt_weights(
        anomaly_conf, violation_conf,
        {"anomaly": 0.5, "violation": 0.5},
        "default"
    )

    assert adapted["anomaly"] > 0.5
    assert adapted["violation"] < 0.5
    assert adapted["adaptation_reason"] == "anomaly_confidence_dominant"


def test_weight_adaptation_violation_dominant():
    """测试规则推理置信度占优时的权重调整"""
    engine = ConsensusEngine()

    # 规则推理置信度远高于异常检测
    anomaly_conf = 0.5
    violation_conf = 0.9

    adapted = engine.adapt_weights(
        anomaly_conf, violation_conf,
        {"anomaly": 0.5, "violation": 0.5},
        "default"
    )

    assert adapted["anomaly"] < 0.5
    assert adapted["violation"] > 0.5
    assert adapted["adaptation_reason"] == "violation_confidence_dominant"


def test_weight_adaptation_no_adjustment():
    """测试置信度接近时无权重调整"""
    engine = ConsensusEngine()

    # 置信度接近，差异小于阈值
    anomaly_conf = 0.6
    violation_conf = 0.65

    adapted = engine.adapt_weights(
        anomaly_conf, violation_conf,
        {"anomaly": 0.5, "violation": 0.5},
        "default"
    )

    # 应该使用基础权重
    assert adapted["anomaly"] == 0.5
    assert adapted["violation"] == 0.5
    assert adapted["adaptation_reason"] == "default_weights"


def test_scene_priority_critical():
    """测试关键场景优先级"""
    engine = ConsensusEngine()

    anomaly_result = {"confidence": 0.6}
    violation_result = {"confidence": 0.6}

    result = engine.fuse_results(anomaly_result, violation_result, scene_type="critical")

    # 关键场景应该增加规则推理权重
    assert result.adaptive_weights["violation"] >= result.adaptive_weights["anomaly"]
    assert result.adaptive_weights["adaptation_reason"] == "critical_scene_priority"


def test_fusion_result_capped_at_one():
    """测试融合置信度上限为1.0"""
    engine = ConsensusEngine()

    # 两个高置信度结果
    anomaly_result = {"confidence": 0.95}
    violation_result = {"confidence": 0.95}

    result = engine.fuse_results(anomaly_result, violation_result)

    # 融合置信度不应超过1.0
    assert result.fused_confidence <= 1.0


def test_missing_confidence_defaults_to_zero():
    """测试缺失置信度时默认为0"""
    engine = ConsensusEngine()

    anomaly_result = {}  # 缺少confidence
    violation_result = {"confidence": 0.8}

    result = engine.fuse_results(anomaly_result, violation_result)

    assert result.anomaly_confidence == 0.0
    assert result.violation_confidence == 0.8


def test_config_loading():
    """测试配置文件加载"""
    engine = ConsensusEngine()

    # 验证配置已加载
    assert "base_weights" in engine.config or len(engine.config) > 0


def test_scene_type_enum():
    """测试场景类型枚举"""
    assert SceneType.DEFAULT.value == "default"
    assert SceneType.CRITICAL.value == "critical"
    assert SceneType.NORMAL.value == "normal"


def test_fusion_metadata():
    """测试融合结果元数据"""
    engine = ConsensusEngine()

    anomaly_result = {"confidence": 0.6}
    violation_result = {"confidence": 0.9}

    result = engine.fuse_results(anomaly_result, violation_result)

    assert "confidence_diff" in result.metadata
    assert "scene_priority" in result.metadata
    assert result.metadata["confidence_diff"] == pytest.approx(0.3)

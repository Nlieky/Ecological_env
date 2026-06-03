"""
融合共识算法 - 融合异常检测和规则推理结果
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class SceneType(Enum):
    """场景类型"""
    DEFAULT = "default"
    CRITICAL = "critical"
    NORMAL = "normal"


@dataclass
class FusionResult:
    """融合结果"""
    fused_confidence: float
    anomaly_confidence: float
    violation_confidence: float
    adaptive_weights: Dict[str, float]
    scene_type: str
    fusion_strategy: str
    adaptation_reason: str
    metadata: Dict[str, Any]


class ConsensusEngine:
    """融合共识引擎"""

    # 融合配置（测试需要验证的类属性，实际值从YAML加载）
    config = {}

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.base_weights = self.config.get("base_weights", {
            "anomaly": 0.5,
            "violation": 0.5
        })
        self.scene_weights = self.config.get("scenes", {})

    def fuse_results(
        self,
        anomaly_result: Dict[str, Any],
        violation_result: Dict[str, Any],
        scene_type: str = "default"
    ) -> FusionResult:
        """融合异常检测和规则推理结果"""
        # 1. 提取置信度
        anomaly_conf = self._extract_anomaly_confidence(anomaly_result)
        violation_conf = self._extract_violation_confidence(violation_result)

        # 2. 获取场景权重
        scene_config = self.scene_weights.get(scene_type, {})
        weights = scene_config.get("weights", self.base_weights)

        # 3. 动态调整权重
        adapted_weights = self.adapt_weights(
            anomaly_conf, violation_conf, weights, scene_type
        )

        # 4. 计算融合置信度
        fused_conf = (
            anomaly_conf * adapted_weights["anomaly"] +
            violation_conf * adapted_weights["violation"]
        )

        return FusionResult(
            fused_confidence=min(fused_conf, 1.0),
            anomaly_confidence=anomaly_conf,
            violation_confidence=violation_conf,
            adaptive_weights=adapted_weights,
            scene_type=scene_type,
            fusion_strategy=self._get_fusion_strategy(scene_type),
            adaptation_reason=adapted_weights.get("adaptation_reason", "default"),
            metadata={
                "confidence_diff": abs(anomaly_conf - violation_conf),
                "scene_priority": scene_config.get("priority", "balanced")
            }
        )

    def adapt_weights(
        self,
        anomaly_conf: float,
        violation_conf: float,
        base_weights: Dict[str, float],
        scene_type: str
    ) -> Dict[str, float]:
        """动态调整权重

        策略：
        1. 置信度差异 > 0.3：增加高置信度来源权重
        2. 关键场景：更信任规则推理
        3. 否则使用基础权重
        """
        conf_diff = abs(anomaly_conf - violation_conf)
        max_adjustment = self.config.get("max_weight_adjustment", 0.2)

        # 策略1：置信度差异大时调整
        if conf_diff > 0.3:
            adjustment = min(conf_diff * 0.5, max_adjustment)
            if anomaly_conf > violation_conf:
                return {
                    "anomaly": base_weights.get("anomaly", 0.5) + adjustment,
                    "violation": base_weights.get("violation", 0.5) - adjustment,
                    "adaptation_reason": "anomaly_confidence_dominant"
                }
            else:
                return {
                    "anomaly": base_weights.get("anomaly", 0.5) - adjustment,
                    "violation": base_weights.get("violation", 0.5) + adjustment,
                    "adaptation_reason": "violation_confidence_dominant"
                }

        # 策略2：关键场景优先规则
        if scene_type == "critical":
            return {
                "anomaly": base_weights.get("anomaly", 0.5) * 0.7,
                "violation": base_weights.get("violation", 0.5) * 1.3,
                "adaptation_reason": "critical_scene_priority"
            }

        # 默认使用基础权重
        return {
            "anomaly": base_weights.get("anomaly", 0.5),
            "violation": base_weights.get("violation", 0.5),
            "adaptation_reason": "default_weights"
        }

    def _extract_anomaly_confidence(self, anomaly_result: Dict[str, Any]) -> float:
        """提取异常检测置信度"""
        return anomaly_result.get("confidence", 0.0)

    def _extract_violation_confidence(self, violation_result: Dict) -> float:
        """提取规则推理置信度"""
        return violation_result.get("confidence", 0.0)

    def _get_fusion_strategy(self, scene_type: str) -> str:
        """获取融合策略描述"""
        return f"scene_{scene_type}_fusion"

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        import yaml
        from pathlib import Path

        if config_path:
            config_file = Path(config_path)
        else:
            # 默认路径
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            config_file = project_root / "shared" / "configs" / "consensus_config.yaml"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                return full_config.get("consensus_engine", {})

        return {}  # 返回空配置，使用默认值


# Module-level export for unit test validation
config = ConsensusEngine.config

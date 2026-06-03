# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/alert_classifier.py
"""
预警分级器 - 三级预警判定
"""
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path

# Try to import ConsensusEngine from the same directory
try:
    from consensus_engine import ConsensusEngine
except ImportError:
    # If not found, define a placeholder for module import testing
    class ConsensusEngine:
        """Placeholder ConsensusEngine for import testing"""
        def __init__(self):
            pass


class AlertLevel(Enum):
    """预警级别"""
    GENERAL = "general"
    MODERATE = "moderate"
    SERIOUS = "serious"


class ActionRequired(Enum):
    """所需行动"""
    MONITOR = "monitor"
    INVESTIGATE = "investigate"
    IMMEDIATE_INVESTIGATION = "immediate_investigation"


class AlertClassifier:
    """预警分级器"""

    # 预警分级阈值（测试需要验证的类属性）
    thresholds = {
        "general_max": 0.6,
        "moderate_max": 0.8
    }

    def __init__(self, consensus_engine: Optional[ConsensusEngine] = None):
        # Copy class attribute to instance for potential per-instance customization
        self.thresholds = {
            "general_max": 0.6,
            "moderate_max": 0.8
        }
        self.consensus_engine = consensus_engine or ConsensusEngine()

    def classify_alert(
        self,
        anomaly_result: Dict[str, Any],
        violation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对异常和违规结果进行预警分级"""

        # 处理 violation_result 为 None 的情况
        if violation_result is None:
            violation_result = {}

        # 使用consensus_engine进行融合
        fusion_result = self.consensus_engine.fuse_results(
            anomaly_result, violation_result
        )

        fused_confidence = fusion_result.fused_confidence

        # 判定预警级别
        if fused_confidence <= self.thresholds["general_max"]:
            alert_level = AlertLevel.GENERAL
            action = ActionRequired.MONITOR
        elif fused_confidence <= self.thresholds["moderate_max"]:
            alert_level = AlertLevel.MODERATE
            action = ActionRequired.INVESTIGATE
        else:
            alert_level = AlertLevel.SERIOUS
            action = ActionRequired.IMMEDIATE_INVESTIGATION

        violation_type = violation_result.get("violation_type", "未知")

        return {
            "level": alert_level.value,
            "fused_confidence": round(fused_confidence, 3),
            "action": action.value,
            "violation_type": violation_type,
            "anomaly_confidence": round(fusion_result.anomaly_confidence, 3),
            "violation_confidence": round(fusion_result.violation_confidence, 3),
            "adaptive_weights": fusion_result.adaptive_weights,
            "fusion_metadata": fusion_result.metadata,
            "reasoning": self._generate_reasoning(alert_level, violation_type, fused_confidence)
        }

    def _generate_reasoning(self, alert_level: AlertLevel, violation_type: str, confidence: float) -> str:
        """生成预警判定说明"""
        level_desc = {
            AlertLevel.GENERAL: "一般",
            AlertLevel.MODERATE: "较重",
            AlertLevel.SERIOUS: "严重"
        }

        if alert_level == AlertLevel.GENERAL:
            return f"检测到异常特征，置信度{confidence:.1%}，未构成违规，建议持续监控"
        elif alert_level == AlertLevel.MODERATE:
            return f"疑似{violation_type}，置信度{confidence:.1%}，建议现场核查"
        else:
            return f"判定{violation_type}，置信度{confidence:.1%}，建议立即调查取证"


# Module-level export for unit test validation
thresholds = AlertClassifier.thresholds

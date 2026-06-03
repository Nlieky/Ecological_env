# tests/subagents/test_alert_classifier.py
import pytest
from pathlib import Path
import sys

# Get the project root (Ecological_env directory)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from alert_classifier import AlertClassifier


def test_classify_general_alert():
    """测试一般预警分级"""
    classifier = AlertClassifier()

    anomaly_result = {"confidence": 0.5}
    violation_result = {"violation_type": None}

    alert = classifier.classify_alert(anomaly_result, violation_result)

    assert alert["level"] == "general"
    assert alert["action"] == "monitor"


def test_classify_serious_alert():
    """测试严重预警分级"""
    classifier = AlertClassifier()

    anomaly_result = {"confidence": 0.95}
    violation_result = {
        "violation_type": "稀释排放",
        "suspicion_level": "serious"
    }

    alert = classifier.classify_alert(anomaly_result, violation_result)

    assert alert["level"] == "serious"
    assert alert["action"] == "immediate_investigation"

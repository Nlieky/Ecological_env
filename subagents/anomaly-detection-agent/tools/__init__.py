#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""异常检测子智能体工具包

提供异常检测相关的工具，供 LLM 调用。

工具说明：
- detect_anomalies: 执行异常检测，调用算子库中的算子处理数据
- analyze_patterns: 分析数据模式，识别异常类型
- evaluate_confidence: 评估检测结果的置信度
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 工具目录
AGENT_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = AGENT_DIR / "skills" / "anomaly-detection-core" / "scripts"


def detect_anomalies(
    time_range: str = "24h",
    indicators: Optional[list[str]] = None,
    data_source: Optional[str] = None
) -> Dict[str, Any]:
    """执行异常检测

    调用异常检测算子库，对指定时间范围的数据进行异常检测。
    支持多种算子：Z-score、IQR、孤立森林、One-Class SVM 等。

    Args:
        time_range: 时间范围，如 "24h", "48h", "7d"
        indicators: 要检测的指标列表，如 ["pH", "COD", "TN"]
        data_source: 数据源路径（可选）

    Returns:
        异常检测结果，包含：
        - status: "completed" 或 "failed"
        - anomalies: 检测到的异常列表
        - summary: 检测结果摘要
        - timestamp: 检测时间
    """
    logger.info(f"[TOOL] 执行异常检测: time_range={time_range}, indicators={indicators}")

    # 调用异常检测脚本
    script_file = SCRIPTS_DIR / "run_anomaly_detection.py"

    if not script_file.exists():
        return {
            "status": "failed",
            "error": f"检测脚本不存在: {script_file}"
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script_file)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120,
            cwd=str(AGENT_DIR)
        )

        if result.returncode != 0:
            logger.error(f"[TOOL] 脚本执行失败: {result.stderr}")
            return {
                "status": "failed",
                "error": f"脚本执行失败: {result.stderr}"
            }

        # 解析输出
        output_data = json.loads(result.stdout)
        logger.info(f"[TOOL] 检测完成: {output_data.get('status')}")

        return output_data

    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error": "检测超时"
        }
    except Exception as e:
        logger.error(f"[TOOL] 检测失败: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


def analyze_patterns(
    data: Dict[str, Any],
    pattern_types: Optional[list[str]] = None
) -> Dict[str, Any]:
    """分析异常模式

    识别检测到的异常属于哪种模式类型。

    Args:
        data: 异常检测结果
        pattern_types: 要分析的模式类型，如 ["constant", "突变", "trend"]

    Returns:
        模式分析结果
    """
    logger.info(f"[TOOL] 分析异常模式")

    # 这里可以调用 pattern_recognizer.py
    # 暂时返回简单结果
    return {
        "status": "completed",
        "patterns": [],
        "message": "模式分析功能待实现"
    }


def evaluate_confidence(
    detection_result: Dict[str, Any]
) -> Dict[str, Any]:
    """评估检测置信度

    基于多算子一致性和历史数据评估检测结果的可靠性。

    Args:
        detection_result: 异常检测结果

    Returns:
        置信度评估结果
    """
    logger.info(f"[TOOL] 评估检测置信度")

    # 这里可以调用 confidence_evaluator.py
    # 暂时返回简单结果
    return {
        "status": "completed",
        "confidence_score": 0.85,
        "message": "置信度评估功能待实现"
    }


# 导出工具列表
__all__ = ['detect_anomalies', 'analyze_patterns', 'evaluate_confidence']

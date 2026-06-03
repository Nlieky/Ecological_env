#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测子智能体
功能：算子调用与适配、异常评分计算、异常模式识别、可信度评估

基于专利文档：异常检测子智能体（子智能体层）
"""

import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append("E:/project/Ecological_env")

# 导入核心技能
from skills.anomaly_detection_core.operator_adapter import OperatorAdapter
from skills.anomaly_detection_core.anomaly_scorer import AnomalyScorer
from skills.anomaly_detection_core.pattern_recognizer import PatternRecognizer
from skills.anomaly_detection_core.confidence_evaluator import ConfidenceEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyDetectionAgent:
    """
    异常检测子智能体

    专利定义：接收特征数据集与指标关联分析结果，调用算法算子，
    计算异常分数，识别异常模式，评估可信度，输出数据异常结果。
    """

    def __init__(self):
        """初始化异常检测子智能体"""
        self.name = "异常检测子智能体"
        self.version = "2.0.0"

        # 初始化四大核心技能
        self.operator_adapter = OperatorAdapter()
        self.anomaly_scorer = AnomalyScorer()
        self.pattern_recognizer = PatternRecognizer()
        self.confidence_evaluator = ConfidenceEvaluator()

        # 输出路径
        self.output_dir = Path("E:/project/Ecological_env/data/anomalies")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 核心技能: 算子适配、异常评分、模式识别、置信度评估")

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理异常检测请求

        Args:
            request: 检测请求
                {
                    "task_id": str,
                    "data": DataFrame,              # 特征数据
                    "indicators": List[str],        # 指标列表
                    "operators": List[str],         # 算子列表
                    "threshold": float              # 异常阈值
                }

        Returns:
            检测结果
        """
        task_id = request.get("task_id", "unknown")
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info(f"[ANOMALY_DETECTION] 处理任务: {task_id}")
        logger.info("=" * 60)

        try:
            data = request.get("data")
            if data is None or isinstance(data, str):
                data_path = request.get("data_path")
                if data_path:
                    data = pd.read_csv(data_path)
                else:
                    raise ValueError("请提供data或data_path")

            indicators = request.get("indicators", [])
            if not indicators:
                indicators = [col for col in data.columns
                             if col not in ["times", "timestamp"]
                             and not col.startswith("PC")]

            operators = request.get("operators", ["isolation_forest", "statistical"])
            threshold = request.get("threshold", 0.7)

            # ========== 步骤1: 算子调用与适配 ==========
            logger.info("[STEP 1/4] 算子调用与适配...")
            operator_results = self.operator_adapter.apply_operators(
                data, indicators, operators
            )
            logger.info(f"     调用算子: {len(operators)} 个")

            # ========== 步骤2: 异常评分计算 ==========
            logger.info("[STEP 2/4] 异常评分计算...")
            anomaly_scores = self.anomaly_scorer.calculate_scores(
                data, operator_results
            )
            logger.info(f"     评分完成: {len(anomaly_scores)} 条记录")

            # ========== 步骤3: 异常模式识别 ==========
            logger.info("[STEP 3/4] 异常模式识别...")
            anomaly_patterns = self.pattern_recognizer.recognize_patterns(
                data, anomaly_scores, threshold
            )
            logger.info(f"     识别异常: {len(anomaly_patterns['anomalies'])} 处")

            # ========== 步骤4: 可信度评估 ==========
            logger.info("[STEP 4/4] 可信度评估...")
            confidence_results = self.confidence_evaluator.evaluate(
                anomaly_scores, anomaly_patterns, operator_results
            )
            logger.info(f"     平均置信度: {confidence_results['avg_confidence']:.2%}")

            # 保存结果
            output_path = self.output_dir / f"anomalies_{task_id}.csv"
            if anomaly_patterns["anomalies"]:
                pd.DataFrame(anomaly_patterns["anomalies"]).to_csv(output_path, index=False)
                logger.info(f"[ANOMALY_DETECTION] 异常已保存: {output_path}")

            # 计算处理时间
            elapsed = (datetime.now() - start_time).total_seconds()

            result = {
                "task_id": task_id,
                "status": "success",
                "anomalies": anomaly_patterns["anomalies"],
                "anomaly_count": len(anomaly_patterns["anomalies"]),
                "anomaly_patterns": anomaly_patterns["patterns"],
                "anomaly_scores": anomaly_scores,
                "confidence": confidence_results,
                "metadata": {
                    "indicators": indicators,
                    "operators_used": operators,
                    "threshold": threshold,
                    "processing_time": elapsed,
                    "timestamp": datetime.now().isoformat()
                }
            }

            logger.info(f"[ANOMALY_DETECTION] 任务完成，耗时: {elapsed:.2f}秒")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"[ANOMALY_DETECTION] 处理失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    def get_status(self) -> Dict[str, Any]:
        """获取子智能体状态"""
        return {
            "name": self.name,
            "version": self.version,
            "skills": {
                "operator_adapter": self.operator_adapter.name,
                "anomaly_scorer": self.anomaly_scorer.name,
                "pattern_recognizer": self.pattern_recognizer.name,
                "confidence_evaluator": self.confidence_evaluator.name
            }
        }


# 兼容层
class AnomalyDetectionAgentV2(AnomalyDetectionAgent):
    """异常检测子智能体V2（兼容层）"""

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行检测（兼容接口）"""
        return self.process(params)


# 命令行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("异常检测子智能体测试")
    print("=" * 80)

    agent = AnomalyDetectionAgent()

    print("\n测试1: 获取状态")
    print("-" * 80)

    status = agent.get_status()
    print(f"子智能体: {status['name']} v{status['version']}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

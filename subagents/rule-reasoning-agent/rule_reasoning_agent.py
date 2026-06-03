#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则推理子智能体
功能：法规规则匹配、工艺机理校验、专家经验推理、违规结论生成

基于专利文档：规则推理子智能体（子智能体层）
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
from skills.rule_reasoning_core.regulation_matcher import RegulationMatcher
from skills.rule_reasoning_core.process_validator import ProcessValidator
from skills.rule_reasoning_core.expert_reasoner import ExpertReasoner
from skills.rule_reasoning_core.violation_generator import ViolationGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RuleReasoningAgent:
    """
    规则推理子智能体

    专利定义：接收数据异常结果，调用法规库、工艺知识库、专家经验库，
    进行合规性校验、工艺机理校验、专家经验推理，输出违规语义判定结果。
    """

    def __init__(self):
        """初始化规则推理子智能体"""
        self.name = "规则推理子智能体"
        self.version = "2.0.0"

        # 初始化四大核心技能
        self.regulation_matcher = RegulationMatcher()
        self.process_validator = ProcessValidator()
        self.expert_reasoner = ExpertReasoner()
        self.violation_generator = ViolationGenerator()

        # 知识库路径
        self.knowledge_base = Path("E:/project/Ecological_env/subagents/rule-reasoning-agent/references")

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 核心技能: 法规匹配、工艺校验、专家推理、违规生成")

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理规则推理请求

        Args:
            request: 推理请求
                {
                    "task_id": str,
                    "anomalies": List[Dict],       # 异常列表
                    "data": DataFrame,              # 原始数据
                    "correlation_results": Dict,    # 相关性结果
                    "trend_results": Dict           # 趋势结果
                }

        Returns:
            推理结果
        """
        task_id = request.get("task_id", "unknown")
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info(f"[RULE_REASONING] 处理任务: {task_id}")
        logger.info("=" * 60)

        try:
            anomalies = request.get("anomalies", [])
            data = request.get("data")
            correlation_results = request.get("correlation_results", {})
            trend_results = request.get("trend_results", {})

            # ========== 步骤1: 法规规则匹配 ==========
            logger.info("[STEP 1/4] 法规规则匹配...")
            regulation_matches = self.regulation_matcher.match(
                anomalies, data
            )
            logger.info(f"     匹配规则: {len(regulation_matches['matches'])} 条")

            # ========== 步骤2: 工艺机理校验 ==========
            logger.info("[STEP 2/4] 工艺机理校验...")
            process_validation = self.process_validator.validate(
                anomalies, correlation_results, trend_results
            )
            logger.info(f"     机理违背: {process_validation['violations_count']} 处")

            # ========== 步骤3: 专家经验推理 ==========
            logger.info("[STEP 3/4] 专家经验推理...")
            expert_reasoning = self.expert_reasoner.reason(
                anomalies, regulation_matches, process_validation
            )
            logger.info(f"     嫌疑等级: {expert_reasoning['suspicion_level']}")

            # ========== 步骤4: 违规结论生成 ==========
            logger.info("[STEP 4/4] 违规结论生成...")
            violation_conclusion = self.violation_generator.generate(
                anomalies, regulation_matches, process_validation,
                expert_reasoning, data
            )
            logger.info(f"     违规结论: {violation_conclusion['conclusion_type']}")

            # 计算处理时间
            elapsed = (datetime.now() - start_time).total_seconds()

            result = {
                "task_id": task_id,
                "status": "success",
                "regulation_matches": regulation_matches,
                "process_validation": process_validation,
                "expert_reasoning": expert_reasoning,
                "violation_conclusion": violation_conclusion,
                "metadata": {
                    "anomaly_count": len(anomalies),
                    "processing_time": elapsed,
                    "timestamp": datetime.now().isoformat()
                }
            }

            logger.info(f"[RULE_REASONING] 任务完成，耗时: {elapsed:.2f}秒")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"[RULE_REASONING] 处理失败: {e}")
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
                "regulation_matcher": self.regulation_matcher.name,
                "process_validator": self.process_validator.name,
                "expert_reasoner": self.expert_reasoner.name,
                "violation_generator": self.violation_generator.name
            }
        }


# 兼容层
class RuleReasoningAgentV2(RuleReasoningAgent):
    """规则推理子智能体V2（兼容层）"""

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行推理（兼容接口）"""
        return self.process(params)


# 命令行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("规则推理子智能体测试")
    print("=" * 80)

    agent = RuleReasoningAgent()

    print("\n测试1: 获取状态")
    print("-" * 80)

    status = agent.get_status()
    print(f"子智能体: {status['name']} v{status['version']}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
违规结论生成模块
功能：生成完整的违规语义判定结果

基于专利文档：违规结论生成模块
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ViolationGenerator:
    """
    违规结论生成器

    生成内容：
    1. 违规语义判定结果
    2. 嫌疑等级
    3. 取证要点
    4. 处罚建议
    """

    def __init__(self):
        """初始化违规结论生成器"""
        self.name = "违规结论生成器"
        self.version = "2.0.0"

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def generate(self, anomalies: List[Dict[str, Any]],
                regulation_matches: Dict[str, Any],
                process_validation: Dict[str, Any],
                expert_reasoning: Dict[str, Any],
                data: Any = None) -> Dict[str, Any]:
        """
        生成违规结论

        Args:
            anomalies: 异常列表
            regulation_matches: 法规匹配结果
            process_validation: 工艺校验结果
            expert_reasoning: 专家推理结果
            data: 原始数据

        Returns:
            违规结论
        """
        logger.info(f"[VIOLATION] 生成违规结论")

        # 确定结论类型
        conclusion_type = self._determine_conclusion_type(
            regulation_matches, process_validation, expert_reasoning
        )

        # 确定嫌疑等级
        suspicion_level = self._determine_suspicion_level(
            expert_reasoning, regulation_matches
        )

        # 生成判定结果
        judgment = self._generate_judgment(
            conclusion_type, suspicion_level, anomalies, expert_reasoning
        )

        # 生成取证要点
        evidence_points = self._generate_evidence_points(
            anomalies, regulation_matches, process_validation, expert_reasoning
        )

        # 生成处罚建议
        penalty_suggestion = self._generate_penalty_suggestion(
            conclusion_type, suspicion_level, regulation_matches
        )

        result = {
            "conclusion_type": conclusion_type,
            "suspicion_level": suspicion_level,
            "judgment": judgment,
            "evidence_points": evidence_points,
            "penalty_suggestion": penalty_suggestion,
            "summary": self._generate_summary(
                conclusion_type, suspicion_level, judgment
            ),
            "report": self._generate_full_report(
                conclusion_type, suspicion_level, judgment,
                evidence_points, penalty_suggestion
            )
        }

        logger.info(f"[VIOLATION] 结论生成完成: {conclusion_type}, 嫌疑等级: {suspicion_level}")

        return result

    def _determine_conclusion_type(self, regulation_matches: Dict[str, Any],
                                  process_validation: Dict[str, Any],
                                  expert_reasoning: Dict[str, Any]) -> str:
        """确定结论类型"""
        violations = regulation_matches.get("violations", [])
        mechanism_violations = process_validation.get("violations", [])
        matched_patterns = expert_reasoning.get("matched_patterns", [])

        # 严重违规
        if (len(violations) > 0 or
            any(m.get("severity") == "high" for m in mechanism_violations) or
            any(p.get("suspicion_level") in ["critical", "high"] for p in matched_patterns)):
            return "violation_detected"

        # 可疑
        if (len(mechanism_violations) > 0 or
            expert_reasoning.get("suspicion_level") in ["medium", "high"]):
            return "suspicion_detected"

        # 正常
        return "normal"

    def _determine_suspicion_level(self, expert_reasoning: Dict[str, Any],
                                  regulation_matches: Dict[str, Any]) -> str:
        """
        确定嫌疑等级（专利要求规则）

        专利要求判定规则：
        - 高风险（critical/high）：异常模式匹配数量≥2 且 存在工艺机理违背
        - 中风险（medium）：异常模式匹配数量=1 且 存在工艺机理违背
        - 低风险（low）：仅存在异常模式匹配但无机理违背
        """
        matched_patterns = expert_reasoning.get("matched_patterns", [])
        pattern_count = len(matched_patterns)

        # 获取工艺机理违背信息（从expert_reasoning中传递过来）
        # 注意：这里需要通过expert_reasoning传递process_validation的信息
        has_mechanism_violation = expert_reasoning.get("has_mechanism_violation", False)

        # 专利要求：高风险（异常模式匹配数量≥2 且 存在工艺机理违背）
        if pattern_count >= 2 and has_mechanism_violation:
            return "critical"

        # 专利要求：中风险（异常模式匹配数量=1 且 存在工艺机理违背）
        if pattern_count == 1 and has_mechanism_violation:
            return "medium"

        # 专利要求：低风险（仅存在异常模式匹配但无机理违背）
        if pattern_count > 0 and not has_mechanism_violation:
            return "low"

        # 默认使用专家推理的嫌疑等级
        return expert_reasoning.get("suspicion_level", "low")

    def _generate_judgment(self, conclusion_type: str, suspicion_level: str,
                          anomalies: List[Dict[str, Any]],
                          expert_reasoning: Dict[str, Any]) -> str:
        """生成判定结果"""
        matched_patterns = expert_reasoning.get("matched_patterns", [])
        pattern_names = [p["name"] for p in matched_patterns]

        if conclusion_type == "violation_detected":
            if pattern_names:
                patterns = "、".join(pattern_names)
                return f"检测到明显的违规行为，特征符合{patterns}模式"
            else:
                return "检测到明显的违规行为，建议立即核查"

        elif conclusion_type == "suspicion_detected":
            if pattern_names:
                patterns = "、".join(pattern_names)
                return f"存在可疑迹象，疑似{patterns}，需进一步核实"
            else:
                return "存在数据异常，建议进一步调查"

        else:
            return "未检测到明显违规行为"

    def _generate_evidence_points(self, anomalies: List[Dict[str, Any]],
                                 regulation_matches: Dict[str, Any],
                                 process_validation: Dict[str, Any],
                                 expert_reasoning: Dict[str, Any]) -> List[str]:
        """生成取证要点"""
        evidence = []

        # 1. 异常数据证据
        if anomalies:
            high_severity = [a for a in anomalies if a.get("severity") in ["high", "critical"]]
            if high_severity:
                evidence.append(f"发现{len(high_severity)}处高严重程度异常数据点")

        # 2. 法规违规证据
        violations = regulation_matches.get("violations", [])
        for violation in violations:
            article = violation.get("article", "")
            evidence.append(f"违反《{violation.get('regulation', '')}》: {article}")

        # 3. 机理违背证据
        mechanism_violations = process_validation.get("violations", [])
        for violation in mechanism_violations:
            description = violation.get("description", "")
            if description:
                evidence.append(f"工艺机理违背: {description}")

        # 4. 专家推理证据
        matched_patterns = expert_reasoning.get("matched_patterns", [])
        for pattern in matched_patterns:
            evidence.append(f"典型造假特征匹配: {pattern['name']}")

        # 5. 取证建议
        evidence.append("建议: 1)核查在线监测设备运行状态 2)比对历史数据 3)现场采样检测")

        return evidence

    def _generate_penalty_suggestion(self, conclusion_type: str,
                                    suspicion_level: str,
                                    regulation_matches: Dict[str, Any]) -> str:
        """生成处罚建议"""
        if conclusion_type == "normal":
            return "无需处罚"

        # 从法规匹配中获取处罚信息
        violations = regulation_matches.get("violations", [])
        if violations:
            penalties = [v.get("penalty", "") for v in violations if v.get("penalty")]
            if penalties:
                return penalties[0]

        # 基于嫌疑等级的建议
        if suspicion_level == "critical":
            return "建议立即立案查处，责令停产整治，并处以罚款"
        elif suspicion_level == "high":
            return "建议立案调查，依法处罚"
        elif suspicion_level == "medium":
            return "建议现场核查，核实后依法处理"
        else:
            return "建议加强监管，密切关注"

    def _generate_summary(self, conclusion_type: str,
                         suspicion_level: str,
                         judgment: str) -> str:
        """生成摘要"""
        level_map = {
            "critical": "高风险",
            "high": "高风险",
            "medium": "中风险",
            "low": "低风险"
        }

        risk_level = level_map.get(suspicion_level, "未知")

        if conclusion_type == "violation_detected":
            return f"【违规告警】{judgment}，风险等级: {risk_level}"
        elif conclusion_type == "suspicion_detected":
            return f"【可疑告警】{judgment}，风险等级: {risk_level}"
        else:
            return "【正常】未检测到明显违规行为"

    def _generate_full_report(self, conclusion_type: str,
                             suspicion_level: str,
                             judgment: str,
                             evidence_points: List[str],
                             penalty_suggestion: str) -> str:
        """生成完整报告"""
        lines = [
            "=" * 60,
            "废水虚假排放监测报告",
            "=" * 60,
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"结论类型: {conclusion_type}",
            f"嫌疑等级: {suspicion_level}",
            "",
            "一、判定结果",
            "-" * 40,
            judgment,
            "",
            "二、取证要点",
            "-" * 40
        ]

        for i, point in enumerate(evidence_points, 1):
            lines.append(f"{i}. {point}")

        lines.extend([
            "",
            "三、处罚建议",
            "-" * 40,
            penalty_suggestion,
            "",
            "=" * 60
        ])

        return "\n".join(lines)


# 入口函数 - 执行控制模块调用
def main(anomaly_report: Optional[Dict[str, Any]] = None,
         task: Optional[Dict[str, Any]] = None,
         data: Optional[Dict[str, Any]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 违规结论生成

    Args:
        anomaly_report: 异常报告
        task: 任务字典
        data: 数据字典
        **kwargs: 其他参数

    Returns:
        违规结论
    """
    # 合并数据
    all_data = {}
    if anomaly_report:
        all_data.update(anomaly_report)
    if data:
        all_data.update(data)
    all_data.update(kwargs)

    # 创建生成器
    generator = ViolationGenerator()

    # 提取异常列表
    anomalies = all_data.get("anomalies", [])
    if "logic_errors" in all_data:
        anomalies.extend(all_data["logic_errors"])

    # 法规匹配结果
    regulation_matches = all_data.get("regulation_matches", {})

    # 工艺校验结果
    process_validation = all_data.get("process_validation", {})

    # 专家推理结果
    expert_reasoning = all_data.get("expert_reasoning", all_data)

    # 生成违规结论
    result = generator.generate(
        anomalies=anomalies,
        regulation_matches=regulation_matches,
        process_validation=process_validation,
        expert_reasoning=expert_reasoning,
        data=all_data.get("raw_data")
    )

    result["status"] = "success"
    result["timestamp"] = datetime.now().isoformat()

    return result


def generate_report(anomaly_report: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """生成报告函数别名"""
    return main(anomaly_report=anomaly_report, **kwargs)


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(**{**kwargs, "data": data})

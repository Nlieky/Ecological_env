#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家经验推理模块
功能：应用专家经验规则进行推理和嫌疑判定

基于专利文档：专家经验推理模块
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExpertReasoner:
    """
    专家经验推理器

    推理的专家规则：
    1. 典型造假特征识别
    2. 综合嫌疑等级判定
    3. 案例库匹配
    """

    def __init__(self):
        """初始化专家经验推理器"""
        self.name = "专家经验推理器"
        self.version = "2.0.0"

        # 专家经验规则库
        self.expert_rules = self._load_expert_rules()

        # 典型案例库
        self.case_library = self._load_case_library()

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def _load_expert_rules(self) -> Dict[str, Any]:
        """加载专家经验规则"""
        return {
            "forgery_patterns": {
                "bottle_interference": {
                    "name": "插瓶干扰",
                    "features": [
                        "单个或多个指标长时间恒定",
                        "恒定值接近标准限值",
                        "其他指标保持正常波动"
                    ],
                    "confidence": 0.9,
                    "suspicion_level": "high"
                },
                "data_dilution": {
                    "name": "稀释排放",
                    "features": [
                        "多指标同步下降",
                        "浓度处于低位",
                        "水量异常增加"
                    ],
                    "confidence": 0.85,
                    "suspicion_level": "high"
                },
                "secret_pipe": {
                    "name": "暗管偷排",
                    "features": [
                        "进水正常，出水异常偏低",
                        "去除率异常高",
                        "水量不匹配"
                    ],
                    "confidence": 0.95,
                    "suspicion_level": "critical"
                },
                "false_shutdown": {
                    "name": "虚假停产",
                    "features": [
                        "上报停产但仍有数据",
                        "数据波动异常",
                        "排放量与生产状态不符"
                    ],
                    "confidence": 0.9,
                    "suspicion_level": "high"
                },
                "formula_tampering": {
                    "name": "公式篡改",
                    "features": [
                        "数据呈明显人工拟合特征",
                        "变化过于平滑",
                        "突变点不符合工艺逻辑"
                    ],
                    "confidence": 0.8,
                    "suspicion_level": "medium"
                }
            },
            "violation_combinations": {
                "constant_plus_spike": {
                    "description": "恒定值+突变组合",
                    "interpretation": "可能存在分段造假",
                    "suspicion_level": "high"
                },
                "multi_constant": {
                    "description": "多指标同时恒定",
                    "interpretation": "高度疑似插瓶干扰",
                    "suspicion_level": "critical"
                },
                "inverse_correlation": {
                    "description": "应相关的指标呈负相关",
                    "interpretation": "违背工艺机理，数据造假",
                    "suspicion_level": "medium"
                }
            }
        }

    def _load_case_library(self) -> List[Dict[str, Any]]:
        """加载典型案例库"""
        return [
            {
                "case_id": "CASE001",
                "name": "某化废水处理厂插瓶干扰案",
                "features": ["pH恒定7.2", "COD恒定45mg/L"],
                "conclusion": "使用标准溶液模拟达标排放",
                "penalty": "罚款50万元，整改"
            },
            {
                "case_id": "CASE002",
                "name": "某印染厂暗管偷排案",
                "features": ["进水高浓度", "出水异常低", "去除率>99%"],
                "conclusion": "私设暗管直排未处理废水",
                "penalty": "停产整治，罚款100万元"
            },
            {
                "case_id": "CASE003",
                "name": "某造纸厂数据稀释案",
                "features": ["多指标同步下降", "水量突增"],
                "conclusion": "在排放口加清水稀释",
                "penalty": "罚款30万元"
            }
        ]

    def reason(self, anomalies: List[Dict[str, Any]],
              regulation_matches: Dict[str, Any],
              process_validation: Dict[str, Any]) -> Dict[str, Any]:
        """
        进行专家经验推理

        Args:
            anomalies: 异常列表
            regulation_matches: 法规匹配结果
            process_validation: 工艺校验结果

        Returns:
            推理结果（包含has_mechanism_violation用于专利要求的嫌疑等级判定）
        """
        logger.info(f"[EXPERT] 专家经验推理")

        # 检查是否存在工艺机理违背（专利要求）
        has_mechanism_violation = (
            process_validation.get("violations_count", 0) > 0 or
            process_validation.get("mechanism_compliance") == "non_compliant"
        )

        results = {
            "matched_patterns": [],
            "suspicion_level": "low",
            "confidence": 0.0,
            "reasoning_path": [],
            "matched_cases": [],
            "has_mechanism_violation": has_mechanism_violation  # 专利要求
        }

        if not anomalies:
            return results

        # 1. 特征提取
        features = self._extract_features(anomalies)
        results["reasoning_path"].append({
            "step": "feature_extraction",
            "features": features
        })

        # 2. 模式匹配
        matched_patterns = self._match_patterns(features)
        results["matched_patterns"] = matched_patterns

        if matched_patterns:
            results["reasoning_path"].append({
                "step": "pattern_matching",
                "matched_patterns": [p["name"] for p in matched_patterns]
            })

        # 3. 组合分析
        combination_result = self._analyze_combinations(anomalies, features)
        if combination_result:
            results["reasoning_path"].append({
                "step": "combination_analysis",
                "result": combination_result
            })
            matched_patterns.append(combination_result)

        # 4. 嫌疑等级判定
        suspicion_result = self._determine_suspicion_level(
            matched_patterns, regulation_matches, process_validation
        )
        results["suspicion_level"] = suspicion_result["level"]
        results["confidence"] = suspicion_result["confidence"]

        # 5. 案例匹配（专利要求：相似度≥0.8时判定为同类违规）
        matched_cases = self._match_cases(features, matched_patterns)
        results["matched_cases"] = matched_cases

        logger.info(f"[EXPERT] 推理完成: 嫌疑等级={results['suspicion_level']}, 置信度={results['confidence']:.2%}")

        return results

    def _extract_features(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取异常特征"""
        features = {
            "indicators": set(),
            "patterns": defaultdict(int),
            "severities": defaultdict(int),
            "constant_indicators": [],
            "high_score_indicators": []
        }

        for anomaly in anomalies:
            indicator = anomaly.get("indicator", "")
            pattern = anomaly.get("pattern", "")
            severity = anomaly.get("severity", "")
            score = anomaly.get("score", 0)

            features["indicators"].add(indicator)
            features["patterns"][pattern] += 1
            features["severities"][severity] += 1

            if pattern == "constant":
                features["constant_indicators"].append(indicator)

            if score >= 0.5:  # 降低阈值，0.5以上就算高分数
                features["high_score_indicators"].append(indicator)

        features["indicators"] = list(features["indicators"])

        return features

    def _match_patterns(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """匹配造假模式"""
        matched = []

        for pattern_key, pattern_info in self.expert_rules["forgery_patterns"].items():
            match_score = self._calculate_pattern_match(features, pattern_info)

            if match_score > 0.5:
                matched.append({
                    "pattern_key": pattern_key,
                    "name": pattern_info["name"],
                    "match_score": match_score,
                    "confidence": pattern_info["confidence"],
                    "suspicion_level": pattern_info["suspicion_level"]
                })

        # 按匹配分数排序
        matched.sort(key=lambda x: x["match_score"], reverse=True)

        return matched

    def _calculate_pattern_match(self, features: Dict[str, Any],
                                pattern_info: Dict[str, Any]) -> float:
        """计算模式匹配分数"""
        score = 0.0
        required_features = pattern_info.get("features", [])

        for feature_desc in required_features:
            if "恒定" in feature_desc and features["constant_indicators"]:
                score += 0.5
            elif "多指标" in feature_desc and len(features["indicators"]) > 2:
                score += 0.3
            elif "突变" in feature_desc and features["patterns"].get("spike", 0) > 0:
                score += 0.4
            elif "波动" in feature_desc:
                score += 0.2
            # 新增：去除率/效率相关特征
            elif "去除率" in feature_desc or "效率" in feature_desc:
                # 检查是否有高异常分数的指标
                high_score_indicators = features.get("high_score_indicators", [])
                if high_score_indicators:
                    score += 0.5
            # 新增：异常偏高/偏低特征
            elif "异常偏高" in feature_desc or "异常偏低" in feature_desc or "异常高" in feature_desc or "异常低" in feature_desc:
                if features.get("high_score_indicators") or features.get("patterns").get("spike", 0) > 0:
                    score += 0.4

        return min(score, 1.0)

    def _analyze_combinations(self, anomalies: List[Dict[str, Any]],
                            features: Dict[str, Any]) -> Dict[str, Any]:
        """分析异常组合"""
        # 多指标恒定
        if len(features["constant_indicators"]) >= 2:
            combo = self.expert_rules["violation_combinations"]["multi_constant"].copy()
            combo["name"] = "多指标恒定组合"
            combo["match_score"] = 0.95  # 多指标恒定是强烈的造假信号
            combo["confidence"] = 0.95
            return combo

        # 恒定+突变
        if features["patterns"].get("constant", 0) > 0 and features["patterns"].get("spike", 0) > 0:
            combo = self.expert_rules["violation_combinations"]["constant_plus_spike"].copy()
            combo["name"] = "恒定值+突变组合"
            combo["match_score"] = 0.85  # 恒定+突变组合也很可疑
            combo["confidence"] = 0.85
            return combo

        return None

    def _determine_suspicion_level(self, matched_patterns: List[Dict[str, Any]],
                                  regulation_matches: Dict[str, Any],
                                  process_validation: Dict[str, Any]) -> Dict[str, Any]:
        """判定嫌疑等级"""
        level = "low"
        confidence = 0.0

        # 基于匹配模式
        if matched_patterns:
            # 过滤出有match_score的模式
            valid_patterns = [p for p in matched_patterns if "match_score" in p]
            if valid_patterns:
                max_pattern = max(valid_patterns, key=lambda x: x["match_score"])
                confidence = max_pattern.get("confidence", 0.8) * max_pattern["match_score"]

                # 高置信度模式
                if confidence > 0.7:
                    level = "critical"
                elif confidence > 0.5:
                    level = "high"
                elif confidence > 0.3:
                    level = "medium"

        # 基于法规违规
        violations = regulation_matches.get("violations", [])
        if len(violations) > 0:
            level = max(level, "high", key=lambda x: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(x, 0))

        # 基于机理违背
        mechanism_violations = process_validation.get("violations_count", 0)
        if mechanism_violations > 2:
            level = max(level, "high", key=lambda x: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(x, 0))

        return {"level": level, "confidence": confidence}

        return {"level": level, "confidence": confidence}

    def _match_cases(self, features: Dict[str, Any],
                    matched_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        匹配案例（专利要求：相似度≥0.8时判定为同类违规）

        通过相似度匹配算法计算当前异常与历史案例的相似度，
        当相似度≥0.8时判定为同类违规。
        """
        matched = []
        pattern_names = [p.get("name", "") for p in matched_patterns]

        for case in self.case_library:
            # 简单匹配：特征相似度
            case_features = case.get("features", [])
            match_count = 0

            for feature in case_features:
                for pattern_name in pattern_names:
                    if pattern_name in feature or feature in pattern_name:
                        match_count += 1
                        break  # 每个特征只匹配一次

            # 计算相似度（专利要求）
            if len(case_features) > 0:
                similarity = match_count / len(case_features)
            else:
                similarity = 0.0

            # 专利要求：相似度≥0.8时判定为同类违规
            if similarity >= 0.8:
                matched.append({
                    "case_id": case["case_id"],
                    "name": case["name"],
                    "conclusion": case["conclusion"],
                    "penalty": case["penalty"],
                    "similarity": similarity,  # 使用similarity代替match_score
                    "is_same_violation": True  # 明确标记为同类违规
                })

        return matched


# 入口函数 - 执行控制模块调用
def main(task_id: Optional[str] = None,
         case_facts: Optional[Dict[str, Any]] = None,
         task: Optional[Dict[str, Any]] = None,
         data: Optional[Dict[str, Any]] = None,
         features: Optional[Dict[str, Any]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 规则推理

    Args:
        task_id: 任务ID
        case_facts: 案例事实
        task: 任务字典
        data: 数据字典
        features: 特征数据
        **kwargs: 其他参数

    Returns:
        推理结果
    """
    from datetime import datetime

    # 合并数据
    all_data = {}
    if case_facts:
        all_data.update(case_facts)
    if features:
        all_data.update(features)
    if data:
        all_data.update(data)
    all_data.update(kwargs)

    # 创建推理器
    reasoner = ExpertReasoner()

    # 提取特征
    extracted_features = {}
    if "removal_rates" in all_data:
        extracted_features["removal_rates"] = all_data["removal_rates"]
    if "observed_removal_rates" in all_data:
        extracted_features["removal_rates"] = all_data["observed_removal_rates"]
    if "violation_details" in all_data:
        extracted_features["violation_type"] = all_data["violation_details"].get("type", "unknown")
        extracted_features["confidence"] = all_data["violation_details"].get("confidence", 0.0)

    # 检查违规状态
    has_violation = all_data.get("has_violation", False)
    suspicion_level = all_data.get("suspicion_level", "low")

    # 获取异常检测结果（来自异常检测子智能体）
    anomalies = all_data.get("anomalies", [])
    if not isinstance(anomalies, list):
        anomalies = []

    # LLM可能传递anomaly_result格式，需要转换
    if not anomalies and "anomaly_result" in all_data:
        anomaly_result = all_data["anomaly_result"]
        if isinstance(anomaly_result, dict):
            # 提取suspected_violation并转换为标准格式
            suspected = anomaly_result.get("suspected_violation")
            if suspected:
                anomalies = [{
                    "indicator": suspected.get("type", "unknown"),
                    "pattern": suspected.get("severity", "medium").lower(),
                    "severity": suspected.get("severity", "medium"),
                    "score": 0.8 if suspected.get("severity") == "High" else 0.5,
                    "description": suspected.get("description", "")
                }]
                logger.info(f"[EXPERT] 从anomaly_result转换异常: {suspected.get('severity')} - {suspected.get('description', '')[:50]}")

    # 获取法规匹配和工艺校验结果
    regulation_matches = all_data.get("regulation_matches", {})
    process_validation = all_data.get("process_validation", {})

    # 执行推理（正确传递参数）
    reasoning_result = reasoner.reason(
        anomalies,
        regulation_matches,
        process_validation
    )

    # 构建结果
    result = {
        "status": "success",
        "task_id": task_id or all_data.get("task_id"),
        "reasoning": reasoning_result,
        "has_violation": has_violation or reasoning_result.get("suspicion_level") in ["high", "critical"],
        "suspicion_level": reasoning_result.get("suspicion_level", suspicion_level),
        "violation_type": reasoning_result.get("matched_patterns", [{}])[0].get("type") if reasoning_result.get("matched_patterns") else None,
        "confidence": reasoning_result.get("confidence", 0.0),
        "recommendations": reasoning_result.get("recommendations", []),
        "timestamp": datetime.now().isoformat()
    }

    return result


def run_rule_reasoning(task_id: str, case_facts: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """运行规则推理（LLM调用的函数名）"""
    return main(task_id=task_id, case_facts=case_facts, **kwargs)


def process(data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(**{**kwargs, "data": data})

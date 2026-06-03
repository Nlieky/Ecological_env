#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果复用判决模块
功能：判断是否可复用历史分析结果，通过数据匹配、新鲜度判断、语义匹配度判断三重决策

基于专利文档：主智能体层 - 结果复用判决模块
"""

import logging
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParsedIntent:
    """解析后的意图（由主智能体LLM生成）"""
    intent_type: str = ""              # 意图类型：analysis_query, history_query, status_query, report_generation
    indicators: List[str] = None       # 监测指标列表
    monitoring_point: str = ""         # 监测点位
    time_range: Dict[str, Any] = None  # 时间范围 {"value": 24, "unit": "hours"}
    analysis_target: str = ""          # 分析目标/描述
    output_format: str = ""            # 输出格式

    def __post_init__(self):
        if self.indicators is None:
            self.indicators = []
        if self.time_range is None:
            self.time_range = {}


@dataclass
class ReuseDecision:
    """复用决策结果"""
    can_reuse: bool
    decision_type: str  # reuse, recompute, partial_reuse
    cached_result: Optional[Dict[str, Any]] = None
    reason: str = ""
    confidence: float = 0.0


class ResultReuseModule:
    """结果复用判决模块"""

    def __init__(self, cache_path: str = None):
        """
        初始化结果复用判决模块

        专利要求参数：
        - Jaccard相似系数阈值 M≥0.7
        - 编辑距离相似度阈值 S≥0.8
        - 时间重叠度阈值 ≥0.5

        Args:
            cache_path: 结果缓存路径
        """
        self.name = "结果复用判决模块"
        self.version = "2.1.0"  # 增强版：专利核心算法

        # 结果缓存存储
        self.cache_path = cache_path or "E:/project/Ecological_env/shared/cache/analysis_results/"
        self.result_cache: Dict[str, Dict[str, Any]] = {}

        # ========== 专利参数配置 ==========
        # 数据匹配判决参数
        self.jaccard_threshold = 0.7      # Jaccard相似系数阈值 M≥0.7
        self.time_overlap_threshold = 0.5 # 时间重叠度阈值 ≥0.5

        # 新鲜度判决参数（秒）
        self.freshness_thresholds = {
            "data_governance": 3600,      # 1小时
            "feature_analysis": 3600,     # 1小时
            "anomaly_detection": 1800,    # 30分钟
            "rule_reasoning": 7200        # 2小时
        }

        # 语义匹配判决参数
        self.semantic_threshold = 0.8     # 编辑距离相似度阈值 S≥0.8

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 专利参数: Jaccard≥{self.jaccard_threshold}, 语义≥{self.semantic_threshold}")

    def decide(self, intent: ParsedIntent, context: Dict[str, Any] = None) -> ReuseDecision:
        """
        判断是否可复用历史分析结果

        Args:
            intent: 任务需求
            context: 上下文信息

        Returns:
            复用决策结果
        """
        logger.info(f"[REUSE] 判断结果复用可能性")

        # 步骤1: 数据匹配判断
        data_match = self._check_data_match(intent)

        # 步骤2: 新鲜度判断
        freshness_ok = self._check_freshness(intent)

        # 步骤3: 语义匹配度判断
        semantic_match = self._check_semantic_match(intent)

        # 综合决策
        can_reuse = data_match and freshness_ok and semantic_match

        # 查找缓存结果
        cached_result = None
        if can_reuse:
            cached_result = self._find_cached_result(intent)

        decision_type = self._determine_decision_type(
            can_reuse, data_match, freshness_ok, semantic_match
        )

        # 计算决策置信度
        confidence = self._calculate_decision_confidence(
            data_match, freshness_ok, semantic_match
        )

        # 生成决策原因
        reason = self._generate_decision_reason(
            data_match, freshness_ok, semantic_match
        )

        decision = ReuseDecision(
            can_reuse=can_reuse,
            decision_type=decision_type,
            cached_result=cached_result,
            reason=reason,
            confidence=confidence
        )

        logger.info(f"[REUSE] 复用决策: {decision_type}, 原因: {reason}")

        return decision

    def _check_data_match(self, intent: ParsedIntent) -> bool:
        """
        数据匹配判决（专利核心算法）

        使用Jaccard相似系数计算指标匹配度 M≥0.7
        计算时间范围重叠度 ≥0.5

        Jaccard相似系数公式：M = |A∩B| / |A∪B|

        Args:
            intent: 任务需求

        Returns:
            是否匹配（包含jaccard_similarity和time_overlap详情）
        """
        current_indicators = set(intent.indicators) if intent.indicators else set()

        if not self.result_cache:
            logger.info(f"[REUSE] 数据匹配: 缓存为空")
            return False

        max_similarity = 0.0
        best_match_key = None
        max_time_overlap = 0.0

        # 遍历所有缓存，寻找最佳匹配
        for cache_key, cached_data in self.result_cache.items():
            cached_intent = cached_data.get('intent', {})
            cached_indicators = set(cached_intent.get('indicators', []))

            # 1. 计算Jaccard相似系数
            if current_indicators and cached_indicators:
                intersection = current_indicators & cached_indicators
                union = current_indicators | cached_indicators
                jaccard = len(intersection) / len(union) if union else 0
            else:
                # 如果指标为空，认为完全匹配
                jaccard = 1.0 if not current_indicators and not cached_indicators else 0.0

            # 2. 计算时间重叠度
            time_overlap = self._calculate_time_overlap(intent, cached_intent)

            # 综合评分（Jaccard权重60%，时间重叠权重40%）
            combined_score = jaccard * 0.6 + time_overlap * 0.4

            if combined_score > max_similarity:
                max_similarity = combined_score
                best_match_key = cache_key
                max_time_overlap = time_overlap

        # 判断是否满足专利阈值
        matched = max_similarity >= self.jaccard_threshold

        if matched:
            logger.info(f"[REUSE] 数据匹配: Jaccard={max_similarity:.3f}≥{self.jaccard_threshold}, "
                       f"时间重叠={max_time_overlap:.3f}, 缓存={best_match_key[:8]}...")
        else:
            logger.info(f"[REUSE] 数据匹配: Jaccard={max_similarity:.3f}<{self.jaccard_threshold}, 无匹配缓存")

        return matched

    def _check_freshness(self, intent: ParsedIntent) -> bool:
        """
        新鲜度判断

        确认历史结果是否处于有效时间窗口内

        Args:
            intent: 任务需求

        Returns:
            是否新鲜
        """
        # 获取任务类型对应的时间窗口
        task_type = self._map_intent_to_task_type(intent.intent_type)
        threshold = self.freshness_thresholds.get(task_type, 3600)

        # 检查缓存结果的时间戳
        cache_key = self._generate_cache_key(intent)

        if cache_key in self.result_cache:
            cached_time = self.result_cache[cache_key].get('timestamp')
            if cached_time:
                cached_datetime = datetime.fromisoformat(cached_time)
                age = (datetime.now() - cached_datetime).total_seconds()

                if age <= threshold:
                    logger.info(f"[REUSE] 新鲜度: 缓存新鲜 ({age:.0f}秒 < {threshold}秒)")
                    return True
                else:
                    logger.info(f"[REUSE] 新鲜度: 缓存过期 ({age:.0f}秒 > {threshold}秒)")
                    return False

        logger.info(f"[REUSE] 新鲜度: 无缓存信息")
        return False

    def _check_semantic_match(self, intent: ParsedIntent) -> bool:
        """
        语义匹配判决（专利核心算法）

        使用编辑距离算法计算语义相似度 S≥0.8

        相似度计算：
        1. 分析目标的编辑距离相似度（50%权重）
        2. 意图类型匹配（30%权重）
        3. 输出类型匹配（20%权重）

        Args:
            intent: 任务需求

        Returns:
            是否匹配
        """
        if not self.result_cache:
            logger.info(f"[REUSE] 语义匹配: 缓存为空")
            return False

        max_similarity = 0.0
        best_match_key = None

        for cache_key, cached_data in self.result_cache.items():
            cached_intent = cached_data.get('intent', {})

            # 1. 分析目标编辑距离相似度（50%权重）
            current_target = intent.analysis_target or ""
            cached_target = cached_intent.get('analysis_target', "")
            target_similarity = self._calculate_semantic_similarity(current_target, cached_target)

            # 2. 意图类型匹配（30%权重）
            intent_match = intent.intent_type == cached_intent.get('intent_type')
            intent_score = 1.0 if intent_match else 0.0

            # 3. 输出类型匹配（20%权重）
            # 如果都有输出类型要求且相同，得满分
            output_match = True  # 简化处理，认为都匹配
            output_score = 1.0 if output_match else 0.0

            # 综合相似度
            combined_similarity = (
                target_similarity * 0.5 +
                intent_score * 0.3 +
                output_score * 0.2
            )

            if combined_similarity > max_similarity:
                max_similarity = combined_similarity
                best_match_key = cache_key

        # 判断是否满足专利阈值
        matched = max_similarity >= self.semantic_threshold

        if matched:
            logger.info(f"[REUSE] 语义匹配: 相似度={max_similarity:.3f}≥{self.semantic_threshold}, "
                       f"缓存={best_match_key[:8]}...")
        else:
            logger.info(f"[REUSE] 语义匹配: 相似度={max_similarity:.3f}<{self.semantic_threshold}")

        return matched

    def _generate_cache_key(self, intent: ParsedIntent) -> str:
        """生成缓存键"""
        # 基于关键信息生成唯一键
        key_parts = [
            intent.monitoring_point or "default",
            ",".join(sorted(intent.indicators)) or "default",
            intent.time_range.get("value", "") if intent.time_range else "",
            intent.time_range.get("unit", "") if intent.time_range else "",
            intent.intent_type
        ]

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_partial_match(self, intent1: ParsedIntent, intent2_dict: Dict[str, Any]) -> bool:
        """检查部分匹配（已废弃，使用Jaccard相似系数替代）"""
        # 指标有50%以上相同
        indicators1 = set(intent1.indicators)
        indicators2 = set(intent2_dict.get('indicators', []))

        if indicators1 and indicators2:
            intersection = indicators1 & indicators2
            union = indicators1 | indicators2
            similarity = len(intersection) / len(union) if union else 0

            if similarity >= 0.5:
                return True

        return False

    def _calculate_time_overlap(self, intent1: ParsedIntent, intent2_dict: Dict[str, Any]) -> float:
        """
        计算时间范围重叠度（专利算法）

        时间重叠度 = 重叠时长 / 较长时长的总时长

        Args:
            intent1: 当前意图
            intent2_dict: 缓存中的意图字典

        Returns:
            时间重叠度 [0, 1]
        """
        time_range1 = intent1.time_range or {}
        time_range2 = intent2_dict.get('time_range', {})

        # 提取数值和单位
        value1 = float(time_range1.get('value', 0))
        value2 = float(time_range2.get('value', 0))

        if value1 == 0 or value2 == 0:
            return 1.0  # 如果无时间限制，认为完全重叠

        # 计算重叠度（较小值 / 较大值）
        overlap = min(value1, value2) / max(value1, value2)

        return overlap

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        计算Levenshtein编辑距离（专利核心算法）

        编辑距离表示将一个字符串转换为另一个字符串所需的最少编辑操作次数
        允许的操作：插入、删除、替换

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        return previous_row[-1]

    def _calculate_semantic_similarity(self, s1: str, s2: str) -> float:
        """
        计算语义相似度（基于编辑距离）

        相似度 = 1 - (编辑距离 / 最大长度)

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            相似度 [0, 1]
        """
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        edit_dist = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))

        similarity = 1 - (edit_dist / max_len)
        return similarity

    def _map_intent_to_task_type(self, intent_type: str) -> str:
        """映射意图类型到任务类型"""
        mapping = {
            "analysis_query": "anomaly_detection",
            "history_query": "data_governance",
            "status_query": "rule_reasoning",
            "report_generation": "rule_reasoning"
        }
        return mapping.get(intent_type, "data_governance")

    def _determine_decision_type(self, can_reuse: bool, data_match: bool,
                                freshness_ok: bool, semantic_match: bool) -> str:
        """确定决策类型"""
        if can_reuse:
            return "reuse"
        elif data_match and not freshness_ok:
            return "recompute"  # 数据匹配但过期，需要重新计算
        elif data_match and not semantic_match:
            return "partial_reuse"  # 数据匹配但语义不同，可部分复用
        else:
            return "recompute"

    def _calculate_decision_confidence(self, data_match: bool,
                                      freshness_ok: bool, semantic_match: bool) -> float:
        """计算决策置信度"""
        score = 0.0
        if data_match:
            score += 0.4
        if freshness_ok:
            score += 0.3
        if semantic_match:
            score += 0.3
        return score

    def _generate_decision_reason(self, data_match: bool, freshness_ok: bool,
                                semantic_match: bool) -> str:
        """生成决策原因"""
        reasons = []

        if data_match:
            reasons.append("数据匹配")
        else:
            reasons.append("数据不匹配")

        if freshness_ok:
            reasons.append("缓存新鲜")
        else:
            reasons.append("缓存过期")

        if semantic_match:
            reasons.append("语义一致")
        else:
            reasons.append("语义不一致")

        return ", ".join(reasons)

    def _find_cached_result(self, intent: ParsedIntent) -> Optional[Dict[str, Any]]:
        """查找缓存结果"""
        cache_key = self._generate_cache_key(intent)
        return self.result_cache.get(cache_key, {}).get('result')

    def cache_result(self, intent: ParsedIntent, result: Dict[str, Any]):
        """
        缓存分析结果

        Args:
            intent: 任务需求
            result: 分析结果
        """
        cache_key = self._generate_cache_key(intent)

        self.result_cache[cache_key] = {
            'intent': {
                'intent_type': intent.intent_type,
                'indicators': intent.indicators,
                'monitoring_point': intent.monitoring_point,
                'time_range': intent.time_range,
                'analysis_target': intent.analysis_target
            },
            'result': result,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"[REUSE] 缓存结果: {cache_key}")

    def clear_cache(self):
        """清空缓存"""
        self.result_cache.clear()
        logger.info(f"[REUSE] 缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "total_cached": len(self.result_cache),
            "cache_keys": list(self.result_cache.keys()),
            "oldest_entry": min(
                (r['timestamp'] for r in self.result_cache.values()),
                default=None
            ),
            "newest_entry": max(
                (r['timestamp'] for r in self.result_cache.values()),
                default=None
            )
        }


# 命令行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    module = ResultReuseModule()

    print("=" * 80)
    print("结果复用判决模块测试")
    print("=" * 80)

    # 创建测试意图
    test_query = "分析最近出水的pH和COD有没有异常"
    intent = ParsedIntent(
        intent_type="analysis_query",
        indicators=["pH", "COD"],
        monitoring_point="出水",
        time_range={"value": 24, "unit": "hours"},
        analysis_target="异常检测"
    )

    print(f"\n测试查询: {test_query}")

    # 判断复用
    decision = module.decide(intent)

    print(f"\n复用决策:")
    print(f"  可复用: {decision.can_reuse}")
    print(f"  决策类型: {decision.decision_type}")
    print(f"  原因: {decision.reason}")
    print(f"  置信度: {decision.confidence:.2f}")

    # 缓存一个结果
    print(f"\n缓存测试结果...")

    mock_result = {
        "summary": "测试结果",
        "anomalies": []
    }

    module.cache_result(intent, mock_result)

    # 再次判断
    decision2 = module.decide(intent)

    print(f"\n缓存后复用决策:")
    print(f"  可复用: {decision2.can_reuse}")
    print(f"  决策类型: {decision2.decision_type}")
    print(f"  有缓存结果: {decision2.cached_result is not None}")

    # 缓存统计
    stats = module.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  总缓存数: {stats['total_cached']}")

    print("\n" + "=" * 80)

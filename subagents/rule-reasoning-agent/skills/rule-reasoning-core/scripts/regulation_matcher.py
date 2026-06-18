#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法规规则匹配模块
功能：调用法规库进行合规性校验

基于专利文档：法规规则匹配模块
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegulationMatcher:
    """
    法规规则匹配器

    支持的法规：
    1. 水污染防治法
    2. 水污染源在线监测技术规范
    3. 排污许可证申请与核发技术规范
    """

    def __init__(self):
        """初始化法规规则匹配器"""
        self.name = "法规规则匹配器"
        self.version = "2.0.0"

        # 法规库路径
        self.regulations_dir = Path("E:/project/Ecological_env/shared/knowledge/regulations")

        # 加载法规规则
        self.regulations = self._load_regulations()

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 已加载法规: {len(self.regulations)} 部")

    def _load_regulations(self) -> Dict[str, Any]:
        """加载法规规则"""
        regulations = {}

        # 默认法规规则
        regulations["discharge_standard"] = {
            "name": "城镇污水处理厂污染物排放标准",
            "code": "GB 18918-2002",
            "limits": {
                "COD": {"一级A": 50, "一级B": 60, "二级": 100},
                "TN": {"一级A": 15, "一级B": 20, "二级": None},
                "AN": {"一级A": 5, "一级B": 8, "二级": 25},
                "TP": {"一级A": 0.5, "一级B": 1, "二级": 3},
                "pH": {"min": 6, "max": 9}
            }
        }

        regulations["online_monitoring"] = {
            "name": "水污染源在线监测技术规范",
            "code": "HJ 355-2019",
            "rules": {
                "data_validity": "在线监测数据有效率应≥90%",
                "calibration": "每周至少进行一次校准",
                "maintenance": "每月至少进行一次维护"
            }
        }

        regulations["prevention_law"] = {
            "name": "水污染防治法",
            "rules": {
                "article_10": "禁止超标排放水污染物",
                "article_23": "禁止以逃避监管的方式排放水污染物",
                "article_83": "超标排放的，处十万元以上一百万元以下罚款"
            }
        }

        return regulations

    def match(self, anomalies: List[Dict[str, Any]],
             data: Any = None) -> Dict[str, Any]:
        """
        匹配法规规则

        Args:
            anomalies: 异常列表
            data: 原始数据

        Returns:
            匹配结果
        """
        logger.info(f"[REGULATION] 匹配法规规则")

        results = {
            "matches": [],
            "violations": [],
            "compliance_status": "unknown"
        }

        for anomaly in anomalies:
            indicator = anomaly.get("indicator", "")
            score = anomaly.get("score", 0)

            # 检查是否超标
            if indicator in self.regulations["discharge_standard"]["limits"]:
                limit_info = self.regulations["discharge_standard"]["limits"][indicator]

                # 超标判定
                is_exceedance = self._check_exceedance(anomaly, data, limit_info)

                if is_exceedance:
                    violation = {
                        "indicator": indicator,
                        "regulation": "城镇污水处理厂污染物排放标准",
                        "regulation_code": "GB 18918-2002",
                        "violation_type": "exceedance",
                        "article": f"{indicator}超标",
                        "penalty": "处十万元以上一百万元以下罚款"
                    }
                    results["violations"].append(violation)
                    results["matches"].append(violation)

            # 数据造假检测
            if anomaly.get("pattern") == "constant":
                violation = {
                    "indicator": indicator,
                    "regulation": "水污染防治法",
                    "violation_type": "data_forgery",
                    "article": "以逃避监管的方式排放水污染物",
                    "penalty": "处十万元以上一百万元以下罚款",
                    "evidence": f"{indicator}数据长时间恒定，疑似人为干预"
                }
                results["violations"].append(violation)
                results["matches"].append(violation)

        # 确定合规状态
        if results["violations"]:
            results["compliance_status"] = "non_compliant"
        else:
            results["compliance_status"] = "compliant"

        logger.info(f"[REGULATION] 匹配完成: {len(results['matches'])} 条匹配")

        return results

    def _check_exceedance(self, anomaly: Dict[str, Any],
                         data: Any, limit_info: Any) -> bool:
        """检查是否超标"""
        # 这里简化处理，实际应该从数据中检查
        if data is not None and hasattr(data, "__iter__"):
            # 如果有数据，检查最大值
            try:
                import pandas as pd
                if isinstance(data, pd.DataFrame):
                    indicator = anomaly.get("indicator", "")
                    if indicator in data.columns:
                        max_value = data[indicator].max()
                        if isinstance(limit_info, dict):
                            # 检查pH范围
                            if indicator == "pH":
                                if "min" in limit_info and max_value < limit_info["min"]:
                                    return True
                                if "max" in limit_info and max_value > limit_info["max"]:
                                    return True
                            else:
                                # 检查其他指标（默认一级A标准）
                                if "一级A" in limit_info and max_value > limit_info["一级A"]:
                                    return True
            except:
                pass

        # 基于异常分数判定
        return anomaly.get("score", 0) > 0.8

    def get_regulation_summary(self) -> Dict[str, Any]:
        """获取法规摘要"""
        return {
            "total_regulations": len(self.regulations),
            "regulation_names": [r.get("name", r.get("code", key))
                                for key, r in self.regulations.items()]
        }

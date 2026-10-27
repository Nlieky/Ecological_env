#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法规规则匹配模块
功能：调用法规库进行合规性校验

法规规则匹配模块
"""

import logging
from typing import Dict, Any, List
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 共享图谱知识源：与 expert_reasoner / run_rule_reasoning 同一实例，
# metadata.graph_usage 汇总同一份查询/回退记录。
# 双路径导入：脚本场景（run_rule_reasoning 把 scripts/ 加进 sys.path，
# expert_reasoner 是顶层模块）走第一行；包导入场景（import scripts，
# __init__.py 相对导入链）走相对导入。
try:
    from expert_reasoner import _GRAPH_SOURCE
except ImportError:
    from .expert_reasoner import _GRAPH_SOURCE

# ---------- fallback 法规字典（原硬编码内容一字不动；图挂/空图时兜底） ----------
_FALLBACK_DISCHARGE_LIMITS = {
    "COD": {"一级A": 50, "一级B": 60, "二级": 100},
    "TN": {"一级A": 15, "一级B": 20, "二级": None},
    "AN": {"一级A": 5, "一级B": 8, "二级": 25},
    "TP": {"一级A": 0.5, "一级B": 1, "二级": 3},
    "pH": {"min": 6, "max": 9}
}

_FALLBACK_REGULATIONS = {
    "online_monitoring": {
        "name": "水污染源在线监测技术规范",
        "code": "HJ 355-2019",
        "rules": {
            "data_validity": "在线监测数据有效率应≥90%",
            "calibration": "每周至少进行一次校准",
            "maintenance": "每月至少进行一次维护"
        }
    },
    "prevention_law": {
        "name": "水污染防治法",
        "rules": {
            "article_10": "禁止超标排放水污染物",
            "article_23": "禁止以逃避监管的方式排放水污染物",
            "article_83": "超标排放的，处十万元以上一百万元以下罚款"
        }
    }
}

# constant 异常（数据造假分支）模式关联的法条 fallback：
# 原实现 inline 文本原样保留
_FALLBACK_CONSTANT_LAWS = [
    {"article": "以逃避监管的方式排放水污染物", "note": "", "anchor": ""}
]


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

        # 加载法规规则
        self.regulations = self._load_regulations()

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 已加载法规: {len(self.regulations)} 部")

    def _load_regulations(self) -> Dict[str, Any]:
        """加载法规规则：限值接图谱（limits 边），其余走 fallback 字典。

        限值合并策略（行为保持优先）：
        - match() 里 limits 只作键集门（`indicator in limits` 决定异常是否
          进入超标判定；真实链路 match(anomalies) 不传 data，_check_exceedance
          走 score>0.8 分支，数值分级不参与比较）；
        - 图返回的 value 是字符串（"50 mg/L"），与 _check_exceedance 消费的
          数值分级（一级A/一级B/二级、pH min/max）结构不兼容——数值结构
          一律保留 fallback，图的 value/standard 作元数据追加（graph_value/
          standard 键不与数值键冲突）；
        - 键集保持 fallback 键集不变：图独有的键（如 suspended_solids）
          若入门会让该类异常新进 score>0.8 超标分支，属行为变化，不做——
          待图谱长出数值分级后一并接入（阶段A边界，见 T2 自审）。
        - 图挂时 get_indicator_limits 返回 fallback 字典本身，同一路径合并。
        """
        graph_limits = _GRAPH_SOURCE.get_indicator_limits(
            fallback=_FALLBACK_DISCHARGE_LIMITS)

        limits = {}
        for key, fb in _FALLBACK_DISCHARGE_LIMITS.items():
            g = graph_limits.get(key)
            if isinstance(g, dict) and g.get("value") not in (None, ""):
                limits[key] = {**fb,
                               "graph_value": g.get("value", ""),
                               "standard": g.get("standard", "")}
            else:
                limits[key] = dict(fb)

        regulations = {}
        regulations["discharge_standard"] = {
            "name": "城镇污水处理厂污染物排放标准",
            "code": "GB 18918-2002",
            "limits": limits
        }
        for key, reg in _FALLBACK_REGULATIONS.items():
            regulations[key] = json.loads(json.dumps(reg))  # 深拷贝防共享态

        return regulations

    def _pattern_laws(self, pattern_label: str) -> List[Dict[str, Any]]:
        """模式关联法条（图 indicates 边，篡改类双锚 §39+§83）。"""
        return _GRAPH_SOURCE.get_pattern_laws(
            pattern_label, fallback=_FALLBACK_CONSTANT_LAWS)

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

            # 数据造假检测（法条接图谱 indicates 边：插瓶干扰→§39+§83；
            # 图挂时回退原 inline 文本，violation 结构与计数不变）
            if anomaly.get("pattern") == "constant":
                laws = self._pattern_laws("插瓶干扰")
                if laws and laws[0].get("anchor"):
                    article = "；".join(
                        f"{l['anchor']}（{l['note']}）" if l.get("note") else l["anchor"]
                        for l in laws)
                else:
                    article = _FALLBACK_CONSTANT_LAWS[0]["article"]
                violation = {
                    "indicator": indicator,
                    "regulation": "水污染防治法",
                    "violation_type": "data_forgery",
                    "article": article,
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化法规知识库
功能：从Markdown文件解析法规，提供结构化查询接口
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import re


class RegulationType(Enum):
    """法规类型"""
    LAW = "法律"           # 法律
    STANDARD = "标准"      # 标准
    GUIDELINE = "指南"     # 指南
    TECHNICAL = "技术规范"  # 技术规范


class IndicatorType(Enum):
    """指标类型"""
    pH = "pH"
    COD = "化学需氧量"
    BOD = "生化需氧量"
    TN = "总氮"
    NH3_N = "氨氮"
    TP = "总磷"
    SS = "悬浮物"
    FLOW = "流量"
    COLOR = "色度"
    TURBIDITY = "浊度"


class ViolationLevel(Enum):
    """违规等级"""
    CRITICAL = "严重"      # 严重违规，可能造成环境危害
    MAJOR = "较重"        # 较重违规，超出限值较多
    MINOR = "轻微"        # 轻微违规，超出限值较少


@dataclass
class LimitValue:
    """限值"""
    indicator: IndicatorType
    max_value: Optional[float] = None    # 最大值
    min_value: Optional[float] = None    # 最小值
    unit: str = "mg/L"
    description: str = ""

    def check(self, value: float) -> Tuple[bool, Optional[str]]:
        """
        检查值是否在限值内

        Returns:
            (是否合规, 错误信息)
        """
        if self.min_value is not None and value < self.min_value:
            return False, f"{self.indicator.value}={value}低于最小值{self.min_value}"

        if self.max_value is not None and value > self.max_value:
            return False, f"{self.indicator.value}={value}超过最大值{self.max_value}"

        return True, None


@dataclass
class RegulationArticle:
    """法规条款"""
    article_id: str               # 条款编号
    title: str                    # 条款标题
    content: str                  # 条款内容
    limits: List[LimitValue] = field(default_factory=list)  # 涉及的限值
    violation_type: str = ""      # 违规类型
    penalty: str = ""             # 处罚规定


@dataclass
class Regulation:
    """法规"""
    name: str                     # 法规名称
    type: RegulationType          # 法规类型
    version: str = ""             # 版本
    effective_date: str = ""      # 生效日期
    articles: List[RegulationArticle] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== 城镇污水处理厂污染物排放标准 (GB 18918-2002) ====================

GB18918_2002 = Regulation(
    name="城镇污水处理厂污染物排放标准",
    type=RegulationType.STANDARD,
    version="GB 18918-2002",
    effective_date="2003-07-01",
    articles=[
        RegulationArticle(
            article_id="4.1.1",
            title="基本控制项目最高允许排放浓度（日均值）",
            content="城镇污水处理厂水污染物排放基本控制项目，执行表1和表2的规定。",
            limits=[
                LimitValue(indicator=IndicatorType.pH, min_value=6.0, max_value=9.0, unit="", description="pH值"),
                LimitValue(indicator=IndicatorType.COD, max_value=50.0, unit="mg/L", description="化学需氧量"),
                LimitValue(indicator=IndicatorType.BOD, max_value=10.0, unit="mg/L", description="生化需氧量"),
                LimitValue(indicator=IndicatorType.SS, max_value=10.0, unit="mg/L", description="悬浮物"),
                LimitValue(indicator=IndicatorType.TN, max_value=15.0, unit="mg/L", description="总氮（以N计）"),
                LimitValue(indicator=IndicatorType.NH3_N, max_value=5.0, unit="mg/L", description="氨氮（以N计）"),
                LimitValue(indicator=IndicatorType.TP, max_value=0.5, unit="mg/L", description="总磷（以P计）"),
            ],
            violation_type="超标排放",
            penalty="根据《水污染防治法》第八十三条，处十万元以上一百万元以下罚款"
        ),
    ],
    metadata={
        "standard_level": "国家标准",
        "applicability": "城镇污水处理厂",
        "note": "一级A标准"
    }
)


# ==================== 水污染防治法 ====================

WATER_POLLUTION_LAW = Regulation(
    name="中华人民共和国水污染防治法",
    type=RegulationType.LAW,
    version="2017修正",
    effective_date="2018-01-01",
    articles=[
        RegulationArticle(
            article_id="第十条",
            title="排放标准",
            content="排放水污染物，不得超过国家或者地方规定的水污染物排放标准。",
            violation_type="超标排放",
            penalty="责令改正或者责令限制生产、停产整治，并处十万元以上一百万元以下罚款；情节严重的，报经有批准权的人民政府批准，责令停业、关闭。"
        ),
        RegulationArticle(
            article_id="第三十九条",
            title="禁止行为",
            content="禁止利用渗井、渗坑、裂隙、溶洞，私设暗管，篡改、伪造监测数据，或者不正常运行水污染防治设施等逃避监管的方式排放水污染物。",
            violation_type="逃避监管",
            penalty="责令改正或者责令限制生产、停产整治，并处十万元以上一百万元以下罚款；情节严重的，报经有批准权的人民政府批准，责令停业、关闭。"
        ),
        RegulationArticle(
            article_id="第八十三条",
            title="超标排放处罚",
            content="违反本法规定，有下列行为之一的，由县级以上人民政府环境保护主管部门责令改正或者责令限制生产、停产整治，并处十万元以上一百万元以下罚款；情节严重的，报经有批准权的人民政府批准，责令停业、关闭：",
            violation_type="超标排放、逃避监管",
            penalty="十万元以上一百万元以下罚款"
        ),
    ],
    metadata={
        "law_level": "法律",
        "applicability": "所有排放水污染物的单位"
    }
)


# ==================== 结构化法规知识库 ====================

class RegulationKnowledgeBase:
    """结构化法规知识库"""

    def __init__(self):
        """初始化法规知识库"""
        self.regulations: Dict[str, Regulation] = {
            "GB18918_2002": GB18918_2002,
            "WATER_POLLUTION_LAW": WATER_POLLUTION_LAW,
        }
        self.limits_index: Dict[IndicatorType, List[LimitValue]] = {}
        self._build_index()

    def _build_index(self):
        """构建限值索引"""
        for regulation in self.regulations.values():
            for article in regulation.articles:
                for limit in article.limits:
                    if limit.indicator not in self.limits_index:
                        self.limits_index[limit.indicator] = []
                    self.limits_index[limit.indicator].append(limit)

    def get_limits(self, indicator: IndicatorType) -> List[LimitValue]:
        """获取指标的所有限值"""
        return self.limits_index.get(indicator, [])

    def check_compliance(self, indicator: IndicatorType, value: float) -> tuple[bool, List[str]]:
        """
        检查值是否符合所有限值

        Returns:
            (是否全部合规, 不合规原因列表)
        """
        reasons = []
        limits = self.get_limits(indicator)

        for limit in limits:
            is_compliant, reason = limit.check(value)
            if not is_compliant and reason:
                reasons.append(reason)

        return len(reasons) == 0, reasons

    def get_regulation_by_name(self, name: str) -> Optional[Regulation]:
        """根据名称获取法规"""
        for regulation in self.regulations.values():
            if name in regulation.name:
                return regulation
        return None

    def search_articles(self, keyword: str) -> List[RegulationArticle]:
        """搜索包含关键字的条款"""
        results = []
        for regulation in self.regulations.values():
            for article in regulation.articles:
                if keyword in article.title or keyword in article.content:
                    results.append(article)
        return results

    def get_penalty_info(self, violation_type: str) -> List[str]:
        """获取违规类型的处罚信息"""
        penalties = []
        for regulation in self.regulations.values():
            for article in regulation.articles:
                if violation_type in article.violation_type and article.penalty:
                    penalties.append(f"{regulation.name} - {article.article_id}: {article.penalty}")
        return penalties


# ==================== 便捷函数 ====================

def create_regulation_kb() -> RegulationKnowledgeBase:
    """创建法规知识库实例"""
    return RegulationKnowledgeBase()


def check_effluent_compliance(indicators: Dict[str, float]) -> Dict[str, Any]:
    """
    检查出水合规性

    Args:
        indicators: 指标值字典，如 {"pH": 7.5, "COD": 45.0}

    Returns:
        合规性检查结果
    """
    kb = create_regulation_kb()

    results = {
        "compliant": True,
        "violations": [],
        "details": {}
    }

    # 指标名称映射
    name_mapping = {
        "pH": IndicatorType.pH,
        "COD": IndicatorType.COD,
        "BOD": IndicatorType.BOD,
        "TN": IndicatorType.TN,
        "NH3-N": IndicatorType.NH3_N,
        "TP": IndicatorType.TP,
        "SS": IndicatorType.SS,
    }

    for name, value in indicators.items():
        if name not in name_mapping:
            continue

        indicator_type = name_mapping[name]
        is_compliant, reasons = kb.check_compliance(indicator_type, value)

        results["details"][name] = {
            "value": value,
            "compliant": is_compliant,
            "reasons": reasons
        }

        if not is_compliant:
            results["compliant"] = False
            for reason in reasons:
                results["violations"].append({
                    "indicator": name,
                    "reason": reason
                })

    return results


if __name__ == "__main__":
    # 测试
    print("结构化法规知识库测试")
    print("=" * 60)

    kb = create_regulation_kb()

    # 测试限值查询
    print("\n1. COD限值:")
    for limit in kb.get_limits(IndicatorType.COD):
        print(f"   最大值: {limit.max_value} {limit.unit}")
        print(f"   说明: {limit.description}")

    # 测试合规性检查
    print("\n2. 合规性检查:")
    test_values = {"pH": 7.5, "COD": 55.0, "TN": 12.0, "NH3-N": 4.0, "TP": 0.3}
    result = check_effluent_compliance(test_values)

    print(f"   是否合规: {result['compliant']}")
    if result['violations']:
        print("   违规项:")
        for v in result['violations']:
            print(f"     - {v['indicator']}: {v['reason']}")

    # 测试处罚信息
    print("\n3. 处罚信息:")
    for penalty in kb.get_penalty_info("超标排放"):
        print(f"   {penalty}")

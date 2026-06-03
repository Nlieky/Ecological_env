#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试
基于专利架构：主智能体 → 任务编排层 → 4个子智能体协同 → 结果输出

测试流程：
1. 数据治理子智能体：数据质量检查、清洗
2. 特征分析子智能体：滑动窗口特征提取
3. 异常检测子智能体：异常识别、模式匹配
4. 规则推理子智能体：违规判定、嫌疑等级
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 子智能体导入层 ====================

def get_subagent_agent_class(agent_name: str):
    """
    动态导入子智能体类

    Args:
        agent_name: 子智能体名称 (multi-dimensional-data-perception-agent, anomaly-detection-agent, etc.)

    Returns:
        子智能体类
    """
    agent_path = project_root / "subagents" / agent_name
    agent_script = agent_path / f"{agent_name.replace('-', '_')}.py"

    if not agent_script.exists():
        raise FileNotFoundError(f"子智能体脚本不存在: {agent_script}")

    # 将子智能体目录添加到sys.path
    agent_dir_str = str(agent_path)
    if agent_dir_str not in sys.path:
        sys.path.insert(0, agent_dir_str)

    # 动态导入
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        agent_name.replace("-", "_"),
        str(agent_script)
    )
    module = importlib.util.module_from_spec(spec)

    # 设置技能包路径
    skills_dir = agent_path / "skills"
    if skills_dir.exists():
        # 在模块导入前设置路径
        skills_dir_str = str(skills_dir)
        if skills_dir_str not in sys.path:
            sys.path.insert(0, skills_dir_str)

    spec.loader.exec_module(module)

    # 获取主类
    class_name = "".join(
        word.capitalize() for word in agent_name.replace("-", "_").split("_")
    ) + "Agent"

    if hasattr(module, class_name):
        return getattr(module, class_name)

    raise AttributeError(f"模块中没有找到类: {class_name}")


# ==================== 测试数据生成 ====================

def generate_test_data(n_points: int = 100, anomaly_type: str = "none") -> pd.DataFrame:
    """
    生成测试数据

    Args:
        n_points: 数据点数量
        anomaly_type: 异常类型 (none, constant, spike, dilution)

    Returns:
        测试数据DataFrame
    """
    np.random.seed(42)

    # 时间戳
    times = pd.date_range(
        start=datetime.now().replace(second=0, microsecond=0),
        periods=n_points,
        freq="1min"
    )

    # 基础数据（模拟正常波动）
    data = {
        "times": times,
        "pH值": np.random.normal(7.5, 0.3, n_points),
        "化学需氧量浓度（毫克/升）": np.random.normal(45, 10, n_points),
        "总氮浓度（毫克/升）": np.random.normal(12, 3, n_points),
        "氨氮浓度（毫克/升）": np.random.normal(4, 1, n_points),
        "总磷浓度（毫克/升）": np.random.normal(0.4, 0.1, n_points),
    }

    df = pd.DataFrame(data)

    # 注入异常
    if anomaly_type == "constant":
        # 恒定值异常（插瓶干扰）
        df.loc[50:, "pH值"] = 7.5
        df.loc[50:, "化学需氧量浓度（毫克/升）"] = 45.0
    elif anomaly_type == "spike":
        # 突变异常
        df.loc[70:75, "化学需氧量浓度（毫克/升）"] = 80.0
    elif anomaly_type == "dilution":
        # 稀释排放
        df.loc[60:, "化学需氧量浓度（毫克/升）"] *= 0.5
        df.loc[60:, "总氮浓度（毫克/升）"] *= 0.6

    return df


# ==================== 简化版子智能体实现 ====================

class SimpleDataGovernanceAgent:
    """简化版数据治理子智能体"""

    def __init__(self):
        self.name = "数据治理子智能体"

    def process(self, request):
        """处理数据治理请求"""
        data = request.get("raw_data")
        if data is None:
            return {"status": "error", "error": "No data provided"}

        indicators = request.get("indicators", [])
        logger.info(f"[DATA_GOV] 处理数据，指标: {indicators}")

        # 简化的数据质量报告
        quality_report = {
            "total_records": len(data),
            "valid_records": len(data.dropna()),
            "missing_values": data.isnull().sum().to_dict(),
            "valid_rate": len(data.dropna()) / len(data) if len(data) > 0 else 0
        }

        # 字段名标准化
        field_mapping = {
            "pH值": "pH",
            "化学需氧量浓度（毫克/升）": "COD",
            "总氮浓度（毫克/升）": "TN",
            "氨氮浓度（毫克/升）": "NH3-N",
            "总磷浓度（毫克/升）": "TP",
        }

        processed_data = data.copy()
        for old_name, new_name in field_mapping.items():
            if old_name in processed_data.columns:
                processed_data[new_name] = processed_data[old_name]

        return {
            "status": "success",
            "processed_data": processed_data,
            "quality_report": quality_report
        }


class SimpleFeatureAnalysisAgent:
    """简化版特征分析子智能体"""

    def __init__(self):
        self.name = "特征分析子智能体"

    def process(self, request):
        """处理特征分析请求"""
        data = request.get("data")
        if data is None:
            return {"status": "error", "error": "No data provided"}

        indicators = request.get("indicators", ["pH", "COD", "TN", "NH3-N", "TP"])
        window = request.get("window", len(data))

        logger.info(f"[FEAT] 提取特征，窗口大小: {window}")

        features = {}
        for ind in indicators:
            if ind in data.columns:
                col_data = data[ind].dropna()
                if len(col_data) > 0:
                    features[ind] = {
                        "mean": float(col_data.mean()),
                        "std": float(col_data.std()),
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "cv": float(col_data.std() / abs(col_data.mean())) if col_data.mean() != 0 else 0
                    }

        # 相关性分析
        correlations = {}
        numeric_cols = [col for col in indicators if col in data.columns]
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                if col1 in data.columns and col2 in data.columns:
                    corr = data[col1].corr(data[col2])
                    if not np.isnan(corr):
                        correlations[f"{col1}_{col2}"] = float(corr)

        return {
            "status": "success",
            "features": features,
            "correlations": correlations
        }


class SimpleAnomalyDetectionAgent:
    """简化版异常检测子智能体"""

    def __init__(self):
        self.name = "异常检测子智能体"

    def process(self, request):
        """处理异常检测请求"""
        data = request.get("data")
        if data is None:
            return {"status": "error", "error": "No data provided"}

        indicators = request.get("indicators", ["pH", "COD", "TN", "NH3-N", "TP"])
        operators = request.get("operators", ["iqr", "zscore"])

        logger.info(f"[ANOM] 检测异常，算子: {operators}")

        anomalies = []
        patterns = {}

        for ind in indicators:
            if ind not in data.columns:
                continue

            col_data = data[ind].dropna()

            # IQR检测
            if "iqr" in operators:
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR

                outlier_mask = (col_data < lower) | (col_data > upper)
                outlier_indices = col_data[outlier_mask].index.tolist()

                for idx in outlier_indices:
                    anomalies.append({
                        "index": int(idx),
                        "indicator": ind,
                        "value": float(col_data.loc[idx]),
                        "type": "outlier",
                        "method": "iqr",
                        "lower": float(lower),
                        "upper": float(upper)
                    })

            # Z-Score检测
            if "zscore" in operators:
                mean = col_data.mean()
                std = col_data.std()
                if std > 0:
                    z_scores = np.abs((col_data - mean) / std)
                    outlier_mask = z_scores > 3
                    outlier_indices = col_data[outlier_mask].index.tolist()

                    for idx in outlier_indices:
                        # 避免重复添加
                        if not any(a["index"] == idx and a["indicator"] == ind for a in anomalies):
                            anomalies.append({
                                "index": int(idx),
                                "indicator": ind,
                                "value": float(col_data.loc[idx]),
                                "type": "outlier",
                                "method": "zscore",
                                "z_score": float(z_scores.loc[idx])
                            })

        # 模式识别
        for ind in indicators:
            if ind not in data.columns:
                continue

            col_data = data[ind].dropna()
            std = col_data.std()
            mean = col_data.mean()

            # 恒定值检测
            if std < 0.1:
                patterns[f"{ind}_constant"] = {
                    "type": "constant",
                    "std": float(std),
                    "suspicion": 0.85
                }

            # 变异系数检测
            if mean != 0:
                cv = std / abs(mean)
                if cv < 0.05:
                    patterns[f"{ind}_low_cv"] = {
                        "type": "low_cv",
                        "cv": float(cv),
                        "suspicion": 0.75
                    }

        return {
            "status": "success",
            "has_anomaly": len(anomalies) > 0 or len(patterns) > 0,
            "anomalies": anomalies,
            "patterns": patterns
        }


class SimpleRuleReasoningAgent:
    """简化版规则推理子智能体"""

    def __init__(self):
        self.name = "规则推理子智能体"

        # GB18918-2002 一级A标准限值
        self.limits = {
            "pH": {"min": 6.0, "max": 9.0},
            "COD": {"max": 50.0},
            "TN": {"max": 15.0},
            "NH3-N": {"max": 5.0},
            "TP": {"max": 0.5},
        }

    def process(self, request):
        """处理规则推理请求"""
        anomalies = request.get("anomalies", [])
        features = request.get("features", {})
        data = request.get("data")

        logger.info(f"[RULE] 执行规则推理")

        violations = []
        suspicion_level = "low"

        # 1. 法规超标检查
        if data is not None:
            for ind, limit in self.limits.items():
                if ind in data.columns:
                    col_data = data[ind].dropna()
                    if len(col_data) > 0:
                        latest_value = col_data.iloc[-1]
                        if "max" in limit and latest_value > limit["max"]:
                            violations.append({
                                "type": "exceedance",
                                "indicator": ind,
                                "value": float(latest_value),
                                "limit": limit["max"],
                                "level": "high"
                            })
                        if "min" in limit and latest_value < limit["min"]:
                            violations.append({
                                "type": "below_limit",
                                "indicator": ind,
                                "value": float(latest_value),
                                "limit": limit["min"],
                                "level": "high"
                            })

        # 2. 异常模式判定
        patterns = request.get("patterns", {})

        # 恒定值判定（插瓶干扰）
        constant_indicators = [k.replace("_constant", "") for k, v in patterns.items()
                               if v.get("type") == "constant"]
        if len(constant_indicators) >= 2:
            violations.append({
                "type": "bottle_interference",
                "indicators": constant_indicators,
                "level": "critical",
                "evidence": f"多个指标恒定: {', '.join(constant_indicators)}",
                "legal_reference": "水污染防治法第三十九条"
            })
            suspicion_level = "high"

        # 低变异系数判定
        low_cv_indicators = [k.replace("_low_cv", "") for k, v in patterns.items()
                             if v.get("type") == "low_cv"]
        if len(low_cv_indicators) >= 2:
            violations.append({
                "type": "data_smoothing",
                "indicators": low_cv_indicators,
                "level": "medium",
                "evidence": f"数据过度平滑: {', '.join(low_cv_indicators)}",
                "legal_reference": "水污染防治法第三十九条"
            })

        # 3. 计算嫌疑等级
        if any(v.get("level") == "critical" for v in violations):
            suspicion_level = "critical"
        elif any(v.get("level") == "high" for v in violations):
            suspicion_level = "high"
        elif len(violations) > 0:
            suspicion_level = "medium"

        return {
            "status": "success",
            "has_violation": len(violations) > 0,
            "violations": violations,
            "suspicion_level": suspicion_level
        }


# ==================== 主编排器 ====================

class MainOrchestrator:
    """
    主编排器
    模拟专利架构：主智能体 → 任务编排层 → 4个子智能体协同
    """

    def __init__(self):
        """初始化编排器"""
        self.data_governance = SimpleDataGovernanceAgent()
        self.feature_analysis = SimpleFeatureAnalysisAgent()
        self.anomaly_detection = SimpleAnomalyDetectionAgent()
        self.rule_reasoning = SimpleRuleReasoningAgent()

        logger.info("[ORCHESTRATOR] 主编排器初始化完成")

    def process_realtime(self, influent_data: dict, effluent_data: dict) -> dict:
        """
        处理实时数据

        Args:
            influent_data: 进水数据
            effluent_data: 出水数据

        Returns:
            分析结果
        """
        timestamp = datetime.now().isoformat()
        logger.info("=" * 60)
        logger.info(f"[ORCHESTRATOR] 开始处理实时数据: {timestamp}")

        # 准备数据
        raw_data = pd.DataFrame([effluent_data])

        # 阶段1: 数据治理子智能体
        logger.info("[STAGE 1/4] 数据治理子智能体处理...")
        gov_result = self.data_governance.process({
            "raw_data": raw_data,
            "indicators": ["pH", "COD", "TN", "NH3-N", "TP"]
        })

        if gov_result["status"] != "success":
            return {"error": gov_result.get("error"), "status": "error"}

        # 阶段2: 特征分析子智能体
        logger.info("[STAGE 2/4] 特征分析子智能体处理...")
        feat_result = self.feature_analysis.process({
            "data": gov_result["processed_data"],
            "indicators": ["pH", "COD", "TN", "NH3-N", "TP"],
            "window": len(raw_data)
        })

        # 阶段3: 异常检测子智能体
        logger.info("[STAGE 3/4] 异常检测子智能体处理...")
        anom_result = self.anomaly_detection.process({
            "data": gov_result["processed_data"],
            "indicators": ["pH", "COD", "TN", "NH3-N", "TP"],
            "operators": ["iqr", "zscore"]
        })

        # 阶段4: 规则推理子智能体
        logger.info("[STAGE 4/4] 规则推理子智能体处理...")
        rule_result = self.rule_reasoning.process({
            "anomalies": anom_result.get("anomalies", []),
            "features": feat_result.get("features", {}),
            "patterns": anom_result.get("patterns", {}),
            "data": gov_result["processed_data"]
        })

        # 生成告警
        alerts = []
        for violation in rule_result.get("violations", []):
            alerts.append({
                "type": violation.get("type"),
                "level": violation.get("level"),
                "message": violation.get("evidence", f"检测到异常: {violation.get('type')}"),
                "timestamp": timestamp
            })

        logger.info(f"[ORCHESTRATOR] 处理完成，检测到 {len(alerts)} 个告警")
        logger.info("=" * 60)

        return {
            "timestamp": timestamp,
            "status": "success",
            "has_anomaly": anom_result.get("has_anomaly", False),
            "has_violation": rule_result.get("has_violation", False),
            "anomalies": anom_result.get("anomalies", []),
            "alerts": alerts,
            "suspicion_level": rule_result.get("suspicion_level", "low")
        }


# ==================== 测试函数 ====================

def test_normal_data():
    """测试正常数据"""
    print("\n" + "=" * 60)
    print("测试1: 正常数据")
    print("=" * 60)

    orchestrator = MainOrchestrator()

    # 正常数据
    influent = {"pH值": 7.2, "化学需氧量浓度（毫克/升）": 120}
    effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45}

    result = orchestrator.process_realtime(influent, effluent)

    print(f"结果: {result['status']}")
    print(f"异常: {result['has_anomaly']}")
    print(f"违规: {result['has_violation']}")
    print(f"嫌疑等级: {result['suspicion_level']}")

    return result


def test_constant_anomaly():
    """测试恒定值异常（插瓶干扰）"""
    print("\n" + "=" * 60)
    print("测试2: 恒定值异常（插瓶干扰）")
    print("=" * 60)

    orchestrator = MainOrchestrator()

    # 发送多条恒定数据
    for i in range(10):
        influent = {"pH值": 7.0 + i * 0.01, "化学需氧量浓度（毫克/升）": 100 + i}
        effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45}  # 恒定

        result = orchestrator.process_realtime(influent, effluent)

    print(f"结果: {result['status']}")
    print(f"异常: {result['has_anomaly']}")
    print(f"违规: {result['has_violation']}")
    print(f"嫌疑等级: {result['suspicion_level']}")

    if result['alerts']:
        print("告警:")
        for alert in result['alerts']:
            print(f"  - {alert['type']} ({alert['level']}): {alert['message']}")

    return result


def test_exceedance():
    """测试超标"""
    print("\n" + "=" * 60)
    print("测试3: 超标")
    print("=" * 60)

    orchestrator = MainOrchestrator()

    # 超标数据
    influent = {"pH值": 7.0, "化学需氧量浓度（毫克/升）": 100}
    effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 75}  # 超标

    result = orchestrator.process_realtime(influent, effluent)

    print(f"结果: {result['status']}")
    print(f"异常: {result['has_anomaly']}")
    print(f"违规: {result['has_violation']}")
    print(f"嫌疑等级: {result['suspicion_level']}")

    if result['alerts']:
        print("告警:")
        for alert in result['alerts']:
            print(f"  - {alert['type']} ({alert['level']}): {alert['message']}")

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("废水虚假排放智能监测系统 - 完整流程测试")
    print("基于专利架构：主智能体 → 任务编排层 → 4个子智能体协同")
    print("=" * 60)

    # 执行测试
    test_normal_data()
    test_constant_anomaly()
    test_exceedance()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
违规模式检测模块（专利4类违规模式）

基于专利文档：违规判定双层逻辑 - 业务层

4类违规模式：
1. 插瓶干扰：使用标准溶液模拟达标排放
2. 人工拟合：数据经过人工处理呈现异常平滑
3. 稀释排放：在排放口加清水稀释降低浓度
4. 恶意逃避：不正常运行监测设备逃避监管
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ViolationDetector:
    """
    违规模式检测器（专利4类违规模式）

    功能：基于异常检测结果，识别具体的违规行为模式

    检测的违规模式：
    1. 插瓶干扰：指标恒定且接近标准限值
    2. 人工拟合：数据过度平滑，符合数学函数特征
    3. 稀释排放：多指标同步下降且处于低位
    4. 恶意逃避：数据缺失率异常，夜间空白模式
    """

    def __init__(self):
        """初始化违规模式检测器"""
        self.name = "违规模式检测器"
        self.version = "1.0.0"

        # 各级排放标准限值（GB 18918-2002）
        self.standard_limits = {
            "COD": 50,        # 一级A标
            "TN": 15,         # 一级A标
            "NH3-N": 5,       # 一级A标（水温>12℃）
            "TP": 0.5,        # 一级A标
            "pH": (6, 9),     # 一级A标（范围）
            "SS": 10          # 一级A标
        }

        # 专利参数配置
        self.params = {
            "bottle_interference": {
                "proximity_ratio": 0.8,      # 接近标准限值的比例
                "min_constant_duration": 2   # 最小恒定时长（小时）
            },
            "artificial_fitting": {
                "smoothness_threshold": 0.3,  # 平滑度阈值
                "r_squared_threshold": 0.95   # 数学拟合R²阈值
            },
            "dilution_discharge": {
                "declining_ratio": 0.6,       # 下降指标比例阈值
                "low_level_ratio": 0.5        # 低位指标比例阈值
            },
            "malicious_evasion": {
                "missing_rate_threshold": 0.2,  # 缺失率阈值
                "night_day_ratio": 2            # 夜间/日间缺失率比值
            }
        }

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def detect_violations(self, anomalies: List[Dict],
                         data: pd.DataFrame) -> Dict[str, Any]:
        """
        检测4类违规模式

        Args:
            anomalies: 异常列表
            data: 原始监测数据

        Returns:
            违规检测结果
        """
        logger.info(f"[VIOLATION] 开始检测违规模式")

        violations = []

        # 1. 检测插瓶干扰
        bottle_violations = self._detect_bottle_interference(anomalies, data)
        violations.extend(bottle_violations)

        # 2. 检测人工拟合
        fitting_violations = self._detect_artificial_fitting(anomalies, data)
        violations.extend(fitting_violations)

        # 3. 检测稀释排放
        dilution_violations = self._detect_dilution_discharge(anomalies, data)
        violations.extend(dilution_violations)

        # 4. 检测恶意逃避
        evasion_violations = self._detect_malicious_evasion(anomalies, data)
        violations.extend(evasion_violations)

        # 计算嫌疑等级
        suspicion_level = self._calculate_suspicion_level(violations)

        # 统计违规类型
        violation_types = list(set(v["type"] for v in violations))

        result = {
            "violations": violations,
            "violation_types": violation_types,
            "violation_count": len(violations),
            "suspicion_level": suspicion_level,
            "detection_time": datetime.now().isoformat()
        }

        logger.info(f"[VIOLATION] 检测完成: {len(violations)}处违规, 嫌疑等级={suspicion_level}")

        return result

    def _detect_bottle_interference(self, anomalies: List[Dict],
                                    data: pd.DataFrame) -> List[Dict]:
        """
        检测插瓶干扰

        特征：
        - 单个或多个指标长时间恒定
        - 恒定值接近标准限值（如COD=45mg/L接近一级A标50mg/L）
        - 其他指标保持正常波动

        Returns:
            插瓶干扰违规列表
        """
        violations = []

        # 找出恒定异常
        constant_anomalies = [
            a for a in anomalies
            if a.get("pattern") == "constant" or a.get("pattern") == "恒定异常"
        ]

        for anomaly in constant_anomalies:
            indicator = anomaly["indicator"]

            # 检查恒定值是否接近标准限值
            if indicator in data.columns:
                index = anomaly.get("index", 0)
                if index < len(data):
                    constant_value = data[indicator].iloc[index]

                    # 获取标准限值
                    limit = self.standard_limits.get(indicator, None)

                    if limit is not None:
                        # 判断是否接近限值
                        if isinstance(limit, tuple):
                            # pH范围判断
                            if limit[0] * 1.1 <= constant_value <= limit[1] * 0.9:
                                violations.append({
                                    "type": "bottle_interference",
                                    "indicator": indicator,
                                    "constant_value": constant_value,
                                    "standard_limit": limit,
                                    "description": f"{indicator}长时间恒定在{constant_value}，接近标准限值{limit}，疑似插瓶干扰",
                                    "severity": "high",
                                    "confidence": 0.9,
                                    "evidence": f"恒定值={constant_value:.2f}, 标准限值={limit}"
                                })
                        else:
                            # 数值判断（在限值的80%-100%范围内）
                            if limit * self.params["bottle_interference"]["proximity_ratio"] <= constant_value <= limit * 1.0:
                                violations.append({
                                    "type": "bottle_interference",
                                    "indicator": indicator,
                                    "constant_value": constant_value,
                                    "standard_limit": limit,
                                    "description": f"{indicator}长时间恒定在{constant_value:.2f}mg/L，接近一级A标{limit}mg/L，疑似插瓶干扰",
                                    "severity": "high",
                                    "confidence": 0.9,
                                    "evidence": f"恒定值={constant_value:.2f}mg/L, 标准限值={limit}mg/L"
                                })

        # 多指标同时恒定的情况（更高嫌疑）
        constant_indicators = set(
            a["indicator"] for a in constant_anomalies
            if a.get("pattern") == "constant" or a.get("pattern") == "恒定异常"
        )
        if len(constant_indicators) >= 2:
            violations.append({
                "type": "bottle_interference",
                "indicators": list(constant_indicators),
                "description": f"{len(constant_indicators)}个指标同时恒定，高度疑似插瓶干扰",
                "severity": "critical",
                "confidence": 0.95,
                "evidence": f"恒定指标数量={len(constant_indicators)}"
            })

        return violations

    def _detect_artificial_fitting(self, anomalies: List[Dict],
                                  data: pd.DataFrame) -> List[Dict]:
        """
        检测人工拟合

        特征：
        - 数据变化过于平滑，标准差异常小
        - 变化模式呈现数学函数特征（如线性、指数）
        - 缺乏真实数据的随机波动

        Returns:
            人工拟合违规列表
        """
        violations = []

        for indicator in data.columns:
            if indicator in ["times", "timestamp", "time"]:
                continue

            series = data[indicator].dropna()

            if len(series) < 20:
                continue

            # 1. 计算平滑度指标
            # 差分标准差 / 序列标准差
            diff_std = series.diff().std()
            series_std = series.std()

            if series_std < 1e-10:
                continue

            smoothness = diff_std / series_std

            # 过度平滑判定
            if smoothness < self.params["artificial_fitting"]["smoothness_threshold"]:
                # 2. 检查是否符合数学函数模式
                is_math_pattern = self._is_mathematical_pattern(series)

                if is_math_pattern:
                    violations.append({
                        "type": "artificial_fitting",
                        "indicator": indicator,
                        "smoothness": smoothness,
                        "description": f"{indicator}数据异常平滑（平滑度={smoothness:.3f}），呈现人工拟合特征",
                        "severity": "medium",
                        "confidence": 0.85,
                        "evidence": f"平滑度={smoothness:.3f} < {self.params['artificial_fitting']['smoothness_threshold']}"
                    })

        return violations

    def _is_mathematical_pattern(self, series: pd.Series) -> bool:
        """
        检查数据是否符合数学函数模式

        使用线性回归和多项式拟合检查R²值
        """
        try:
            x = np.arange(len(series))

            # 线性拟合
            z1 = np.polyfit(x, series, 1)
            p1 = np.poly1d(z1)
            y_pred1 = p1(x)

            # 计算R²
            ss_res = ((series - y_pred1) ** 2).sum()
            ss_tot = ((series - series.mean()) ** 2).sum()

            if ss_tot < 1e-10:
                return False

            r_squared = 1 - (ss_res / ss_tot)

            # 如果R²很高，说明符合数学函数
            return r_squared > self.params["artificial_fitting"]["r_squared_threshold"]

        except Exception as e:
            logger.warning(f"[VIOLATION] 数学模式检测失败: {e}")
            return False

    def _detect_dilution_discharge(self, anomalies: List[Dict],
                                  data: pd.DataFrame) -> List[Dict]:
        """
        检测稀释排放

        特征：
        - 多指标同步下降
        - 浓度处于异常低位
        - 水量数据异常增加（如果有）

        Returns:
            稀释排放违规列表
        """
        violations = []

        # 获取数值型指标
        indicators = [
            col for col in data.columns
            if col not in ["times", "timestamp", "time"] and
            pd.api.types.is_numeric_dtype(data[col])
        ]

        if len(indicators) < 2:
            return violations

        # 计算各指标的趋势
        trends = {}
        for indicator in indicators:
            series = data[indicator].dropna()
            if len(series) > 10:
                # 简单线性回归计算趋势
                x = np.arange(len(series))
                z = np.polyfit(x, series, 1)
                trends[indicator] = z[0]  # 斜率

        # 统计下降趋势的指标数量
        declining = sum(
            1 for slope in trends.values()
            if slope < -0.1  # 负斜率表示下降
        )

        # 如果多数指标都在下降
        if declining >= len(indicators) * self.params["dilution_discharge"]["declining_ratio"]:
            # 检查是否处于异常低位
            low_count = 0
            for indicator in indicators:
                series = data[indicator].dropna()
                if len(series) > 10:
                    recent_value = series.iloc[-10:].mean()
                    historical_median = series.median()

                    if historical_median > 0:
                        ratio = recent_value / historical_median
                        if ratio < 0.5:  # 低于历史中位数50%
                            low_count += 1

            if low_count >= len(indicators) * self.params["dilution_discharge"]["low_level_ratio"]:
                violations.append({
                    "type": "dilution_discharge",
                    "indicators": indicators,
                    "declining_count": declining,
                    "low_count": low_count,
                    "description": f"{declining}个指标同步下降且{low_count}个处于低位，疑似稀释排放",
                    "severity": "high",
                    "confidence": 0.8,
                    "evidence": f"下降指标={declining}/{len(indicators)}, 低位指标={low_count}/{len(indicators)}"
                })

        return violations

    def _detect_malicious_evasion(self, anomalies: List[Dict],
                                 data: pd.DataFrame) -> List[Dict]:
        """
        检测恶意逃避

        特征：
        - 数据缺失或无效值异常增多
        - 监测设备离线时间异常
        - 特定时段数据空白（如夜间）

        Returns:
            恶意逃避违规列表
        """
        violations = []

        # 1. 检查数据缺失率
        for indicator in data.columns:
            if indicator in ["times", "timestamp", "time"]:
                continue

            series = data[indicator]
            missing_count = series.isna().sum()
            missing_rate = missing_count / len(series) if len(series) > 0 else 0

            # 缺失率异常高
            if missing_rate > self.params["malicious_evasion"]["missing_rate_threshold"]:
                violations.append({
                    "type": "malicious_evasion",
                    "indicator": indicator,
                    "missing_rate": missing_rate,
                    "description": f"{indicator}数据缺失率{missing_rate*100:.1f}%，疑似设备异常或恶意逃避",
                    "severity": "medium",
                    "confidence": 0.75,
                    "evidence": f"缺失率={missing_rate*100:.1f}%"
                })

        # 2. 检查特定时段空白（如夜间）
        time_col = None
        for col in ["times", "timestamp", "time"]:
            if col in data.columns:
                time_col = col
                break

        if time_col is not None:
            try:
                # 提取小时
                data_copy = data.copy()
                data_copy["hour"] = pd.to_datetime(data_copy[time_col]).dt.hour

                # 检查夜间数据（22:00-6:00）
                night_mask = (data_copy["hour"] >= 22) | (data_copy["hour"] <= 6)
                day_mask = (data_copy["hour"] > 6) & (data_copy["hour"] < 22)

                night_data = data_copy[night_mask]
                day_data = data_copy[day_mask]

                if len(night_data) > 0 and len(day_data) > 0:
                    # 计算夜间和日间的缺失率
                    night_missing = night_data.isna().sum().sum() / (len(night_data) * len(data.columns))
                    day_missing = day_data.isna().sum().sum() / (len(day_data) * len(data.columns))

                    # 夜间缺失率明显高于日间
                    if night_missing > day_missing * self.params["malicious_evasion"]["night_day_ratio"] and night_missing > 0.1:
                        violations.append({
                            "type": "malicious_evasion",
                            "description": f"夜间数据缺失率({night_missing*100:.1f}%)明显高于日间({day_missing*100:.1f}%)，疑似夜间逃避监测",
                            "severity": "high",
                            "confidence": 0.85,
                            "evidence": f"夜间缺失率={night_missing*100:.1f}%, 日间缺失率={day_missing*100:.1f}%"
                        })
            except Exception as e:
                logger.warning(f"[VIOLATION] 夜间空白检测失败: {e}")

        return violations

    def _calculate_suspicion_level(self, violations: List[Dict]) -> str:
        """
        计算嫌疑等级

        基于违规数量和严重程度

        Returns:
            嫌疑等级：critical, high, medium, low
        """
        if not violations:
            return "low"

        # 统计各严重程度的数量
        severity_counts = {}
        for v in violations:
            severity = v.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # 判定等级
        if severity_counts.get("critical", 0) > 0:
            return "critical"
        elif severity_counts.get("high", 0) >= 2:
            return "critical"
        elif severity_counts.get("high", 0) > 0:
            return "high"
        elif severity_counts.get("medium", 0) >= 2:
            return "medium"
        else:
            return "low"


# 命令行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    detector = ViolationDetector()

    print("=" * 80)
    print("违规模式检测器测试")
    print("=" * 80)

    # 创建测试数据
    test_data = pd.DataFrame({
        "times": pd.date_range("2026-01-01", periods=100, freq="H"),
        "COD": [45] * 50 + [50, 55, 60, 58, 62, 59, 61, 63, 60, 57] + [45] * 40,
        "pH": [7.5] * 100,
        "TN": [12] * 100
    })

    # 模拟异常
    test_anomalies = [
        {"indicator": "COD", "pattern": "constant", "index": 25, "score": 0.9},
        {"indicator": "pH", "pattern": "constant", "index": 50, "score": 0.95}
    ]

    print("\n测试场景: 插瓶干扰（COD和pH恒定）")

    result = detector.detect_violations(test_anomalies, test_data)

    print(f"\n检测结果:")
    print(f"  违规数量: {result['violation_count']}")
    print(f"  违规类型: {result['violation_types']}")
    print(f"  嫌疑等级: {result['suspicion_level']}")

    for v in result["violations"]:
        print(f"\n  违规详情:")
        print(f"    类型: {v['type']}")
        print(f"    描述: {v['description']}")
        print(f"    严重程度: {v['severity']}")
        print(f"    置信度: {v['confidence']}")

    print("\n" + "=" * 80)


# 入口函数 - 执行控制模块调用
def main(features: Optional[Dict[str, Any]] = None,
         task: Optional[Dict[str, Any]] = None,
         data: Optional[Dict[str, Any]] = None,
         influent: Optional[Dict[str, Any]] = None,
         effluent: Optional[Dict[str, Any]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 违规检测

    Args:
        features: 特征数据
        task: 任务字典
        data: 数据字典
        influent: 进水数据
        effluent: 出水数据
        **kwargs: 其他参数

    Returns:
        违规检测结果
    """
    import pandas as pd
    from datetime import datetime

    # 合并数据
    all_data = {}
    if features:
        all_data.update(features)
    if data:
        all_data.update(data)
    if influent:
        all_data["influent"] = influent
    if effluent:
        all_data["effluent"] = effluent
    all_data.update(kwargs)

    # 创建检测器
    detector = ViolationDetector()

    # 检查是否有时间戳问题（常见违规）
    violations = []
    suspicion_level = "low"

    # 检查时间戳逻辑
    influent_time = all_data.get("influent_time") or all_data.get("timestamp_check", {}).get("influent_date")
    effluent_time = all_data.get("effluent_time") or all_data.get("timestamp_check", {}).get("effluent_date")

    if influent_time and effluent_time:
        # 解析时间
        try:
            influent_dt = datetime.strptime(str(influent_time).split()[0], "%Y-%m-%d") if isinstance(influent_time, str) else influent_time
            effluent_dt = datetime.strptime(str(effluent_time).split()[0], "%Y-%m-%d") if isinstance(effluent_time, str) else effluent_time

            # 出水时间早于进水时间是严重违规
            if effluent_dt < influent_dt:
                violations.append({
                    "type": "DATA_FABRICATION",
                    "sub_type": "TIMESTAMP_MANIPULATION",
                    "description": f"出水时间({effluent_time})早于进水时间({influent_time})，违背工艺逻辑",
                    "severity": "critical",
                    "confidence": 0.98,
                    "evidence": f"进水={influent_time}, 出水={effluent_time}"
                })
                suspicion_level = "critical"
        except:
            pass

    # 检查HRT约束
    hrt_constraint = all_data.get("hrt_constraint_hours") or all_data.get("process_hrt")
    timestamp_delta = all_data.get("timestamp_delta_days") or all_data.get("timestamp_delta")

    if hrt_constraint and timestamp_delta:
        if timestamp_delta * 24 > hrt_constraint:
            violations.append({
                "type": "DATA_FABRICATION",
                "sub_type": "HRT_VIOLATION",
                "description": f"时间间隔({timestamp_delta}天)超出HRT约束({hrt_constraint}小时)，违背工艺逻辑",
                "severity": "critical",
                "confidence": 0.95,
                "evidence": f"时间间隔={timestamp_delta}天, HRT={hrt_constraint}小时"
            })
            if suspicion_level != "critical":
                suspicion_level = "high"

    # 检查去除率异常
    removal_rates = all_data.get("removal_rates") or all_data.get("observed_removal_rates") or {}
    if removal_rates:
        for indicator, rate in removal_rates.items():
            if isinstance(rate, str):
                rate = float(rate.rstrip("%"))
            if rate > 100:  # 去除率超过100%是异常
                violations.append({
                    "type": "ANOMALY",
                    "sub_type": "INVALID_REMOVAL_RATE",
                    "description": f"{indicator}去除率({rate}%)超过100%，数据异常",
                    "severity": "high",
                    "confidence": 0.9,
                    "evidence": f"{indicator}去除率={rate}%"
                })
            elif rate < 0:  # 去除率为负是异常
                violations.append({
                    "type": "ANOMALY",
                    "sub_type": "NEGATIVE_REMOVAL_RATE",
                    "description": f"{indicator}去除率({rate}%)为负值，出水浓度高于进水",
                    "severity": "high",
                    "confidence": 0.95,
                    "evidence": f"{indicator}去除率={rate}%"
                })

    return {
        "status": "success",
        "violations": violations,
        "violation_count": len(violations),
        "suspicion_level": suspicion_level,
        "violation_details": violations[0] if violations else None,
        "detection_time": datetime.now().isoformat()
    }


def detect(features: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """检测函数别名"""
    return main(features=features, **kwargs)

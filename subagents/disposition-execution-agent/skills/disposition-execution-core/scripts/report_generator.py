# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/report_generator.py
"""
报告生成模块 - 生成预警、汇总和趋势报告
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlertReport:
    """预警报告"""
    report_id: str
    generated_at: str
    alert_level: str
    violation_type: str
    confidence: float

    # 报告内容
    data_traceback: Dict[str, Any]
    inspection_points: List[Dict[str, Any]]
    legal_references: List[str]
    recommended_actions: List[str]

    # 趋势图表数据（可选）
    trend_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "alert_level": self.alert_level,
            "violation_type": self.violation_type,
            "confidence": self.confidence,
            "data_traceback": self.data_traceback,
            "inspection_points": self.inspection_points,
            "legal_references": self.legal_references,
            "recommended_actions": self.recommended_actions,
            "trend_data": self.trend_data
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""# 预警报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 预警级别: {self.alert_level}
- 违规类型: {self.violation_type}
- 置信度: {self.confidence:.1%}

## 数据溯源
{self._format_dict(self.data_traceback)}

## 现场核查要点
{self._format_list(self.inspection_points)}

## 法规条款
{self._format_list(self.legal_references)}

## 处置建议
{self._format_list(self.recommended_actions)}
"""
        return md

    @staticmethod
    def _format_dict(d: Dict) -> str:
        if not d:
            return "无"
        return "\n".join([f"- {k}: {v}" for k, v in d.items()])

    @staticmethod
    def _format_list(lst: List) -> str:
        if not lst:
            return "无"
        return "\n".join([f"- {item}" for item in lst])


@dataclass
class SummaryReport:
    """汇总报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    total_alerts: int
    by_level: Dict[str, int]
    by_type: Dict[str, int]
    top_enterprises: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "time_range": self.time_range,
            "total_alerts": self.total_alerts,
            "by_level": self.by_level,
            "by_type": self.by_type,
            "top_enterprises": self.top_enterprises
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""# 汇总报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 统计时间: {self.time_range[0]} 至 {self.time_range[1]}
- 总预警数: {self.total_alerts}

## 按级别统计
{self._format_dict(self.by_level)}

## 按类型统计
{self._format_dict(self.by_type)}

## 重点企业
{self._format_enterprises()}
"""
        return md

    @staticmethod
    def _format_dict(d: Dict) -> str:
        if not d:
            return "无"
        return "\n".join([f"- {k}: {v}" for k, v in d.items()])

    def _format_enterprises(self) -> str:
        if not self.top_enterprises:
            return "无"
        lines = []
        for i, ent in enumerate(self.top_enterprises, 1):
            name = ent.get("name", "未知")
            count = ent.get("alert_count", 0)
            lines.append(f"{i}. {name}: {count} 次")
        return "\n".join(lines)


@dataclass
class TrendReport:
    """趋势分析报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    indicators: List[str]
    trend_data: Dict[str, List[Dict[str, Any]]]
    analysis: str
    anomalies: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "time_range": self.time_range,
            "indicators": self.indicators,
            "trend_data": self.trend_data,
            "analysis": self.analysis,
            "anomalies": self.anomalies
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        indicators_str = ", ".join(self.indicators)
        md = f"""# 趋势分析报告

## 基本信息
- 报告编号: {self.report_id}
- 生成时间: {self.generated_at}
- 分析时间: {self.time_range[0]} 至 {self.time_range[1]}
- 分析指标: {indicators_str}

## 趋势分析
{self.analysis}

## 异常事件
{self._format_anomalies()}
"""
        return md

    def _format_anomalies(self) -> str:
        if not self.anomalies:
            return "无异常事件"
        lines = []
        for i, anom in enumerate(self.anomalies, 1):
            time_str = anom.get("time", "未知时间")
            desc = anom.get("description", "无描述")
            lines.append(f"{i}. {time_str}: {desc}")
        return "\n".join(lines)


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "/shared/outputs/reports/"):
        self.output_dir = output_dir

    def generate_alert_report(
        self,
        work_order: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AlertReport:
        """生成单个预警的详细报告

        Args:
            work_order: 工单数据
            context: 上下文信息（历史数据、趋势等）

        Returns:
            AlertReport: 预警报告
        """
        if context is None:
            context = {}

        # 生成报告ID
        report_id = f"ALERT-{work_order.get('id', 'unknown')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 从工单中提取数据
        data_traceback = work_order.get("data_traceback", {})
        inspection_points = work_order.get("inspection_points", [])
        legal_references = work_order.get("legal_references", [])
        recommended_actions = work_order.get("recommended_actions", [])

        # 如果工单中没有趋势数据，可以从 context 中获取
        trend_data = context.get("trend_data")

        report = AlertReport(
            report_id=report_id,
            generated_at=datetime.now().isoformat(),
            alert_level=work_order.get("alert_level", "unknown"),
            violation_type=work_order.get("violation_type", "unknown"),
            confidence=work_order.get("confidence", 0.0),
            data_traceback=data_traceback,
            inspection_points=inspection_points,
            legal_references=legal_references,
            recommended_actions=recommended_actions,
            trend_data=trend_data
        )

        logger.info(f"Generated alert report: {report_id}")
        return report

    def generate_summary_report(
        self,
        work_orders: List[Dict[str, Any]],
        time_range: Tuple[str, str]
    ) -> SummaryReport:
        """生成汇总报告

        Args:
            work_orders: 工单列表
            time_range: 时间范围

        Returns:
            SummaryReport: 汇总报告
        """
        # 统计按级别的数量
        by_level = {"general": 0, "moderate": 0, "serious": 0}
        by_type = {}

        for wo in work_orders:
            level = wo.get("alert_level", "unknown")
            if level in by_level:
                by_level[level] += 1

            vtype = wo.get("violation_type", "unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1

        # 统计重点企业（如果有企业信息）
        top_enterprises = []
        # TODO: 根据企业分组统计

        report = SummaryReport(
            report_id=f"SUMMARY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            time_range=time_range,
            total_alerts=len(work_orders),
            by_level=by_level,
            by_type=by_type,
            top_enterprises=top_enterprises
        )

        logger.info(f"Generated summary report: {report.report_id}")
        return report

    def save_report(self, report: Union[AlertReport, SummaryReport, TrendReport]) -> str:
        """保存报告到文件

        Args:
            report: 报告对象

        Returns:
            str: 文件路径
        """
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 确定文件名
            report_id = report.report_id.replace("/", "-")
            filename = f"{report_id}.json"
            file_path = output_path / filename

            # 保存 JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                if hasattr(report, 'to_dict'):
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                else:
                    json.dump(report.__dict__, f, ensure_ascii=False, indent=2)

            # 同时保存 Markdown
            md_filename = f"{report_id}.md"
            md_file_path = output_path / md_filename
            with open(md_file_path, 'w', encoding='utf-8') as f:
                if hasattr(report, 'to_markdown'):
                    f.write(report.to_markdown())

            logger.info(f"Report saved to {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise

    def generate_trend_report(
        self,
        historical_data: List[Dict[str, Any]],
        indicators: List[str],
        time_range: Tuple[str, str]
    ) -> TrendReport:
        """生成趋势分析报告

        Args:
            historical_data: 历史数据列表
            indicators: 需要分析的指标列表
            time_range: 时间范围

        Returns:
            TrendReport: 趋势报告
        """
        # 提取趋势数据
        trend_data = {}
        anomalies = []

        for indicator in indicators:
            values = []
            for record in historical_data:
                value = record.get(indicator)
                if value is not None:
                    values.append({
                        "time": record.get("监测时间", ""),
                        "value": value
                    })

            trend_data[indicator] = values

            # 简单异常检测
            if len(values) > 1:
                numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]
                if numeric_values:
                    avg = sum(numeric_values) / len(numeric_values)
                    std = (sum((x - avg) ** 2 for x in numeric_values) / len(numeric_values)) ** 0.5

                    for v in values:
                        val = v["value"]
                        if isinstance(val, (int, float)) and abs(val - avg) > 2 * std:
                            anomalies.append({
                                "time": v["time"],
                                "indicator": indicator,
                                "value": val,
                                "description": f"{indicator} 异常: {val} (均值: {avg:.2f}, 标准差: {std:.2f})"
                            })

        # 生成分析文本
        analysis_lines = []
        for indicator in indicators:
            if indicator in trend_data and len(trend_data[indicator]) > 0:
                values_count = len(trend_data[indicator])
                analysis_lines.append(f"- {indicator}: 共 {values_count} 个数据点")

                # 简单趋势判断
                if values_count >= 2:
                    first_val = trend_data[indicator][0].get("value")
                    last_val = trend_data[indicator][-1].get("value")
                    if isinstance(first_val, (int, float)) and isinstance(last_val, (int, float)):
                        if last_val > first_val * 1.2:
                            analysis_lines.append(f"  趋势: 上升")
                        elif last_val < first_val * 0.8:
                            analysis_lines.append(f"  趋势: 下降")
                        else:
                            analysis_lines.append(f"  趋势: 平稳")

        analysis = "\n".join(analysis_lines) if analysis_lines else "无趋势数据"

        report = TrendReport(
            report_id=f"TREND-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            time_range=time_range,
            indicators=indicators,
            trend_data=trend_data,
            analysis=analysis,
            anomalies=anomalies
        )

        logger.info(f"Generated trend report: {report.report_id}")
        return report

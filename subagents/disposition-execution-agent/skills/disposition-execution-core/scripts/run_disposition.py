#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警处置入口脚本 - 预警分级和处置执行

功能：
1. 读取异常检测结果和违规判定结果
2. 执行融合共识算法
3. 进行预警分级
4. 生成处置工单
5. 生成预警报告

输出：disposition_result.json

使用方法:
    python run_disposition.py
    python run_disposition.py --session-dir <path>
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 添加当前目录到 Python 路径
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 导入模块
from consensus_engine import ConsensusEngine, FusionResult
from alert_classifier import AlertClassifier
from work_order_generator import WorkOrderGenerator
from report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def find_project_root() -> Path:
    """查找项目根目录(标志:同时含 shared/ 和 backend/)。"""
    current = Path(__file__).resolve()
    for _ in range(6):
        if (current / "shared").exists() and (current / "backend").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[5]


def load_anomaly_result(session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """加载异常检测结果"""
    search_paths = []

    if session_dir and session_dir.exists():
        search_paths.append(session_dir / "anomaly_result.json")

    # 默认路径
    project_root = find_project_root()
    search_paths.append(project_root / "subagents" / "anomaly-detection-agent" / "anomaly_result.json")

    for path in search_paths:
        if path.exists():
            logger.info(f"[LOAD] 从 {path} 加载异常检测结果")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[LOAD] 加载失败 {path}: {e}")

    logger.error("[LOAD] 未能找到异常检测结果文件")
    return None


def load_violation_result(session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """加载违规判定结果"""
    search_paths = []

    if session_dir and session_dir.exists():
        search_paths.append(session_dir / "rule_reasoning_result.json")

    # 默认路径
    project_root = find_project_root()
    search_paths.append(project_root / "subagents" / "rule-reasoning-agent" / "rule_reasoning_result.json")

    for path in search_paths:
        if path.exists():
            logger.info(f"[LOAD] 从 {path} 加载违规判定结果")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[LOAD] 加载失败 {path}: {e}")

    logger.warning("[LOAD] 未能找到违规判定结果文件，将使用默认值")
    return None


def extract_data_context(anomaly_result: Dict[str, Any], violation_result: Dict[str, Any]) -> Dict[str, Any]:
    """提取数据上下文"""
    context = {}

    # 从异常结果中提取
    if anomaly_result and "result" in anomaly_result:
        anomalies = anomaly_result["result"].get("anomalies", [])
        if anomalies:
            # 提取时间范围
            timestamps = [a.get("timestamp", "") for a in anomalies if a.get("timestamp")]
            if timestamps:
                context["anomaly_time_range"] = [min(timestamps), max(timestamps)]

            # 提取受影响指标
            indicators = list(set([a.get("indicator", "") for a in anomalies if a.get("indicator")]))
            context["anomaly_indicators"] = indicators

    # 从违规结果中提取
    if violation_result and "result" in violation_result:
        context["violation_type"] = violation_result["result"].get("violation_type_names", ["未知"])
        context["suspicion_level"] = violation_result["result"].get("suspicion_level", "unknown")

    return context


def map_alert_level_to_chinese(alert_level: str) -> str:
    """将预警级别映射为中文"""
    mapping = {
        "general": "一般（黄色）",
        "moderate": "较重（橙色）",
        "serious": "严重（红色）"
    }
    return mapping.get(alert_level, alert_level)


def map_action_to_chinese(action: str) -> str:
    """将处置行动映射为中文"""
    mapping = {
        "monitor": "持续监控",
        "investigate": "现场核查",
        "immediate_investigation": "立即调查取证"
    }
    return mapping.get(action, action)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='预警分级和处置执行')
    parser.add_argument('--session-dir', type=str, help='会话目录路径')

    args = parser.parse_args()

    task_id = f"disposition_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("=" * 60)
    logger.info("预警处置任务启动")
    logger.info("=" * 60)

    try:
        # 1. 确定路径
        session_dir = None
        if args.session_dir:
            session_dir = Path(args.session_dir)
        else:
            session_dir = Path(os.environ.get('SESSION_DIR',
                                   str(find_project_root() / "sessions" / f"session_{task_id}")))
            session_dir.mkdir(parents=True, exist_ok=True)

        # 2. 加载输入数据
        logger.info("[STEP 1/5] 加载输入数据")

        anomaly_result = load_anomaly_result(session_dir)
        if not anomaly_result or anomaly_result.get("status") != "completed":
            logger.warning("[LOAD] 异常检测结果无效或未完成")
            anomaly_result = None

        violation_result = load_violation_result(session_dir)
        if not violation_result or violation_result.get("status") != "completed":
            logger.warning("[LOAD] 违规判定结果无效或未完成")
            violation_result = None

        if not anomaly_result and not violation_result:
            raise ValueError("至少需要异常检测结果或违规判定结果之一")

        # 3. 提取数据上下文
        logger.info("[STEP 2/5] 提取数据上下文")
        data_context = extract_data_context(anomaly_result, violation_result)

        # 4. 初始化模块
        logger.info("[STEP 3/5] 初始化模块")

        consensus_engine = ConsensusEngine()
        alert_classifier = AlertClassifier(consensus_engine)
        work_order_generator = WorkOrderGenerator()
        report_generator = ReportGenerator()

        # 5. 执行融合共识
        logger.info("[STEP 4/5] 执行融合共识")

        # 提取置信度
        anomaly_confidence = 0.0
        violation_confidence = 0.0

        if anomaly_result and "result" in anomaly_result:
            # 从异常结果中提取最大置信度
            anomalies = anomaly_result["result"].get("anomalies", [])
            if anomalies:
                anomaly_confidence = max([a.get("score", 0.0) for a in anomalies]) / 3.0  # 归一化

        if violation_result and "result" in violation_result:
            violation_confidence = violation_result["result"].get("confidence", 0.0)

        # 执行融合
        fusion_result = consensus_engine.fuse_results(
            {"confidence": anomaly_confidence},
            {"confidence": violation_confidence}
        )

        # 6. 预警分级
        logger.info("[STEP 5/5] 预警分级和工单生成")

        # 提取违规类型
        violation_type = "未知"
        if violation_result and "result" in violation_result:
            violation_types = violation_result["result"].get("violation_type_names", [])
            if violation_types:
                violation_type = violation_types[0]

        # 预警分类
        alert_info = alert_classifier.classify_alert(
            anomaly_result or {},
            violation_result or {}
        )

        # 生成工单
        work_order = work_order_generator.generate_work_order(
            alert_info,
            data_context
        )

        # 生成预警报告
        alert_report = report_generator.generate_alert_report(work_order, data_context)

        # 7. 生成输出
        # 预警级别中文映射
        alert_level_cn = map_alert_level_to_chinese(alert_info["level"])
        action_cn = map_action_to_chinese(alert_info["action"])

        output = {
            "task_id": task_id,
            "status": "completed",
            "result": {
                # 预警信息
                "alert": {
                    "level": alert_info["level"],
                    "level_cn": alert_level_cn,
                    "confidence": alert_info["fused_confidence"],
                    "action": alert_info["action"],
                    "action_cn": action_cn,
                    "reasoning": alert_info.get("reasoning", "")
                },

                # 违规信息
                "violation_type": violation_type,
                "violation_types": data_context.get("violation_type", ["未知"]),
                "suspicion_level": data_context.get("suspicion_level", "unknown"),

                # 工单信息
                "work_order": work_order,

                # 报告信息
                "report": alert_report.to_dict(),

                # 融合信息
                "fusion": {
                    "anomaly_confidence": round(fusion_result.anomaly_confidence, 3),
                    "violation_confidence": round(fusion_result.violation_confidence, 3),
                    "fused_confidence": round(fusion_result.fused_confidence, 3),
                    "adaptive_weights": fusion_result.adaptive_weights
                }
            },
            "metadata": {
                "subagent": "disposition-execution-agent",
                "timestamp": datetime.now().isoformat(),
                "anomaly_task_id": anomaly_result.get("task_id") if anomaly_result else None,
                "violation_task_id": violation_result.get("task_id") if violation_result else None
            }
        }

        # 8. 保存结果
        output_file = session_dir / "disposition_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 打印摘要
        print(f"\n=== 预警处置完成 ===")
        alert = output["result"]["alert"]
        print(f"预警级别: {alert['level_cn']}")
        print(f"融合置信度: {alert['confidence']:.1%}")
        print(f"处置行动: {alert['action_cn']}")
        print(f"违规类型: {', '.join(output['result']['violation_types'])}")
        print(f"工单编号: {work_order['id']}")
        print(f"报告编号: {alert_report.report_id}")
        print(f"结果已保存到: {output_file}")

        logger.info(f"任务完成：{task_id}")

    except Exception as e:
        logger.error(f"任务失败：{e}", exc_info=True)
        output = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": str(e)},
            "metadata": {
                "subagent": "disposition-execution-agent",
                "timestamp": datetime.now().isoformat()
            }
        }

        # 保存失败结果
        session_dir = Path(args.session_dir) if args.session_dir else Path(__file__).resolve().parents[3]
        output_file = session_dir / "disposition_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"=== 预警处置失败 ===")
        print(f"错误: {str(e)}")
        print(f"结果已保存到: {output_file}")

        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())

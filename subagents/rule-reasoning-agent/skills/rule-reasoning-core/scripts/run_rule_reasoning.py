#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则推理入口脚本 - 违规判定和规则推理

功能：
1. 读取异常检测结果
2. 执行法规规则匹配
3. 执行工艺机理校验
4. 执行专家经验推理
5. 生成违规判定结论

输出：rule_reasoning_result.json

使用方法:
    python run_rule_reasoning.py
    python run_rule_reasoning.py --anomaly-result <path>
    python run_rule_reasoning.py --session-dir <path>
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

# 添加当前目录到 Python 路径
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 导入模块
from regulation_matcher import RegulationMatcher
from expert_reasoner import ExpertReasoner
from process_validator import ProcessValidator

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
    # 兜底:脚本在 subagents/.../scripts/,parents[5] = 项目根
    return Path(__file__).resolve().parents[5]


def load_anomaly_result(anomaly_path: Optional[Path] = None,
                       session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载异常检测结果

    优先级：
    1. 指定的 anomaly_path
    2. session_dir/anomaly_result.json
    3. 默认路径
    """
    # 确定查找路径
    search_paths = []

    if anomaly_path and anomaly_path.exists():
        search_paths.append(anomaly_path)

    if session_dir and session_dir.exists():
        search_paths.append(session_dir / "anomaly_result.json")

    # 默认路径（相对于项目根目录）
    project_root = find_project_root()
    search_paths.extend([
        project_root / "subagents" / "anomaly-detection-agent" / "anomaly_result.json",
    ])

    # 尝试加载
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


def load_data(session_dir: Optional[Path] = None) -> Dict[str, Any]:
    """加载原始数据（用于工艺机理校验）"""
    # 尝试从 session_dir 加载
    if session_dir and session_dir.exists():
        data_path = session_dir / "data_result.json"
        if data_path.exists():
            logger.info(f"[LOAD] 从 {data_path} 加载原始数据")
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    data_result = json.load(f)
                    return data_result.get("result", {})
            except Exception as e:
                logger.warning(f"[LOAD] 加载失败 {data_path}: {e}")

    # 尝试默认路径
    project_root = find_project_root()
    default_path = project_root / "subagents" / "multi-dimensional-data-perception-agent" / "data_result.json"
    if default_path.exists():
        logger.info(f"[LOAD] 从 {default_path} 加载原始数据")
        try:
            with open(default_path, 'r', encoding='utf-8') as f:
                data_result = json.load(f)
                return data_result.get("result", {})
        except Exception as e:
            logger.warning(f"[LOAD] 加载失败 {default_path}: {e}")

    return None


def prepare_dataframes(data_result: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """将数据转换为 DataFrame 格式"""
    dataframes = {}

    for data_type in ["influent", "effluent"]:
        data_list = data_result.get(data_type, [])
        if data_list:
            df = pd.DataFrame(data_list)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            dataframes[data_type] = df
            logger.info(f"[DATA] {data_type} 数据: {len(df)} 条记录")

    return dataframes


def compute_correlation_results(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """计算指标间相关性（用于工艺机理校验）"""
    correlation_results = {"pairs": []}

    # 合并进出水数据计算相关性
    for df in dataframes.values():
        if len(df) < 3:
            continue

        # 选择数值列
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        numeric_cols = [col for col in numeric_cols if col not in ['flow_rate', 'discharge_volume']]

        # 计算相关性
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                try:
                    corr = df[col1].corr(df[col2])
                    if not pd.isna(corr):
                        correlation_results["pairs"].append({
                            "indicator1": col1,
                            "indicator2": col2,
                            "pearson": float(corr)
                        })
                except:
                    pass

    logger.info(f"[DATA] 计算了 {len(correlation_results['pairs'])} 个相关性对")
    return correlation_results


# 指标中文名 → 法规库英文键（regulation_matcher 的 limits 用 COD/TN/AN/TP/pH）
INDICATOR_MAP = {
    "化学需氧量": "COD", "cod": "COD",
    "总氮": "TN", "tn": "TN",
    "氨氮": "AN", "nh3-n": "AN", "nh3n": "AN", "an": "AN",
    "总磷": "TP", "tp": "TP",
    "ph值": "pH", "ph": "pH",
    "悬浮物": "SS", "ss": "SS",
}


def _map_indicator(raw) -> str:
    """中文指标名 → 英文法规键；映射不到则原样返回。"""
    if not raw:
        return ""
    s = str(raw)
    low = s.lower()
    for key, eng in INDICATOR_MAP.items():
        if key.lower() in low:
            return eng
    return s


def normalize_anomalies(anomalies):
    """把异常检测产出的异常归一化成规则模块期望的字段。

    真实 anomaly 字段：indicator(中文) / type(boundary|constant|spike|trend|point) /
    score / value / timestamp ...；而 regulation_matcher / expert_reasoner 读的是
    indicator(英文 COD/TN/..) 和 pattern。这里补齐映射，并保留全部原始字段。
    """
    out = []
    for a in anomalies or []:
        if not isinstance(a, dict):
            continue
        atype = a.get("type") or a.get("pattern") or ""
        try:
            score = float(a.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        norm = dict(a)
        norm["indicator"] = _map_indicator(a.get("indicator", ""))
        norm["pattern"] = atype
        norm["type"] = atype
        norm["score"] = score
        if not a.get("severity"):
            norm["severity"] = "high" if score > 1.0 else ("medium" if score > 0.5 else "low")
        out.append(norm)
    return out


def build_evidence_points(anomalies, regulation_matches, process_validation, reasoning_result):
    """聚合各模块产出，生成可读的证据链（替代原来硬编码的空 []）。"""
    points = []

    # 1. 法规违规证据
    for v in (regulation_matches or {}).get("violations", []):
        points.append({
            "category": "regulation",
            "indicator": v.get("indicator"),
            "regulation": v.get("regulation"),
            "regulation_code": v.get("regulation_code"),
            "violation_type": v.get("violation_type"),
            "article": v.get("article"),
            "penalty": v.get("penalty"),
            "evidence": v.get("evidence", ""),
        })

    # 2. 工艺机理违背证据
    pv = process_validation or {}
    pv_list = pv.get("violations", [])
    if isinstance(pv_list, list):
        for mv in pv_list:
            points.append({"category": "process_mechanism", **(mv if isinstance(mv, dict) else {"detail": mv})})
    if pv.get("violations_count", 0) > 0 and not pv_list:
        points.append({"category": "process_mechanism",
                       "violations_count": pv.get("violations_count"),
                       "mechanism_compliance": pv.get("mechanism_compliance")})

    # 3. 专家匹配的造假模式
    for p in (reasoning_result or {}).get("matched_patterns", []):
        points.append({
            "category": "expert_pattern",
            "pattern": p.get("name"),
            "pattern_key": p.get("pattern_key"),
            "match_score": p.get("match_score"),
            "confidence": p.get("confidence"),
            "suspicion_level": p.get("suspicion_level"),
        })

    # 4. 历史相似案例
    for c in (reasoning_result or {}).get("matched_cases", []):
        points.append({"category": "similar_case", "case": c.get("name"),
                       "similarity": c.get("similarity"), "conclusion": c.get("conclusion")})

    # 5. 数据层证据：分数最高的几个异常点
    top = sorted(anomalies or [], key=lambda a: a.get("score", 0), reverse=True)[:5]
    for a in top:
        points.append({
            "category": "anomaly",
            "indicator": a.get("indicator"),
            "type": a.get("type"),
            "value": a.get("value"),
            "timestamp": a.get("timestamp"),
            "score": a.get("score"),
            "expected_range": a.get("expected_range"),
        })

    return points


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='规则推理和违规判定')
    parser.add_argument('--anomaly-result', type=str, help='异常检测结果路径')
    parser.add_argument('--session-dir', type=str, help='会话目录路径')
    parser.add_argument('--output-dir', type=str, help='输出目录路径')

    args = parser.parse_args()

    task_id = f"rule_reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("=" * 60)
    logger.info("规则推理任务启动")
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

        anomaly_path = Path(args.anomaly_result) if args.anomaly_result else None

        # 2. 加载异常检测结果
        logger.info("[STEP 1/5] 加载异常检测结果")
        anomaly_result = load_anomaly_result(anomaly_path, session_dir)

        if not anomaly_result or anomaly_result.get("status") != "completed":
            raise ValueError("异常检测结果无效或未完成")

        anomalies = anomaly_result.get("result", {}).get("anomalies", [])
        anomalies = normalize_anomalies(anomalies)
        logger.info(f"[LOAD] 加载了 {len(anomalies)} 个异常点（已归一化：indicator→COD/TN/..，type→pattern）")

        if not anomalies:
            logger.warning("[LOAD] 没有异常点，无需进行规则推理")
            output = {
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "conclusion": "无异常，无需违规判定",
                    "suspicion_level": "low",
                    "has_violation": False
                },
                "metadata": {
                    "subagent": "rule-reasoning-agent",
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            # 3. 加载原始数据
            logger.info("[STEP 2/5] 加载原始数据")
            data_result = load_data(session_dir)

            dataframes = {}
            if data_result:
                dataframes = prepare_dataframes(data_result)

            # 4. 计算辅助数据
            logger.info("[STEP 3/5] 计算辅助数据")
            correlation_results = compute_correlation_results(dataframes)
            trend_results = {}  # 简化处理

            # 5. 执行规则推理
            logger.info("[STEP 4/5] 执行规则推理")

            # 5.1 法规规则匹配
            logger.info("[RULE] 法规规则匹配...")
            regulation_matcher = RegulationMatcher()
            regulation_matches = regulation_matcher.match(anomalies)

            # 5.2 工艺机理校验
            logger.info("[RULE] 工艺机理校验...")
            process_validator = ProcessValidator()

            # 获取出水数据用于机理校验
            effluent_df = dataframes.get("effluent")
            if effluent_df is None and dataframes.get("influent") is not None:
                effluent_df = dataframes["influent"]

            process_validation = process_validator.validate(
                anomalies,
                correlation_results,
                trend_results,
                data=effluent_df
            )

            # 5.3 专家经验推理
            logger.info("[RULE] 专家经验推理...")
            expert_reasoner = ExpertReasoner()
            reasoning_result = expert_reasoner.reason(
                anomalies,
                regulation_matches,
                process_validation
            )

            # 6. 生成综合结论
            logger.info("[STEP 5/5] 生成综合结论")

            # 确定违规类型
            violation_types = []
            for pattern in reasoning_result.get("matched_patterns", []):
                pattern_key = pattern.get("pattern_key", "")
                if pattern_key:
                    violation_types.append(pattern_key)

            # 嫌疑等级映射
            suspicion_level = reasoning_result.get("suspicion_level", "low")
            suspicion_mapping = {
                "low": "低",
                "medium": "中",
                "high": "高",
                "critical": "严重"
            }

            # 生成违规判定结论
            has_violation = (
                suspicion_level in ["high", "critical"] or
                process_validation.get("violations_count", 0) > 0 or
                len(regulation_matches.get("violations", [])) > 0
            )

            output = {
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "has_violation": has_violation,
                    "suspicion_level": suspicion_level,
                    "suspicion_level_cn": suspicion_mapping.get(suspicion_level, "未知"),
                    "confidence": reasoning_result.get("confidence", 0.0),

                    # 违规类型
                    "violation_types": violation_types,
                    "violation_type_names": [p.get("name", p.get("pattern_key", ""))
                                            for p in reasoning_result.get("matched_patterns", [])],

                    # 证据点（聚合法规/工艺/专家/案例/数据层证据）
                    "evidence_points": build_evidence_points(
                        anomalies, regulation_matches, process_validation, reasoning_result),
                    "anomaly_count": len(anomalies),

                    # 各模块结果
                    "regulation_matches": regulation_matches,
                    "process_validation": process_validation,
                    "expert_reasoning": reasoning_result,

                    # 结论
                    "conclusion": generate_conclusion(
                        has_violation,
                        suspicion_level,
                        violation_types,
                        reasoning_result,
                        process_validation
                    )
                },
                "metadata": {
                    "subagent": "rule-reasoning-agent",
                    "timestamp": datetime.now().isoformat(),
                    "anomaly_task_id": anomaly_result.get("task_id"),
                    "has_mechanism_violation": reasoning_result.get("has_mechanism_violation", False)
                }
            }

        # 保存结果
        output_file = session_dir / "rule_reasoning_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 打印摘要
        print(f"\n=== 规则推理完成 ===")
        result = output.get("result", {})
        print(f"违规判定: {'是' if result.get('has_violation') else '否'}")
        print(f"嫌疑等级: {result.get('suspicion_level_cn', result.get('suspicion_level'))}")
        print(f"置信度: {result.get('confidence', 0):.1%}")
        print(f"违规类型: {', '.join(result.get('violation_type_names', []))}")
        print(f"结果已保存到: {output_file}")

        logger.info(f"任务完成：{task_id}")

    except Exception as e:
        logger.error(f"任务失败：{e}", exc_info=True)
        output = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": str(e)},
            "metadata": {
                "subagent": "rule-reasoning-agent",
                "timestamp": datetime.now().isoformat()
            }
        }

        # 保存失败结果
        session_dir = Path(args.session_dir) if args.session_dir else Path(__file__).resolve().parents[3]
        output_file = session_dir / "rule_reasoning_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"=== 规则推理失败 ===")
        print(f"错误: {str(e)}")
        print(f"结果已保存到: {output_file}")

        sys.exit(1)


def generate_conclusion(has_violation: bool, suspicion_level: str,
                       violation_types: List[str],
                       reasoning_result: Dict[str, Any],
                       process_validation: Dict[str, Any]) -> str:
    """生成违规判定结论"""
    if not has_violation:
        return "未检测到明显违规行为，数据符合正常工艺规律。"

    # 违规类型映射
    type_names = {
        "bottle_interference": "插瓶干扰",
        "data_dilution": "稀释排放",
        "secret_pipe": "暗管偷排",
        "false_shutdown": "虚假停产",
        "formula_tampering": "公式篡改"
    }

    # 嫌疑等级描述
    level_desc = {
        "low": "存在轻微异常，需关注",
        "medium": "存在违规嫌疑，建议核查",
        "high": "高度疑似违规，强烈建议现场核查",
        "critical": "严重违规，应立即采取措施"
    }

    parts = []

    # 嫌疑等级
    parts.append(f"嫌疑等级：{level_desc.get(suspicion_level, '未知')}")

    # 违规类型
    if violation_types:
        type_list = [type_names.get(t, t) for t in violation_types]
        parts.append(f"疑似违规类型：{', '.join(type_list)}")

    # 工艺机理违背
    if process_validation.get("violations_count", 0) > 0:
        parts.append(f"检测到 {process_validation['violations_count']} 处违背工艺机理")

    # 案例匹配
    matched_cases = reasoning_result.get("matched_cases", [])
    if matched_cases:
        parts.append(f"匹配到 {len(matched_cases)} 个历史相似案例")

    return "；".join(parts) + "。"


if __name__ == "__main__":
    sys.exit(main())

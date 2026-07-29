#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测执行脚本 - 最近24小时
功能：获取最近 24 小时数据并执行异常检测
输出：JSON 格式结果
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 项目根(subagents/.../scripts/ 上 5 层),供 import shared.data.influxdb_query
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

import numpy as np
import pandas as pd
from scipy import stats

from shared.operators.specialized.constant_detector import ConstantDetector
from shared.operators.specialized.change_point_detector import ChangePointDetector
from shared.operators.specialized.trend_detector import TrendDetector
from shared.operators.specialized.high_freq_detector import HighFreqDetector
from shared.operators.specialized.periodicity_detector import PeriodicityDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ---------- InfluxDB 数据源(2026 真实报表)----------
# InfluxDB 契约字段(英文)→ 原 CSV 中文列名(对齐 detect_anomalies 期望,零改动)
_INFLUX_CN_FIELDS = {
    "pH": "pH值", "COD": "化学需氧量浓度（毫克/升）", "TN": "总氮浓度（毫克/升）",
    "AN": "氨氮浓度（毫克/升）", "TP": "总磷浓度（毫克/升）",
    "flow": "流量（升/秒）", "discharge": "排放量（吨）",
    "suspended_solids": "悬浮物浓度（毫克/升）",
}
_INFLUX_KEEP = ["pH", "COD", "TN", "AN", "TP", "flow", "discharge", "suspended_solids"]


def _load_influx_env() -> None:
    """轻量加载项目根 .env(不覆盖已有环境变量)。"""
    env = Path(__file__).resolve().parents[5] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _fetch_influx_cn(client, bucket: str, data_type: str):
    """从 InfluxDB 查一侧(委托共享模块)+ 重命名为中文列名(对齐原 CSV,detect_anomalies 零改动)。"""
    from shared.data.influxdb_query import fetch_wastewater_df, CANONICAL_FIELDS
    df = fetch_wastewater_df(client, bucket, data_type, CANONICAL_FIELDS)
    if df.empty:
        return df
    df = df.rename(columns=_INFLUX_CN_FIELDS).reset_index().rename(columns={"timestamp": "监测时间"})
    for col in df.columns:
        if col != "监测时间":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("监测时间").reset_index(drop=True)


# data_result.json（数据感知产出）英文字段 → detect_anomalies 期望的中文列名。
# 注意 data_result 用 NH3-N/flow_rate/discharge_volume/SS，与 InfluxDB 契约字段
# (AN/flow/discharge/suspended_solids)不同，这里按 data_result 实际字段映射。
_RESULT_FIELD_CN = {
    "timestamp": "监测时间",
    "pH": "pH值", "COD": "化学需氧量浓度（毫克/升）", "TN": "总氮浓度（毫克/升）",
    "NH3-N": "氨氮浓度（毫克/升）", "TP": "总磷浓度（毫克/升）",
    "flow_rate": "流量（升/秒）", "discharge_volume": "排放量（吨）",
    "SS": "悬浮物浓度（毫克/升）",
}


def load_data_from_result():
    """优先读 SESSION_DIR/data_result.json（数据感知已按用户时间范围取的数据）。

    链式设计（CLAUDE.md 三库一体 + 链式传递）：数据感知是唯一数据入口，异常检测消费
    它的结果，保证检测时间范围 = 用户所问（如"14-15日"），而非脚本默认的最近24h。
    之前 main 硬编码 load_recent_data(hours=24)，导致用户问14-15日、数据感知也取了
    14-15日，异常检测却丢掉它自己去 InfluxDB 取最近24h（7-24/25日），时间窗错位。
    无 data_result.json 时返回 None，由 main fallback 到 load_recent_data（旧行为）。
    返回结构与 load_recent_data 一致。
    """
    session_dir = os.environ.get('SESSION_DIR')
    if not session_dir:
        return None
    p = Path(session_dir) / 'data_result.json'
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        r = d.get('result', {}) if isinstance(d, dict) else {}
        infl = r.get('influent', []) or []
        effl = r.get('effluent', []) or []
        if not infl and not effl:
            return None

        def _to_df(rows):
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows).rename(columns=_RESULT_FIELD_CN)
            for col in df.columns:
                if col != "监测时间":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "监测时间" in df.columns:
                df = df.sort_values("监测时间").reset_index(drop=True)
            return df

        df_in = _to_df(infl)
        df_out = _to_df(effl)
        logger.info(f"链式消费 data_result.json: 进水{len(df_in)}条 出水{len(df_out)}条")
        return {"influent_df": df_in, "effluent_df": df_out,
                "time_col_in": "监测时间", "time_col_out": "监测时间"}
    except Exception as e:
        logger.warning(f"读 data_result.json 失败，fallback InfluxDB: {e}")
        return None


def load_recent_data(hours: int = 24) -> dict:
    """从 InfluxDB 加载最近 N 小时数据(2026 真实报表)。

    返回结构与旧 CSV 版完全一致(influent_df/effluent_df/time_col_*),
    列名为中文(对齐原 CSV),detect_anomalies 零改动。
    旧版按 now-cutoff 过滤后 tail(24) 兜底,会取到 2024 末尾;新版直接取 InfluxDB 最新 N 条。
    """
    _load_influx_env()
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")

    logger.info(f"加载最近{hours}小时数据(InfluxDB bucket={bucket})...")

    if not token:
        logger.error("INFLUXDB_TOKEN 未设置(环境变量或项目根 .env)")
        return {"influent_df": pd.DataFrame(), "effluent_df": pd.DataFrame(),
                "time_col_in": "监测时间", "time_col_out": "监测时间"}

    try:
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)
        df_in = _fetch_influx_cn(client, bucket, "influent")
        df_out = _fetch_influx_cn(client, bucket, "effluent")
        client.close()
        logger.info(f"读取数据成功：进水{len(df_in)}条，出水{len(df_out)}条")
    except Exception as e:
        logger.error(f"InfluxDB 读取失败：{e}")
        return {"influent_df": pd.DataFrame(), "effluent_df": pd.DataFrame(),
                "time_col_in": "监测时间", "time_col_out": "监测时间"}

    df_in_recent = df_in.tail(hours).copy() if len(df_in) else df_in.copy()
    df_out_recent = df_out.tail(hours).copy() if len(df_out) else df_out.copy()

    logger.info(f"进水数据：{len(df_in_recent)} 条记录")
    logger.info(f"出水数据：{len(df_out_recent)} 条记录")

    return {
        "influent_df": df_in_recent,
        "effluent_df": df_out_recent,
        "time_col_in": "监测时间",
        "time_col_out": "监测时间",
    }


def zscore_anomaly(values: np.ndarray, threshold: float = 3.0) -> tuple:
    """Z-score 异常检测"""
    mean = np.nanmean(values)
    std = np.nanstd(values)
    if std < 1e-8:
        return np.zeros_like(values), np.zeros(len(values), dtype=bool)
    z_scores = np.abs((values - mean) / std)
    anomaly_mask = z_scores > threshold
    return z_scores, anomaly_mask


def iqr_anomaly(values: np.ndarray, multiplier: float = 1.5) -> tuple:
    """IQR 异常检测"""
    q1 = np.nanpercentile(values, 25)
    q3 = np.nanpercentile(values, 75)
    iqr = q3 - q1
    if iqr < 1e-8:
        return np.zeros_like(values), np.zeros(len(values), dtype=bool)
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    anomaly_mask = (values < lower_bound) | (values > upper_bound)
    # 计算异常分数
    scores = np.zeros_like(values, dtype=float)
    scores[values < lower_bound] = (lower_bound - values[values < lower_bound]) / iqr
    scores[values > upper_bound] = (values[values > upper_bound] - upper_bound) / iqr
    return scores, anomaly_mask


def isolation_forest_anomaly(values: np.ndarray, contamination: float = 0.1) -> tuple:
    """孤立森林异常检测（简化实现;真实数据含缺失,先用中位数填充 NaN）。"""
    try:
        from sklearn.ensemble import IsolationForest
        # 孤立森林不接受 NaN,用中位数填充(保持序列长度,不影响 index 对齐)
        vals = np.asarray(values, dtype=float)
        if np.isnan(vals).any():
            med = np.nanmedian(vals)
            if np.isnan(med):  # 全 NaN 的极端情况
                med = 0.0
            vals = np.where(np.isnan(vals), med, vals)
        X = vals.reshape(-1, 1)
        iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        predictions = iso_forest.fit_predict(X)
        anomaly_mask = predictions == -1
        scores = -iso_forest.score_samples(X)
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        return scores, anomaly_mask
    except ImportError:
        logger.warning("sklearn 不可用，使用 Z-score 替代")
        return zscore_anomaly(values)
    except Exception as e:
        logger.warning(f"孤立森林检测失败，使用 Z-score 替代：{e}")
        return zscore_anomaly(values)


def detect_features_for_series(values: np.ndarray, series_name: str) -> list:
    """对单个序列跑 5 类特征算子 + 孤立森林评分，返回异常点列表。

    每个返回的 anomaly 含: index/features/score/confidence/pattern_similarity/value。
    可信度公式(资料): confidence = 0.6×异常分数 + 0.4×模式相似度。
    """
    series = pd.Series(values)
    if len(series) < 5:
        return []

    # 5 特征算子
    detectors = [
        ("平稳", ConstantDetector(), "is_constant"),
        ("突变", ChangePointDetector(), "is_change"),  # change_point 无统一 flag, 用 mask
        ("趋势", TrendDetector(), "is_trend"),
        ("周期", PeriodicityDetector(), "is_periodic"),
        ("高频波动", HighFreqDetector(), "is_high_freq"),
    ]
    matched_features = []
    for name, det, flag_key in detectors:
        try:
            mask, details = det.detect(series)
            is_hit = details.get(flag_key, False) or (mask is not None and mask.any())
            if is_hit:
                matched_features.append(name)
        except Exception as e:
            logger.warning(f"{name} 检测失败({series_name}): {e}")

    if not matched_features:
        return []

    # 孤立森林评分
    anomaly_score = 0.0
    try:
        vals = series.dropna().values.reshape(-1, 1)
        if len(vals) >= 10:
            iso = IsolationForest(contamination=0.1, random_state=42)
            iso.fit(vals)
            raw = -iso.score_samples(vals)
            mx, mn, sd = raw.max(), raw.min(), raw.std()
            anomaly_score = float((mx - mn) / (sd + 1e-9))
            anomaly_score = float(min(max(anomaly_score / 3.0, 0.0), 1.0))
    except Exception as e:
        logger.warning(f"孤立森林评分失败({series_name}): {e}")

    pattern_similarity = len(matched_features) / 5.0
    confidence = 0.6 * anomaly_score + 0.4 * pattern_similarity

    return [{
        "index": len(series) - 1,  # 整序列级特征, 用末点做锚
        "features": matched_features,
        "score": anomaly_score,
        "confidence": float(confidence),
        "pattern_similarity": float(pattern_similarity),
        "value": float(series.iloc[-1]),
    }]


def detect_anomalies_in_series(values: np.ndarray, series_name: str) -> list:
    """对单个序列执行多算子异常检测"""
    anomalies = []

    if len(values) < 5:
        logger.warning(f"{series_name} 数据点不足，跳过")
        return anomalies

    # 算子 1: Z-score
    z_scores, z_mask = zscore_anomaly(values)

    # 算子 2: IQR
    iqr_scores, iqr_mask = iqr_anomaly(values)

    # 算子 3: 孤立森林（如果数据量足够）
    if len(values) >= 10:
        if_scores, if_mask = isolation_forest_anomaly(values)
    else:
        if_scores = np.zeros_like(values)
        if_mask = np.zeros(len(values), dtype=bool)

    # 综合评分（简单平均）
    combined_scores = (z_scores + iqr_scores + if_scores) / 3.0

    # 算子一致性：至少 2 个算子认为是异常
    vote_count = z_mask.astype(int) + iqr_mask.astype(int) + if_mask.astype(int)
    combined_mask = vote_count >= 2

    # 收集异常点
    for idx in np.where(combined_mask)[0]:
        anomalies.append({
            "index": int(idx),
            "score": float(combined_scores[idx]),
            "votes": int(vote_count[idx]),
            "value": float(values[idx])
        })

    return anomalies


def recognize_pattern(values: np.ndarray, idx: int) -> str:
    """识别异常模式类型"""
    if idx <= 0 or idx >= len(values) - 1:
        return "boundary"

    # 检查是否为恒定值
    if np.std(values[max(0, idx-5):min(len(values), idx+6)]) < 1e-6:
        return "constant"

    # 检查是否为突变（spike）
    left_diff = abs(values[idx] - values[idx-1])
    right_diff = abs(values[idx] - values[idx+1])
    local_std = np.std(values[max(0, idx-5):min(len(values), idx+6)])

    if local_std > 1e-6 and (left_diff > 3 * local_std or right_diff > 3 * local_std):
        return "spike"

    # 检查是否为趋势
    if idx >= 5:
        local_values = values[idx-5:idx+1]
        slope = np.polyfit(range(len(local_values)), local_values, 1)[0]
        if abs(slope) > 0.1 * np.std(local_values):
            return "trend"

    return "point"


def detect_anomalies(data: dict) -> dict:
    """执行异常检测"""
    logger.info("开始异常检测...")

    all_anomalies = []

    # 处理进水和出水数据
    for data_type in ["influent", "effluent"]:
        df = data.get(f"{data_type}_df")
        # 正确获取时间列名称
        if data_type == "influent":
            time_col = data.get("time_col_in", "监测时间")
        else:  # effluent
            time_col = data.get("time_col_out", "监测时间")

        if df is None or len(df) == 0:
            logger.warning(f"{data_type} 数据为空，跳过")
            continue

        # 确定要检测的指标（排除时间和非数值列）
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = ['流量（升/秒）', '排放量（吨）']
        indicators = [col for col in numeric_cols if col not in exclude_cols]

        logger.info(f"检测{data_type}指标：{indicators}")

        # 对每个指标执行异常检测
        for indicator in indicators:
            values = df[indicator].values

            if len(values) < 5:
                logger.warning(f"{indicator} 数据点不足，跳过")
                continue

            # 检测异常(调算子库: 5 特征 + 孤立森林评分 + 可信度)
            anomalies = detect_features_for_series(values, f"{data_type}_{indicator}")

            # 添加元数据
            for anomaly in anomalies:
                idx = anomaly["index"]
                timestamp = df.iloc[idx][time_col] if time_col in df.columns else str(idx)
                if isinstance(timestamp, pd.Timestamp):
                    timestamp = timestamp.isoformat()

                anomaly_entry = {
                    "data_type": data_type,
                    "indicator": indicator,
                    "timestamp": str(timestamp),
                    "features": anomaly.get("features", []),
                    "score": anomaly.get("score", 0.0),
                    "confidence": anomaly.get("confidence", 0.0),
                    "pattern_similarity": anomaly.get("pattern_similarity", 0.0),
                    "value": anomaly.get("value"),
                    "expected_range": [
                        float(np.nanpercentile(values, 25)),
                        float(np.nanpercentile(values, 75))
                    ]
                }
                all_anomalies.append(anomaly_entry)

    # 按分数排序
    all_anomalies.sort(key=lambda x: x['score'], reverse=True)

    # 生成摘要
    summary = {
        "total_anomalies": len(all_anomalies),
        "by_data_type": {},
        "by_indicator": {},
        "by_feature": {}
    }

    for anomaly in all_anomalies:
        dt = anomaly['data_type']
        ind = anomaly['indicator']

        summary['by_data_type'][dt] = summary['by_data_type'].get(dt, 0) + 1
        summary['by_indicator'][ind] = summary['by_indicator'].get(ind, 0) + 1
        for feat in anomaly.get('features', []):
            summary['by_feature'][feat] = summary['by_feature'].get(feat, 0) + 1

    return {
        "anomalies": all_anomalies,
        "summary": summary
    }


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("异常检测任务启动")
    logger.info("=" * 60)

    task_id = f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # 1. 加载数据：优先链式消费数据感知产出的 data_result.json（时间范围=用户所问）；
        #    没有才 fallback 到 InfluxDB 最近 24h（旧行为）。
        data = load_data_from_result()
        _data_source = "data_result(链式消费数据感知)"
        if data is None:
            data = load_recent_data(hours=24)
            _data_source = "influxdb_recent_24h(fallback)"

        if data['influent_df'] is None or len(data['influent_df']) == 0:
            if data['effluent_df'] is None or len(data['effluent_df']) == 0:
                raise ValueError("未能加载到任何数据")

        # 2. 执行异常检测
        detection_result = detect_anomalies(data)

        # 3. 生成输出
        output = {
            "task_id": task_id,
            "status": "completed",
            "result": detection_result,
            "metadata": {
                "subagent": "anomaly-detection-agent",
                "timestamp": datetime.now().isoformat(),
                "time_range": _data_source,
                "data_points": {
                    "influent": len(data.get('influent_df', [])),
                    "effluent": len(data.get('effluent_df', []))
                }
            }
        }

        # 4. 保存到会话目录（优先）或子智能体目录
        # 注意：不打印完整 JSON 到 stdout，避免 LLM 处理大量数据
        session_dir = os.environ.get('SESSION_DIR')
        if session_dir:
            output_file = Path(session_dir) / "anomaly_result.json"
        else:
            output_file = Path(__file__).resolve().parents[3] / "anomaly_result.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 打印摘要信息
        print(f"=== 异常检测完成 ===")
        print(f"状态: {output['status']}")
        print(f"异常数量: {detection_result['summary']['total_anomalies']}")
        print(f"结果已保存到: {output_file}")

        logger.info(f"任务完成：{task_id}")
        logger.info(f"检测到 {detection_result['summary']['total_anomalies']} 处异常")

    except Exception as e:
        logger.error(f"任务失败：{e}", exc_info=True)
        output = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": str(e)},
            "metadata": {
                "subagent": "anomaly-detection-agent",
                "timestamp": datetime.now().isoformat()
            }
        }

        # 保存失败结果到会话目录
        session_dir = os.environ.get('SESSION_DIR')
        if session_dir:
            output_file = Path(session_dir) / "anomaly_result.json"
        else:
            output_file = Path(__file__).resolve().parents[3] / "anomaly_result.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"=== 异常检测失败 ===")
        print(f"错误: {str(e)}")
        print(f"结果已保存到: {output_file}")

        sys.exit(1)


if __name__ == "__main__":
    main()

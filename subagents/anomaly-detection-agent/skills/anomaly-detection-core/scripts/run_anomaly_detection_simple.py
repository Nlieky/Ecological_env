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

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def load_recent_data(hours: int = 24) -> dict:
    """加载最近 N 小时的进水出水数据"""
    # 数据目录 - 从项目根目录查找
    # 方法1: 检查环境变量 PROJECT_ROOT
    project_root = os.environ.get('PROJECT_ROOT')
    if project_root:
        base_dir = Path(project_root)
    else:
        # 方法2: 从脚本位置向上查找项目根目录（包含 data/ 目录的父目录）
        current_dir = Path(__file__).resolve().parent
        for _ in range(6):  # 向上查找最多6层
            if (current_dir / "shared" / "data" / "pollution_water_in.csv").exists():
                base_dir = current_dir
                break
            current_dir = current_dir.parent
        else:
            # 方法3: 使用固定的项目根目录（Windows路径）
            base_dir = Path("E:/project/Ecological_env")

    data_dir = base_dir / "shared" / "data"
    inflow_file = data_dir / "pollution_water_in.csv"
    outflow_file = data_dir / "pollution_water_out.csv"
    
    logger.info(f"加载最近{hours}小时数据...")
    logger.info(f"数据目录：{data_dir}")
    
    if not inflow_file.exists():
        logger.error(f"进水数据文件不存在：{inflow_file}")
        return {"influent": [], "effluent": [], "influent_df": pd.DataFrame(), "effluent_df": pd.DataFrame()}
    
    if not outflow_file.exists():
        logger.error(f"出水数据文件不存在：{outflow_file}")
        return {"influent": [], "effluent": [], "influent_df": pd.DataFrame(), "effluent_df": pd.DataFrame()}
    
    try:
        df_in = pd.read_csv(inflow_file, encoding='utf-8-sig')
        df_out = pd.read_csv(outflow_file, encoding='utf-8-sig')

        # 解析时间列名称
        time_col_in = '监测时间' if '监测时间' in df_in.columns else 'times'
        time_col_out = '监测时间' if '监测时间' in df_out.columns else 'times'

        # 转换所有可能的数值列为 numeric 类型
        for col in df_in.columns:
            if col != time_col_in:
                df_in[col] = pd.to_numeric(df_in[col], errors='coerce')
        for col in df_out.columns:
            if col != time_col_out:
                df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

        logger.info(f"读取数据成功：进水{len(df_in)}条，出水{len(df_out)}条")
    except Exception as e:
        logger.error(f"读取数据文件失败：{e}")
        return {"influent": [], "effluent": [], "influent_df": pd.DataFrame(), "effluent_df": pd.DataFrame()}
    
    df_in[time_col_in] = pd.to_datetime(df_in[time_col_in], errors='coerce')
    df_out[time_col_out] = pd.to_datetime(df_out[time_col_out], errors='coerce')
    
    # 获取最近 24 小时数据
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    df_in_recent = df_in[df_in[time_col_in] >= cutoff_time].copy()
    df_out_recent = df_out[df_out[time_col_out] >= cutoff_time].copy()
    
    # 如果最近 24 小时没有数据，使用最新的数据
    if len(df_in_recent) == 0:
        df_in_recent = df_in.tail(24).copy()
    if len(df_out_recent) == 0:
        df_out_recent = df_out.tail(24).copy()
    
    logger.info(f"进水数据：{len(df_in_recent)} 条记录")
    logger.info(f"出水数据：{len(df_out_recent)} 条记录")
    
    return {
        "influent_df": df_in_recent,
        "effluent_df": df_out_recent,
        "time_col_in": time_col_in,
        "time_col_out": time_col_out
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
    """孤立森林异常检测（简化实现）"""
    try:
        from sklearn.ensemble import IsolationForest
        X = values.reshape(-1, 1)
        iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        predictions = iso_forest.fit_predict(X)
        anomaly_mask = predictions == -1
        scores = -iso_forest.score_samples(X)
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        return scores, anomaly_mask
    except ImportError:
        logger.warning("sklearn 不可用，使用 Z-score 替代")
        return zscore_anomaly(values)


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
            
            # 检测异常
            anomalies = detect_anomalies_in_series(values, f"{data_type}_{indicator}")
            
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
                    "type": recognize_pattern(values, idx),
                    "score": anomaly["score"],
                    "value": anomaly["value"],
                    "votes": anomaly["votes"],
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
        "by_type": {}
    }
    
    for anomaly in all_anomalies:
        dt = anomaly['data_type']
        ind = anomaly['indicator']
        atype = anomaly['type']
        
        summary['by_data_type'][dt] = summary['by_data_type'].get(dt, 0) + 1
        summary['by_indicator'][ind] = summary['by_indicator'].get(ind, 0) + 1
        summary['by_type'][atype] = summary['by_type'].get(atype, 0) + 1
    
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
        # 1. 加载数据
        data = load_recent_data(hours=24)
        
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
                "time_range": "24h",
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
            output_file = Path("E:/project/Ecological_env/subagents/anomaly-detection-agent/anomaly_result.json")

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
            output_file = Path("E:/project/Ecological_env/subagents/anomaly-detection-agent/anomaly_result.json")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"=== 异常检测失败 ===")
        print(f"错误: {str(e)}")
        print(f"结果已保存到: {output_file}")

        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废水监测数据异常检测 - 综合分析脚本
检测类型：插瓶干扰(constant)、突变(spike)、稀释排放、数据缺失、超标
检测方法：3σ + IQR
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# 数据路径
DATA_DIR = Path("E:/project/Ecological_env/data")
INFLOW_FILE = DATA_DIR / "pollution_water_in.csv"
OUTFLOW_FILE = DATA_DIR / "pollution_water_out.csv"

# 排放标准限值（GB 18918-2002 一级A标）
STANDARD_LIMITS = {
    "COD": {"limit": 50, "direction": "upper"},
    "TN": {"limit": 15, "direction": "upper"},
    "NH3-N": {"limit": 5, "direction": "upper"},
    "TP": {"limit": 0.5, "direction": "upper"},
    "SS": {"limit": 10, "direction": "upper"},
    "pH": {"lower": 6.0, "upper": 9.0, "direction": "range"},
    "流量（升/秒）": {"limit": None, "direction": "none"},
    "排放量（吨）": {"limit": None, "direction": "none"},
}

# 列名映射（标准化列名）
COLUMN_MAPPING = {
    "pH 值": "pH",
    "pH值": "pH",
    "化学需氧量浓度（毫克/升）": "COD",
    "总氮浓度（毫克/升）": "TN",
    "氨氮浓度（毫克/升）": "NH3-N",
    "总磷浓度（毫克/升）": "TP",
    "悬浮物浓度（毫克/升）": "SS",
    "流量（升/秒）": "流量（升/秒）",
    "排放量（吨）": "排放量（吨）",
}

# 核心检测指标
CORE_INDICATORS = ["COD", "TN", "NH3-N", "TP", "SS", "pH"]


def load_data():
    """加载进水/出水数据"""
    print("加载数据文件...")
    
    if not INFLOW_FILE.exists():
        raise FileNotFoundError(f"进水数据文件不存在: {INFLOW_FILE}")
    if not OUTFLOW_FILE.exists():
        raise FileNotFoundError(f"出水数据文件不存在: {OUTFLOW_FILE}")
    
    df_in = pd.read_csv(INFLOW_FILE, encoding='utf-8-sig')
    df_out = pd.read_csv(OUTFLOW_FILE, encoding='utf-8-sig')
    
    print(f"  进水数据: {len(df_in)} 条记录")
    print(f"  出水数据: {len(df_out)} 条记录")
    
    # 识别时间列
    time_col_in = None
    time_col_out = None
    for col in df_in.columns:
        if '时间' in col or 'time' in col.lower() or 'times' in col.lower():
            time_col_in = col
            break
    for col in df_out.columns:
        if '时间' in col or 'time' in col.lower() or 'times' in col.lower():
            time_col_out = col
            break
    
    if time_col_in is None:
        # 尝试第一列
        time_col_in = df_in.columns[0]
    if time_col_out is None:
        time_col_out = df_out.columns[0]
    
    print(f"  进水时间列: {time_col_in}")
    print(f"  出水时间列: {time_col_out}")
    
    # 解析时间
    df_in['_timestamp'] = pd.to_datetime(df_in[time_col_in], errors='coerce')
    df_out['_timestamp'] = pd.to_datetime(df_out[time_col_out], errors='coerce')
    
    # 标准化列名
    df_in = df_in.rename(columns=COLUMN_MAPPING)
    df_out = df_out.rename(columns=COLUMN_MAPPING)
    
    # 过滤有效时间
    df_in = df_in[df_in['_timestamp'].notna()].copy()
    df_out = df_out[df_out['_timestamp'].notna()].copy()
    
    df_in = df_in.sort_values('_timestamp').reset_index(drop=True)
    df_out = df_out.sort_values('_timestamp').reset_index(drop=True)
    
    return df_in, df_out, time_col_in, time_col_out


def detect_zscore(values, threshold=3.0):
    """3σ异常检测"""
    values_clean = values[~np.isnan(values)]
    if len(values_clean) < 5:
        return np.zeros(len(values)), np.zeros(len(values), dtype=bool)
    
    mean = np.nanmean(values)
    std = np.nanstd(values)
    
    if std < 1e-10:
        return np.zeros(len(values)), np.zeros(len(values), dtype=bool)
    
    z_scores = np.abs((values - mean) / std)
    z_scores = np.nan_to_num(z_scores, nan=0.0)
    anomaly_mask = z_scores > threshold
    
    return z_scores, anomaly_mask


def detect_iqr(values, multiplier=1.5):
    """IQR异常检测"""
    values_clean = values[~np.isnan(values)]
    if len(values_clean) < 5:
        return np.zeros(len(values)), np.zeros(len(values), dtype=bool)
    
    q1 = np.nanpercentile(values, 25)
    q3 = np.nanpercentile(values, 75)
    iqr = q3 - q1
    
    if iqr < 1e-10:
        return np.zeros(len(values)), np.zeros(len(values), dtype=bool)
    
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    
    anomaly_mask = (values < lower_bound) | (values > upper_bound)
    
    # 异常分数：超出边界的距离 / IQR
    scores = np.zeros_like(values, dtype=float)
    scores[values < lower_bound] = (lower_bound - values[values < lower_bound]) / max(iqr, 1e-10)
    scores[values > upper_bound] = (values[values > upper_bound] - upper_bound) / max(iqr, 1e-10)
    
    return scores, anomaly_mask


def detect_constant_pattern(df, indicator, window=6):
    """
    检测插瓶干扰（恒定不变模式）
    条件：连续window个点的值几乎不变（方差接近0）
    """
    values = df[indicator].values.astype(float)
    n = len(values)
    violations = []
    
    if n < window:
        return violations
    
    for i in range(n - window + 1):
        segment = values[i:i + window]
        valid = segment[~np.isnan(segment)]
        
        if len(valid) < window * 0.8:
            continue
        
        mean_val = np.mean(valid)
        std_val = np.std(valid)
        
        # 方差接近0（变异系数 < 0.5%）
        if mean_val != 0:
            cv = std_val / abs(mean_val)
            is_constant = cv < 0.005
        else:
            is_constant = std_val < 0.01
        
        if is_constant:
            # 检查是否接近标准限值（插瓶干扰特征）
            near_limit = False
            if indicator in STANDARD_LIMITS:
                limit_info = STANDARD_LIMITS[indicator]
                if limit_info["direction"] == "upper":
                    # 接近上限的80%-100%
                    if mean_val >= limit_info["limit"] * 0.8:
                        near_limit = True
                elif limit_info["direction"] == "range":
                    lower = limit_info["lower"]
                    upper = limit_info["upper"]
                    # pH恒定在中性附近或接近限值
                    if abs(mean_val - 7.0) < 0.3 or mean_val <= lower * 1.1 or mean_val >= upper * 0.9:
                        near_limit = True
            
            start_ts = df.iloc[i]['_timestamp']
            end_ts = df.iloc[i + window - 1]['_timestamp']
            
            violations.append({
                "type": "插瓶干扰",
                "sub_type": "constant",
                "indicator": indicator,
                "start_time": str(start_ts),
                "end_time": str(end_ts),
                "duration_hours": window,
                "value_mean": float(mean_val),
                "value_std": float(std_val),
                "cv": float(cv),
                "near_limit": near_limit,
                "confidence": min(0.95, 0.7 + 0.25 * (1 - cv * 200)),
                "evidence": f"{indicator}连续{window}小时值几乎不变（CV={cv:.4f}），均值={mean_val:.2f}" +
                            (f"，接近标准限值" if near_limit else "")
            })
    
    # 合并重叠的恒定异常
    violations = merge_overlapping_violations(violations)
    return violations


def merge_overlapping_violations(violations):
    """合并重叠的违规记录"""
    if not violations:
        return violations
    
    # 按开始时间排序
    violations = sorted(violations, key=lambda x: x["start_time"])
    merged = [violations[0]]
    
    for v in violations[1:]:
        last = merged[-1]
        if v["indicator"] == last["indicator"] and v["start_time"] <= last["end_time"]:
            # 合并
            last["end_time"] = max(last["end_time"], v["end_time"])
            last["duration_hours"] = max(last["duration_hours"], v["duration_hours"])
            last["confidence"] = max(last["confidence"], v["confidence"])
        else:
            merged.append(v)
    
    return merged


def detect_spike_pattern(df, indicator, z_scores, iqr_scores, z_mask, iqr_mask):
    """
    检测突变异常（spike）
    条件：3σ和IQR同时检测到异常，且相邻点变化剧烈
    """
    values = df[indicator].values.astype(float)
    n = len(values)
    anomalies = []
    
    # 算子一致性投票
    vote_count = z_mask.astype(int) + iqr_mask.astype(int)
    combined_mask = vote_count >= 2
    
    for idx in np.where(combined_mask)[0]:
        if idx <= 0 or idx >= n - 1:
            continue
        
        # 计算变化幅度
        prev_val = values[idx - 1] if not np.isnan(values[idx - 1]) else values[idx]
        next_val = values[idx + 1] if not np.isnan(values[idx + 1]) else values[idx]
        curr_val = values[idx]
        
        if np.isnan(curr_val):
            continue
        
        # 相对变化
        if abs(prev_val) > 1e-6:
            rel_change = abs(curr_val - prev_val) / abs(prev_val)
        else:
            rel_change = abs(curr_val - prev_val)
        
        # 突变判定：相对变化 > 20% 或绝对变化 > 3σ
        local_std = np.nanstd(values[max(0, idx-10):min(n, idx+10)])
        is_spike = rel_change > 0.2 or abs(curr_val - prev_val) > 3 * max(local_std, 1e-6)
        
        if is_spike:
            timestamp = df.iloc[idx]['_timestamp']
            combined_score = (z_scores[idx] / 3.0 + iqr_scores[idx]) / 2.0
            
            anomalies.append({
                "type": "突变",
                "sub_type": "spike",
                "indicator": indicator,
                "timestamp": str(timestamp),
                "value": float(curr_val),
                "previous_value": float(prev_val),
                "next_value": float(next_val),
                "relative_change": float(rel_change),
                "z_score": float(z_scores[idx]),
                "iqr_score": float(iqr_scores[idx]),
                "confidence": min(0.95, 0.5 + 0.3 * (z_scores[idx] / 10.0) + 0.2 * rel_change),
                "evidence": f"{indicator}在{timestamp}发生突变：{prev_val:.2f} → {curr_val:.2f}（变化率{rel_change*100:.1f}%）"
            })
    
    return anomalies


def detect_dilution_pattern(df_in, df_out):
    """
    检测稀释排放
    特征：出水多指标同步下降，且处于异常低位
    """
    violations = []
    
    # 对每个指标计算趋势
    declining_indicators = []
    low_level_indicators = []
    
    for indicator in CORE_INDICATORS:
        if indicator not in df_out.columns:
            continue
        
        series = df_out[indicator].dropna()
        if len(series) < 100:
            continue
        
        # 计算近期（后25%）vs 前期（前75%）的均值比
        split_point = int(len(series) * 0.75)
        early_mean = series.iloc[:split_point].mean()
        recent_mean = series.iloc[split_point:].mean()
        
        if early_mean > 1e-6:
            ratio = recent_mean / early_mean
        else:
            ratio = 1.0
        
        # 下降趋势
        if ratio < 0.6:
            declining_indicators.append({
                "indicator": indicator,
                "early_mean": float(early_mean),
                "recent_mean": float(recent_mean),
                "ratio": float(ratio)
            })
        
        # 异常低位（低于历史中位数的50%）
        historical_median = series.median()
        if historical_median > 1e-6 and recent_mean < historical_median * 0.5:
            low_level_indicators.append({
                "indicator": indicator,
                "historical_median": float(historical_median),
                "recent_mean": float(recent_mean)
            })
    
    # 多指标同步下降 → 疑似稀释排放
    if len(declining_indicators) >= 2:
        violation = {
            "type": "稀释排放",
            "sub_type": "dilution",
            "indicators_declining": [d["indicator"] for d in declining_indicators],
            "indicators_low": [d["indicator"] for d in low_level_indicators],
            "details": declining_indicators,
            "confidence": min(0.9, 0.5 + 0.1 * len(declining_indicators)),
            "evidence": f"{len(declining_indicators)}个出水指标同步显著下降，疑似稀释排放"
        }
        violations.append(violation)
    
    return violations


def detect_missing_data(df, data_type):
    """
    检测数据缺失异常
    """
    violations = []
    
    for indicator in CORE_INDICATORS:
        if indicator not in df.columns:
            continue
        
        series = df[indicator]
        total = len(series)
        missing = series.isna().sum()
        missing_rate = missing / total if total > 0 else 0
        
        # 缺失率 > 5% 视为异常
        if missing_rate > 0.05:
            violations.append({
                "type": "数据缺失",
                "sub_type": "missing_data",
                "data_type": data_type,
                "indicator": indicator,
                "total_records": total,
                "missing_count": int(missing),
                "missing_rate": float(missing_rate),
                "confidence": min(0.95, missing_rate * 2),
                "evidence": f"{data_type}的{indicator}缺失率{missing_rate*100:.1f}%（{missing}/{total}）"
            })
    
    # 检查时间间隔异常（数据断点）
    timestamps = df['_timestamp']
    if len(timestamps) > 1:
        time_diffs = timestamps.diff().dropna()
        median_interval = time_diffs.median()
        
        # 超过中位间隔5倍的视为断点
        large_gaps = time_diffs[time_diffs > median_interval * 5]
        
        if len(large_gaps) > 0:
            for gap_idx in large_gaps.index[:10]:  # 最多报告10个
                gap_start = timestamps.iloc[gap_idx - 1]
                gap_end = timestamps.iloc[gap_idx]
                gap_hours = (gap_end - gap_start).total_seconds() / 3600
                
                violations.append({
                    "type": "数据缺失",
                    "sub_type": "time_gap",
                    "data_type": data_type,
                    "gap_start": str(gap_start),
                    "gap_end": str(gap_end),
                    "gap_hours": float(gap_hours),
                    "median_interval_hours": float(median_interval.total_seconds() / 3600),
                    "confidence": min(0.9, gap_hours / 24.0),
                    "evidence": f"{data_type}数据存在{gap_hours:.1f}小时间断（正常间隔{median_interval.total_seconds()/3600:.1f}小时）"
                })
    
    return violations


def detect_exceedance(df, data_type):
    """
    检测超标（超过排放标准限值）
    """
    violations = []
    
    for indicator in CORE_INDICATORS:
        if indicator not in df.columns:
            continue
        
        if indicator not in STANDARD_LIMITS:
            continue
        
        limit_info = STANDARD_LIMITS[indicator]
        series = df[indicator].dropna()
        
        if len(series) == 0:
            continue
        
        exceedance_count = 0
        exceedance_records = []
        
        if limit_info["direction"] == "upper":
            limit = limit_info["limit"]
            exceed_mask = series > limit
            exceedance_count = exceed_mask.sum()
            
            if exceedance_count > 0:
                exceed_values = series[exceed_mask]
                exceedance_records.append({
                    "indicator": indicator,
                    "standard_limit": limit,
                    "exceedance_count": int(exceedance_count),
                    "total_count": int(len(series)),
                    "exceedance_rate": float(exceedance_count / len(series)),
                    "max_value": float(exceed_values.max()),
                    "mean_exceed_value": float(exceed_values.mean()),
                    "confidence": min(0.95, 0.7 + 0.25 * (exceedance_count / len(series))),
                    "evidence": f"{data_type}的{indicator}超标{exceedance_count}次（限值{limit}，最大值{exceed_values.max():.2f}）"
                })
        
        elif limit_info["direction"] == "range":
            lower = limit_info["lower"]
            upper = limit_info["upper"]
            exceed_mask = (series < lower) | (series > upper)
            exceedance_count = exceed_mask.sum()
            
            if exceedance_count > 0:
                exceed_values = series[exceed_mask]
                exceedance_records.append({
                    "indicator": indicator,
                    "standard_lower": lower,
                    "standard_upper": upper,
                    "exceedance_count": int(exceedance_count),
                    "total_count": int(len(series)),
                    "exceedance_rate": float(exceedance_count / len(series)),
                    "min_value": float(exceed_values.min()),
                    "max_value": float(exceed_values.max()),
                    "confidence": min(0.95, 0.7 + 0.25 * (exceedance_count / len(series))),
                    "evidence": f"{data_type}的{indicator}超标{exceedance_count}次（范围{lower}-{upper}，实测范围{exceed_values.min():.2f}-{exceed_values.max():.2f}）"
                })
        
        violations.extend(exceedance_records)
    
    return violations


def detect_statistical_anomalies(df, data_type):
    """
    使用3σ和IQR方法检测统计异常点
    """
    all_anomalies = []
    
    for indicator in CORE_INDICATORS:
        if indicator not in df.columns:
            continue
        
        values = df[indicator].values.astype(float)
        n = len(values)
        
        if n < 10:
            continue
        
        # 3σ检测
        z_scores, z_mask = detect_zscore(values)
        
        # IQR检测
        iqr_scores, iqr_mask = detect_iqr(values)
        
        # 突变检测
        spikes = detect_spike_pattern(df, indicator, z_scores, iqr_scores, z_mask, iqr_mask)
        all_anomalies.extend(spikes)
        
        # 统计异常点（非突变，但3σ+IQR都检测到）
        vote_count = z_mask.astype(int) + iqr_mask.astype(int)
        combined_mask = vote_count >= 2
        
        for idx in np.where(combined_mask)[0]:
            # 跳过已识别为突变的点
            timestamp = str(df.iloc[idx]['_timestamp'])
            already_captured = any(
                a.get("timestamp") == timestamp and a.get("indicator") == indicator
                for a in spikes
            )
            if already_captured:
                continue
            
            curr_val = values[idx]
            if np.isnan(curr_val):
                continue
            
            # 计算期望范围
            mean = np.nanmean(values)
            std = np.nanstd(values)
            
            all_anomalies.append({
                "type": "统计异常",
                "sub_type": "statistical_outlier",
                "data_type": data_type,
                "indicator": indicator,
                "timestamp": timestamp,
                "value": float(curr_val),
                "z_score": float(z_scores[idx]),
                "iqr_score": float(iqr_scores[idx]),
                "expected_range": [
                    float(mean - 3 * std),
                    float(mean + 3 * std)
                ],
                "iqr_range": [
                    float(np.nanpercentile(values, 25) - 1.5 * (np.nanpercentile(values, 75) - np.nanpercentile(values, 25))),
                    float(np.nanpercentile(values, 75) + 1.5 * (np.nanpercentile(values, 75) - np.nanpercentile(values, 25)))
                ],
                "confidence": min(0.9, 0.4 + 0.3 * (z_scores[idx] / 10.0) + 0.2 * min(iqr_scores[idx], 1.0)),
                "evidence": f"{data_type}的{indicator}在{timestamp}异常：值={curr_val:.2f}，Z-score={z_scores[idx]:.2f}，超出3σ范围"
            })
    
    return all_anomalies


def main():
    """主函数"""
    print("=" * 70)
    print("废水监测数据异常检测 - 综合分析")
    print("=" * 70)
    
    task_id = f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # 1. 加载数据
        df_in, df_out, time_col_in, time_col_out = load_data()
        
        # 2. 执行各类检测
        print("\n[1/5] 检测插瓶干扰（恒定模式）...")
        constant_in = []
        constant_out = []
        for indicator in CORE_INDICATORS:
            if indicator in df_in.columns:
                constant_in.extend(detect_constant_pattern(df_in, indicator))
            if indicator in df_out.columns:
                constant_out.extend(detect_constant_pattern(df_out, indicator))
        print(f"  进水: {len(constant_in)} 处恒定异常")
        print(f"  出水: {len(constant_out)} 处恒定异常")
        
        print("\n[2/5] 检测突变异常（spike）...")
        spike_in = detect_statistical_anomalies(df_in, "进水")
        spike_out = detect_statistical_anomalies(df_out, "出水")
        print(f"  进水: {len(spike_in)} 处统计异常")
        print(f"  出水: {len(spike_out)} 处统计异常")
        
        print("\n[3/5] 检测稀释排放...")
        dilution = detect_dilution_pattern(df_in, df_out)
        print(f"  发现 {len(dilution)} 处稀释排放嫌疑")
        
        print("\n[4/5] 检测数据缺失...")
        missing_in = detect_missing_data(df_in, "进水")
        missing_out = detect_missing_data(df_out, "出水")
        print(f"  进水: {len(missing_in)} 处缺失异常")
        print(f"  出水: {len(missing_out)} 处缺失异常")
        
        print("\n[5/5] 检测超标...")
        exceed_in = detect_exceedance(df_in, "进水")
        exceed_out = detect_exceedance(df_out, "出水")
        print(f"  进水: {len(exceed_in)} 项超标")
        print(f"  出水: {len(exceed_out)} 项超标")
        
        # 3. 汇总结果
        all_anomalies = []
        all_anomalies.extend([{**v, "data_type": "进水"} for v in constant_in])
        all_anomalies.extend([{**v, "data_type": "出水"} for v in constant_out])
        all_anomalies.extend(spike_in)
        all_anomalies.extend(spike_out)
        all_anomalies.extend(dilution)
        all_anomalies.extend(missing_in)
        all_anomalies.extend(missing_out)
        all_anomalies.extend(exceed_in)
        all_anomalies.extend(exceed_out)
        
        # 按类型统计
        type_counts = {}
        indicator_counts = {}
        for a in all_anomalies:
            t = a.get("type", "unknown")
            ind = a.get("indicator", "multi")
            type_counts[t] = type_counts.get(t, 0) + 1
            indicator_counts[ind] = indicator_counts.get(ind, 0) + 1
        
        # 4. 构建输出
        output = {
            "task_id": task_id,
            "status": "completed",
            "result": {
                "summary": {
                    "total_anomalies": len(all_anomalies),
                    "by_type": type_counts,
                    "by_indicator": indicator_counts,
                    "detection_methods": ["3σ", "IQR"],
                    "detection_types": ["插瓶干扰", "突变", "稀释排放", "数据缺失", "超标"],
                    "data_range": {
                        "influent": {
                            "start": str(df_in['_timestamp'].iloc[0]) if len(df_in) > 0 else None,
                            "end": str(df_in['_timestamp'].iloc[-1]) if len(df_in) > 0 else None,
                            "total_records": len(df_in)
                        },
                        "effluent": {
                            "start": str(df_out['_timestamp'].iloc[0]) if len(df_out) > 0 else None,
                            "end": str(df_out['_timestamp'].iloc[-1]) if len(df_out) > 0 else None,
                            "total_records": len(df_out)
                        }
                    }
                },
                "anomalies": {
                    "插瓶干扰_进水": [{k: v for k, v in a.items() if k != "data_type"} for a in constant_in],
                    "插瓶干扰_出水": [{k: v for k, v in a.items() if k != "data_type"} for a in constant_out],
                    "突变_进水": [a for a in spike_in if a.get("type") == "突变"],
                    "突变_出水": [a for a in spike_out if a.get("type") == "突变"],
                    "统计异常_进水": [a for a in spike_in if a.get("type") == "统计异常"],
                    "统计异常_出水": [a for a in spike_out if a.get("type") == "统计异常"],
                    "稀释排放": dilution,
                    "数据缺失_进水": missing_in,
                    "数据缺失_出水": missing_out,
                    "超标_进水": exceed_in,
                    "超标_出水": exceed_out
                },
                "statistics": {
                    "influent": {},
                    "effluent": {}
                }
            },
            "metadata": {
                "subagent": "anomaly-detection-agent",
                "timestamp": datetime.now().isoformat(),
                "detection_config": {
                    "zscore_threshold": 3.0,
                    "iqr_multiplier": 1.5,
                    "constant_window": 6,
                    "constant_cv_threshold": 0.005,
                    "spike_relative_change_threshold": 0.2,
                    "missing_rate_threshold": 0.05
                }
            }
        }
        
        # 添加各指标统计信息
        for indicator in CORE_INDICATORS:
            for data_type, df in [("influent", df_in), ("effluent", df_out)]:
                if indicator in df.columns:
                    series = df[indicator].dropna()
                    if len(series) > 0:
                        output["result"]["statistics"][data_type][indicator] = {
                            "count": int(len(series)),
                            "mean": float(series.mean()),
                            "std": float(series.std()),
                            "min": float(series.min()),
                            "max": float(series.max()),
                            "median": float(series.median()),
                            "q25": float(series.quantile(0.25)),
                            "q75": float(series.quantile(0.75))
                        }
        
        # 输出JSON
        print("\n" + "=" * 70)
        print(f"检测完成！共发现 {len(all_anomalies)} 处异常")
        print("=" * 70)
        
        result_json = json.dumps(output, ensure_ascii=False, indent=2, default=str)
        print(result_json)
        
        return output
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        
        error_output = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": str(e)},
            "metadata": {
                "subagent": "anomaly-detection-agent",
                "timestamp": datetime.now().isoformat()
            }
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        return error_output


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Emergency Recovery Script for Wastewater Monitoring System

Use this script when sub-agent orchestration fails due to:
- Disk space exhaustion ([Errno 28])
- API authentication failures (401 Unauthorized)
- Context overflow (truncated responses)
- Repeated tool call failures

This script provides direct data analysis as a fallback.
"""

import pandas as pd
import numpy as np
import os
import shutil
from datetime import datetime

# Configuration
DATA_DIR = "E:/project/Ecological_env/data"
INFLUENT_FILE = os.path.join(DATA_DIR, "pollution_water_in.csv")
EFFLUENT_FILE = os.path.join(DATA_DIR, "pollution_water_out.csv")
SESSION_DIR = "E:/project/Ecological_env/workspace/state"

# Field mapping (CRITICAL: pH 值 has no space - it's 3 characters, not 4)
FIELD_MAPPING = {
    "监测时间": "timestamp",
    "pH 值": "pH",
    "化学需氧量浓度（毫克/升）": "COD",
    "总氮浓度（毫克/升）": "TN",
    "氨氮浓度（毫克/升）": "NH3-N",
    "总磷浓度（毫克/升）": "TP",
    "悬浮物浓度（毫克/升）": "SS",
    "流量（升/秒）": "flow_rate",
    "排放量（吨）": "discharge_volume"
}

# Regulatory limits (example values - adjust based on local standards)
REGULATORY_LIMITS = {
    "pH": (6, 9),  # Range
    "COD": 50,     # mg/L
    "TN": 15,      # mg/L
    "NH3-N": 5,    # mg/L
    "TP": 0.5,     # mg/L
    "SS": 10       # mg/L
}


def check_disk_space(path="E:/", threshold_gb=1.0):
    """Check if disk space is above threshold."""
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (2**30)
    print(f"Disk Space Check: {free_gb:.2f} GB free on {path}")
    if free_gb < threshold_gb:
        print(f"⚠️  WARNING: Free space below {threshold_gb} GB threshold!")
        return False
    return True


def check_env_credentials():
    """Check if API credentials are configured."""
    env_file = os.path.join(os.path.dirname(DATA_DIR), ".env")
    if not os.path.exists(env_file):
        print(f"⚠️  WARNING: .env file not found at {env_file}")
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'API_KEY' in content or 'HERMES_API' in content:
            print("✅ API credentials found in .env")
            return True
        else:
            print("⚠️  WARNING: No API_KEY found in .env")
            return False


def cleanup_old_sessions(days=3):
    """Remove session directories older than specified days."""
    if not os.path.exists(SESSION_DIR):
        print(f"Session directory not found: {SESSION_DIR}")
        return 0
    
    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    for session_name in os.listdir(SESSION_DIR):
        session_path = os.path.join(SESSION_DIR, session_name)
        if not os.path.isdir(session_path):
            continue
        
        # Parse timestamp from session name (session_YYYYMMDD_HHMMSS)
        try:
            parts = session_name.split('_')
            if len(parts) >= 3:
                date_str = parts[1]
                time_str = parts[2]
                session_time = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                if session_time.timestamp() < cutoff:
                    shutil.rmtree(session_path)
                    deleted_count += 1
                    print(f"Deleted old session: {session_name}")
        except Exception as e:
            print(f"Error processing {session_name}: {e}")
    
    print(f"Cleanup complete: {deleted_count} sessions deleted")
    return deleted_count


def load_data(file_path, data_type="effluent"):
    """Load and preprocess wastewater data."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Rename columns using field mapping
    rename_dict = {}
    for cn, en in FIELD_MAPPING.items():
        if cn in df.columns:
            rename_dict[cn] = en
    
    df = df.rename(columns=rename_dict)
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    
    print(f"Loaded {len(df)} records from {data_type} data file")
    return df


def analyze_indicator(df, indicator, hours=24):
    """Analyze a specific indicator for recent hours."""
    if indicator not in df.columns:
        print(f"Indicator {indicator} not found in data")
        return None
    
    recent = df.tail(hours)
    data = recent[indicator].dropna()
    
    if len(data) == 0:
        print(f"No valid data for {indicator} in last {hours} hours")
        return None
    
    # Basic statistics
    stats = {
        'indicator': indicator,
        'time_range': f"{recent['timestamp'].iloc[0]} to {recent['timestamp'].iloc[-1]}",
        'data_points': len(data),
        'mean': data.mean(),
        'std': data.std(),
        'max': data.max(),
        'min': data.min(),
        'missing': len(recent[indicator]) - len(data)
    }
    
    # Anomaly detection
    anomalies = []
    
    # 1. Bottle interference (constant value)
    if stats['std'] < 0.1:
        anomalies.append({
            'type': '疑似插瓶干扰',
            'reason': f'Standard deviation {stats["std"]:.4f} < 0.1 (abnormally constant)'
        })
    
    # 2. Sudden changes (>50%)
    changes = data.pct_change().abs()
    spike_count = (changes > 0.5).sum()
    if spike_count > 0:
        anomalies.append({
            'type': '突变检测',
            'reason': f'{spike_count} instances with >50% change'
        })
    
    # 3. Dilution discharge (sudden drop >50%)
    for i in range(len(data) - 1):
        if data.iloc[i] > 0:
            drop_ratio = (data.iloc[i] - data.iloc[i+1]) / / data.iloc[i]
            if drop_ratio > 0.5:
                anomalies.append({
                    'type': '疑似稀释排放',
                    'reason': f'At index {i}: {drop_ratio*100:.1f}% drop'
                })
    
    # 4. Regulatory exceedance
    if indicator in REGULATORY_LIMITS:
        limit = REGULATORY_LIMITS[indicator]
        if isinstance(limit, tuple):
            # Range check (e.g., pH)
            if (data < limit[0]).any() or (data > limit[1]).any():
                anomalies.append({
                    'type': '超标检测',
                    'reason': f'Values outside range {limit}'
                })
        else:
            # Single limit check
            if (data > limit).any():
                exceed_count = (data > limit).sum()
                anomalies.append({
                    'type': '超标检测',
                    'reason': f'{exceed_count} instances exceed limit {limit}'
                })
    
    stats['anomalies'] = anomalies
    return stats


def print_analysis_report(stats):
    """Print formatted analysis report."""
    print("\n" + "="*60)
    print(f"废水监测数据分析报告 - {stats['indicator']}")
    print("="*60)
    print(f"时间范围：{stats['time_range']}")
    print(f"数据点数：{stats['data_points']}")
    print()
    print("【统计指标】")
    print(f"  均值：{stats['mean']:.2f}")
    print(f"  标准差：{stats['std']:.2f}")
    print(f"  最大值：{stats['max']:.2f}")
    print(f"  最小值：{stats['min']:.2f}")
    print(f"  缺失值：{stats['missing']}")
    print()
    
    if stats['anomalies']:
        print("【异常检测】")
        for anomaly in stats['anomalies']:
            print(f"  ⚠️  {anomaly['type']}: {anomaly['reason']}")
    else:
        print("【异常检测】")
        print("  ✅ 未检测到明显异常模式")
    
    print("="*60)


def main():
    """Main recovery and analysis workflow."""
    print("废水监测系统 - 紧急恢复与数据分析脚本")
    print("Emergency Recovery and Data Analysis Script")
    print("="*60)
    
    # Step 1: System health check
    print("\n【步骤 1: 系统健康检查】")
    disk_ok = check_disk_space()
    creds_ok = check_env_credentials()
    
    if not disk_ok:
        print("\n⚠️  磁盘空间不足，正在清理...")
        cleanup_old_sessions(days=3)
        check_disk_space()  # Re-check
    
    # Step 2: Load data
    print("\n【步骤 2: 加载数据】")
    try:
        df = load_data(EFFLUENT_FILE, "effluent")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("尝试加载进水数据...")
        try:
            df = load_data(INFLUENT_FILE, "influent")
        except FileNotFoundError:
            print("❌ 无法找到任何数据文件")
            return
    
    # Step 3: Analyze COD (default indicator)
    print("\n【步骤 3: 分析 COD 指标】")
    stats = analyze_indicator(df, 'COD', hours=24)
    
    if stats:
        print_analysis_report(stats)
    else:
        print("❌ 无法分析 COD 数据")
    
    # Step 4: Offer additional analysis
    print("\n【步骤 4: 其他可用分析】")
    print("可分析的指标：pH, COD, TN, NH3-N, TP, SS, flow_rate")
    print("示例：analyze_indicator(df, 'NH3-N', hours=24)")
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)


if __name__ == "__main__":
    main()

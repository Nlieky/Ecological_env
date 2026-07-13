#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最近 N 小时的进水和出水数据

用法:
    python get_recent_data.py --hours 24 --indicators pH,COD,TN,TP --output recent_data.json

数据来源:
    - E:/project/Ecological_env/data/pollution_water_in.csv (进水)
    - E:/project/Ecological_env/data/pollution_water_out.csv (出水)

注意:
    - CSV 中的列名是 "pH 值"（无空格），不是 "pH 值"（有空格）
    - 数据时间范围是 2024 年全年，脚本自动取最后 N 小时的数据（按条数）
    - 默认数据间隔为 1 小时，24 小时约 24-288 条数据
"""

import pandas as pd
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 数据文件路径
DATA_DIR = Path("E:/project/Ecological_env/data")
INFLUENT_FILE = DATA_DIR / "pollution_water_in.csv"
EFFLUENT_FILE = DATA_DIR / "pollution_water_out.csv"

# 字段名映射：中文字段名到英文字段名
# 注意："pH 值" 是无空格的 3 个字符，不是 "pH 值"（4 个字符，有空格）
FIELD_MAPPING = {
    "监测时间": "timestamp",
    "pH值": "pH",  # 注意：pH和值之间无空格，CSV中实际列名为"pH值"
    "化学需氧量浓度（毫克/升）": "COD",
    "总氮浓度（毫克/升）": "TN",
    "氨氮浓度（毫克/升）": "NH3-N",
    "总磷浓度（毫克/升）": "TP",
    "悬浮物浓度（毫克/升）": "SS",
    "流量（升/秒）": "flow_rate",
    "排放量（吨）": "discharge_volume"
}


def get_recent_data(file_path, hours_back=24, indicators=None):
    """
    获取最近 N 小时的数据
    
    Args:
        file_path: CSV 文件路径
        hours_back: 回溯小时数
        indicators: 需要的指标列表，None 表示全部
    
    Returns:
        List[Dict]: 数据列表
    """
    try:
        df = pd.read_csv(file_path)
        
        # 重命名字段为英文
        df = df.rename(columns=FIELD_MAPPING)
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # 获取最后 N 小时的数据（按条数）
        # 假设数据间隔为 1 小时，N 小时约 N 条数据
        # 如果数据间隔更短（如 5 分钟），则条数更多
        rows_needed = hours_back * 12  # 假设 5 分钟间隔
        recent_data = df.tail(rows_needed)
        
        # 筛选需要的指标
        if indicators:
            available = ['timestamp'] + [i for i in indicators if i in recent_data.columns]
        else:
            available = ['timestamp'] + [c for c in recent_data.columns if c != 'timestamp']
        
        result = recent_data[available].copy()
        
        # 转换为字典列表
        records = []
        for _, row in result.iterrows():
            record = {}
            for col in available:
                value = row[col]
                if pd.isna(value):
                    value = None
                elif col == 'timestamp':
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    try:
                        value = round(float(value), 2)
                    except (ValueError, TypeError):
                        value = None
                record[col] = value
            records.append(record)
        
        return records
        
    except Exception as e:
        print(f"[ERROR] 读取数据失败：{e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取最近 N 小时的水质监测数据')
    parser.add_argument('--hours', type=int, default=24, help='回溯小时数（默认：24）')
    parser.add_argument('--indicators', type=str, default='pH,COD,TN,TP', 
                        help='需要的指标，逗号分隔（默认：pH,COD,TN,TP）')
    parser.add_argument('--output', type=str, default='recent_data.json', 
                        help='输出文件路径（默认：recent_data.json）')
    parser.add_argument('--source', type=str, default='both', 
                        choices=['influent', 'effluent', 'both'],
                        help='数据源：进水/出水/两者（默认：both）')
    
    args = parser.parse_args()
    
    # 解析指标列表
    indicators = [i.strip() for i in args.indicators.split(',')] if args.indicators else None
    
    print(f"获取最近 {args.hours} 小时的数据...")
    print(f"指标：{indicators or '全部'}")
    print(f"数据源：{args.source}")
    
    result = {
        "metadata": {
            "hours_back": args.hours,
            "indicators": indicators,
            "data_source": args.source,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "influent": [],
        "effluent": []
    }
    
    if args.source in ['influent', 'both']:
        print("\n读取进水数据...")
        result['influent'] = get_recent_data(INFLUENT_FILE, args.hours, indicators)
        print(f"  获取到 {len(result['influent'])} 条进水数据")
    
    if args.source in ['effluent', 'both']:
        print("\n读取出水数据...")
        result['effluent'] = get_recent_data(EFFLUENT_FILE, args.hours, indicators)
        print(f"  获取到 {len(result['effluent'])} 条出水数据")
    
    # 保存结果
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已保存到：{output_path.absolute()}")
    
    # 显示统计摘要
    if result['influent']:
        print("\n=== 进水数据摘要 ===")
        show_summary(result['influent'], indicators)
    
    if result['effluent']:
        print("\n=== 出水数据摘要 ===")
        show_summary(result['effluent'], indicators)


def show_summary(data, indicators):
    """显示数据统计摘要"""
    if not data:
        return
    
    print(f"时间范围：{data[0]['timestamp']} 至 {data[-1]['timestamp']}")
    print(f"数据条数：{len(data)}")
    
    if indicators:
        for ind in indicators:
            # 处理 pH 的特殊情况
            key = ind if ind in data[0] else (ind + '值' if ind == 'pH' else ind)
            values = [r.get(key) for r in data if r.get(key) is not None]
            if values:
                print(f"  {ind}: 最小={min(values):.2f}, 最大={max(values):.2f}, 平均={sum(values)/len(values):.2f}")


if __name__ == "__main__":
    main()

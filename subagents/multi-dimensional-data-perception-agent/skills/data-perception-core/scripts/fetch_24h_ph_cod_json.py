#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最近 24 小时进水和出水的 pH、COD 数据
输出 JSON 格式结果
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# 数据文件路径
DATA_DIR = Path("E:/project/Ecological_env/data")
INFLUENT_FILE = DATA_DIR / "pollution_water_in.csv"
EFFLUENT_FILE = DATA_DIR / "pollution_water_out.csv"
OUTPUT_FILE = Path("E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/sessions/data_result.json")

# 字段名映射
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

def get_recent_data(file_path, hours_back=24, indicators=None):
    """获取最近 N 小时的数据"""
    try:
        df = pd.read_csv(file_path)
        df = df.rename(columns=FIELD_MAPPING)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # 获取最后 N 小时的数据（按条数）
        rows_needed = hours_back * 12
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
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"任务 ID: {task_id}")
    print(f"开始获取最近 24 小时的 pH、COD 数据...")
    
    # 获取进水数据
    print("\n读取进水数据...")
    influent_data = get_recent_data(INFLUENT_FILE, hours_back=24, indicators=['pH', 'COD'])
    print(f"  获取到 {len(influent_data)} 条进水数据")
    
    # 获取出水数据
    print("\n读取出水数据...")
    effluent_data = get_recent_data(EFFLUENT_FILE, hours_back=24, indicators=['pH', 'COD'])
    print(f"  获取到 {len(effluent_data)} 条出水数据")
    
    # 构建结果
    result = {
        "task_id": task_id,
        "status": "completed" if (influent_data or effluent_data) else "failed",
        "result": {
            "influent": influent_data,
            "effluent": effluent_data,
            "summary": {
                "influent_count": len(influent_data),
                "effluent_count": len(effluent_data),
                "time_range": {
                    "influent": {
                        "start": influent_data[0]["timestamp"] if influent_data else None,
                        "end": influent_data[-1]["timestamp"] if influent_data else None
                    },
                    "effluent": {
                        "start": effluent_data[0]["timestamp"] if effluent_data else None,
                        "end": effluent_data[-1]["timestamp"] if effluent_data else None
                    }
                }
            }
        },
        "metadata": {
            "subagent": "multi-dimensional-data-perception-agent",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "llm_driven": True,
            "indicators": ["pH", "COD"],
            "time_range_hours": 24,
            "data_sources": ["influent", "effluent"]
        }
    }
    
    # 确保输出目录存在
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到：{OUTPUT_FILE.absolute()}")
    
    # 显示摘要
    if influent_data:
        print("\n=== 进水数据摘要 ===")
        ph_values = [r['pH'] for r in influent_data if r['pH'] is not None]
        cod_values = [r['COD'] for r in influent_data if r['COD'] is not None]
        if ph_values:
            print(f"  pH: 最小={min(ph_values):.2f}, 最大={max(ph_values):.2f}, 平均={sum(ph_values)/len(ph_values):.2f}")
        if cod_values:
            print(f"  COD: 最小={min(cod_values):.2f}, 最大={max(cod_values):.2f}, 平均={sum(cod_values)/len(cod_values):.2f}")
    
    if effluent_data:
        print("\n=== 出水数据摘要 ===")
        ph_values = [r['pH'] for r in effluent_data if r['pH'] is not None]
        cod_values = [r['COD'] for r in effluent_data if r['COD'] is not None]
        if ph_values:
            print(f"  pH: 最小={min(ph_values):.2f}, 最大={max(ph_values):.2f}, 平均={sum(ph_values)/len(ph_values):.2f}")
        if cod_values:
            print(f"  COD: 最小={min(cod_values):.2f}, 最大={max(cod_values):.2f}, 平均={sum(cod_values)/len(cod_values):.2f}")
    
    return result

if __name__ == "__main__":
    main()

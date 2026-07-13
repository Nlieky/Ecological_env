#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最近 24 小时进水和出水数据并返回 JSON 结果
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

# 数据文件路径
DATA_DIR = Path("E:/project/Ecological_env/data")
INFLUENT_FILE = DATA_DIR / "pollution_water_in.csv"
EFFLUENT_FILE = DATA_DIR / "pollution_water_out.csv"

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

def get_recent_data(file_path, hours_back=24):
    """获取最近 N 小时的数据"""
    try:
        df = pd.read_csv(file_path)
        
        # 重命名字段
        df = df.rename(columns=FIELD_MAPPING)
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # 获取最后 N 小时的数据（假设 5 分钟间隔，24 小时约 288 条）
        rows_needed = hours_back * 12
        recent_data = df.tail(rows_needed)
        
        # 选择需要的列
        columns_to_keep = ['timestamp', 'pH', 'COD', 'TN', 'NH3-N', 'TP', 'SS', 'flow_rate', 'discharge_volume']
        available_cols = [c for c in columns_to_keep if c in recent_data.columns]
        
        result = recent_data[available_cols].copy()
        
        # 转换为字典列表
        records = []
        for _, row in result.iterrows():
            record = {}
            for col in available_cols:
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
    
    print(f"获取最近 24 小时的进水和出水数据...")
    print(f"任务 ID: {task_id}")
    
    # 获取进水数据
    influent_data = []
    influent_error = None
    if INFLUENT_FILE.exists():
        influent_data = get_recent_data(INFLUENT_FILE, hours_back=24)
        if not influent_data:
            influent_error = "进水数据为空或读取失败"
    else:
        influent_error = f"进水数据文件不存在：{INFLUENT_FILE}"
    
    # 获取出水数据
    effluent_data = []
    effluent_error = None
    if EFFLUENT_FILE.exists():
        effluent_data = get_recent_data(EFFLUENT_FILE, hours_back=24)
        if not effluent_data:
            effluent_error = "出水数据为空或读取失败"
    else:
        effluent_error = f"出水数据文件不存在：{EFFLUENT_FILE}"
    
    # 构建结果
    result = {
        "task_id": task_id,
        "status": "completed" if (influent_data or effluent_data) else "failed",
        "result": {
            "influent": influent_data,
            "effluent": effluent_data,
            "metadata": {
                "hours_back": 24,
                "indicators": ["pH", "COD", "TN", "NH3-N", "TP", "SS", "flow_rate", "discharge_volume"],
                "data_source": "both"
            }
        },
        "metadata": {
            "subagent": "multi-dimensional-data-perception-agent",
            "timestamp": datetime.now().isoformat(),
            "llm_driven": True
        }
    }
    
    # 添加错误信息（如果有）
    if influent_error:
        result["result"]["influent_error"] = influent_error
    if effluent_error:
        result["result"]["effluent_error"] = effluent_error
    
    # 打印统计信息
    print(f"\n=== 数据统计 ===")
    if influent_data:
        print(f"进水数据：{len(influent_data)} 条")
        print(f"  时间范围：{influent_data[0]['timestamp']} 至 {influent_data[-1]['timestamp']}")
    else:
        print(f"进水数据：无 ({influent_error})")
    
    if effluent_data:
        print(f"出水数据：{len(effluent_data)} 条")
        print(f"  时间范围：{effluent_data[0]['timestamp']} 至 {effluent_data[-1]['timestamp']}")
    else:
        print(f"出水数据：无 ({effluent_error})")
    
    # 输出 JSON 结果
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    print(f"\n=== JSON 输出 ===")
    print(output_json)
    
    # 保存到文件
    output_file = Path("E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到：{output_file}")

if __name__ == "__main__":
    main()

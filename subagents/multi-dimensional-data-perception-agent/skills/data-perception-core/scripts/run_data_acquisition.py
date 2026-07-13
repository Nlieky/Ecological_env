#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多维数据感知脚本 - 从 CSV 文件获取废水监测数据

数据源：
- E:/project/Ecological_env/data/pollution_water_in.csv（进水）
- E:/project/Ecological_env/data/pollution_water_out.csv（出水）

输出格式：
- 标准化的 JSON 数据
- 包含时间戳、指标名称、数值
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path("E:/project/Ecological_env")
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据文件路径
DATA_DIR = PROJECT_ROOT / "data"
INFLUENT_FILE = DATA_DIR / "pollution_water_in.csv"
EFFLUENT_FILE = DATA_DIR / "pollution_water_out.csv"


# 字段映射：CSV 列名 → 标准字段名
INFLUENT_FIELDS = {
    'pH值': 'pH',
    '化学需氧量浓度（毫克/升）': 'COD',
    '总氮浓度（毫克/升）': 'TN',
    '氨氮浓度（毫克/升）': 'NH3_N',
    '总磷浓度（毫克/升）': 'TP'
}

EFFLUENT_FIELDS = {
    'pH值': 'pH',
    '悬浮物浓度（毫克/升）': 'SS',
    '化学需氧量浓度（毫克/升）': 'COD',
    '总氮浓度（毫克/升）': 'TN',
    '氨氮浓度（毫克/升）': 'NH3_N',
    '总磷浓度（毫克/升）': 'TP',
    '流量（升/秒）': 'Flow'
}


def parse_time_range(time_range: str) -> tuple:
    """解析时间范围字符串，返回 (start_index, count)

    支持格式：
    - "24h" -> 最近 24 小时（约 288 条，5 分钟间隔）
    - "48h" -> 最近 48 小时
    - "7d" -> 最近 7 天
    - "all" -> 全部数据
    """
    time_range = time_range.lower().strip()

    if time_range == "all":
        return 0, None  # 从开始读取全部

    # 计算记录数（假设 5 分钟间隔）
    records_per_hour = 12

    if time_range.endswith("h"):
        hours = int(time_range[:-1])
        count = hours * records_per_hour
        return -count, count  # 从倒数第 count 条开始

    if time_range.endswith("d"):
        days = int(time_range[:-1])
        count = days * 24 * records_per_hour
        return -count, count

    # 默认返回最近 24 小时
    return -288, 288


def load_csv_data(file_path: Path, fields_mapping: dict) -> list:
    """加载 CSV 数据并转换为标准格式"""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"加载数据文件: {file_path.name}, 记录数: {len(df)}")
    except Exception as e:
        logger.error(f"加载失败: {e}")
        return []

    # 检查时间列
    time_col = None
    for col in df.columns:
        if '时间' in col or 'time' in col.lower():
            time_col = col
            break

    if time_col is None:
        logger.warning(f"未找到时间列，使用索引")
        time_col = df.columns[0]

    # 转换数据
    data = []
    for idx, row in df.iterrows():
        record = {'index': idx}

        # 解析时间
        try:
            time_str = str(row[time_col]).strip()
            # 格式如 "2024-01-01 00"
            if ' ' in time_str:
                date_part, hour_part = time_str.split()
                time_str = f"{date_part} {hour_part.zfill(2)}:00:00"
            record['timestamp'] = time_str
        except:
            record['timestamp'] = f"2024-01-01 {str(idx).zfill(2)}:00:00"

        # 转换指标字段
        for csv_field, std_field in fields_mapping.items():
            if csv_field in df.columns:
                try:
                    value = float(row[csv_field])
                    if value != '/':  # 跳过缺失值
                        record[std_field] = value
                except:
                    pass

        data.append(record)

    return data


def filter_data(data: list, start_idx: int, count: int, indicators: list = None) -> list:
    """筛选数据"""
    # 确定起止索引
    if start_idx < 0:
        start_idx = max(0, len(data) + start_idx)

    if count is None:
        end_idx = len(data)
    else:
        end_idx = min(len(data), start_idx + count)

    filtered = data[start_idx:end_idx]

    # 如果指定了指标，只保留这些指标
    if indicators:
        result = []
        for record in filtered:
            filtered_record = {'timestamp': record.get('timestamp')}
            for indicator in indicators:
                if indicator in record:
                    filtered_record[indicator] = record[indicator]
            result.append(filtered_record)
        return result

    return filtered


def get_data_summary(influent_data: list, effluent_data: list) -> dict:
    """生成数据摘要"""
    # 收集所有指标名称
    influent_indicators = set()
    effluent_indicators = set()

    for d in influent_data:
        if d:
            influent_indicators.update(d.keys())

    for d in effluent_data:
        if d:
            effluent_indicators.update(d.keys())

    # 移除非指标字段
    for fields in [influent_indicators, effluent_indicators]:
        fields.discard('index')
        fields.discard('timestamp')

    return {
        'influent_records': len(influent_data),
        'effluent_records': len(effluent_data),
        'influent_indicators': list(influent_indicators),
        'effluent_indicators': list(effluent_indicators),
        'time_range': f"{influent_data[0].get('timestamp', '')} ~ {influent_data[-1].get('timestamp', '')}" if influent_data else ""
    }


def main():
    """主函数"""
    # 从环境变量或参数获取配置
    time_range = sys.argv[1] if len(sys.argv) > 1 else "24h"
    indicators = sys.argv[2].split(',') if len(sys.argv) > 2 else None

    logger.info(f"数据获取参数: time_range={time_range}, indicators={indicators}")

    # 解析时间范围
    start_idx, count = parse_time_range(time_range)

    # 加载数据
    influent_data = load_csv_data(INFLUENT_FILE, INFLUENT_FIELDS)
    effluent_data = load_csv_data(EFFLUENT_FILE, EFFLUENT_FIELDS)

    # 筛选数据
    if start_idx != 0 or count is not None:
        influent_data = filter_data(influent_data, start_idx, count, indicators)
        effluent_data = filter_data(effluent_data, start_idx, count, indicators)

    # 生成摘要
    summary = get_data_summary(influent_data, effluent_data)

    # 构建结果
    result = {
        'status': 'completed',
        'data': {
            'influent': influent_data,
            'effluent': effluent_data
        },
        'summary': summary,
        'metadata': {
            'source': 'CSV files',
            'influent_file': str(INFLUENT_FILE),
            'effluent_file': str(EFFLUENT_FILE),
            'timestamp': datetime.now().isoformat()
        }
    }

    # 输出 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用数据获取脚本 - 支持命令行参数

使用方法:
    python get_data.py --hours 24
    python get_data.py --days 7
    python get_data.py --start "2024-01-01" --end "2024-01-02"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 数据文件路径
DATA_DIR = Path("E:/project/Ecological_env/data")
INFLUENT_FILE = DATA_DIR / "pollution_water_in.csv"
EFFLUENT_FILE = DATA_DIR / "pollution_water_out.csv"

# 字段名映射
FIELD_MAPPING = {
    "监测时间": "timestamp",
    "pH值": "pH",
    "化学需氧量浓度（毫克/升）": "COD",
    "总氮浓度（毫克/升）": "TN",
    "氨氮浓度（毫克/升）": "NH3-N",
    "总磷浓度（毫克/升）": "TP",
    "悬浮物浓度（毫克/升）": "SS",
    "流量（升/秒）": "flow_rate",
    "排放量（吨）": "discharge_volume"
}


def get_data_by_hours(file_path, hours_back=24):
    """获取最近 N 小时的数据"""
    try:
        import pandas as pd

        df = pd.read_csv(file_path)

        # 重命名字段
        df = df.rename(columns=FIELD_MAPPING)

        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 获取最后 N 小时的数据（数据为小时级，1条/小时）
        rows_needed = hours_back
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
        print(f"[ERROR] 读取数据失败：{e}", file=sys.stderr)
        return []


def get_data_by_range(file_path, start_time, end_time):
    """获取指定时间范围的数据"""
    try:
        import pandas as pd

        df = pd.read_csv(file_path)

        # 重命名字段
        df = df.rename(columns=FIELD_MAPPING)

        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 过滤时间范围
        start_dt = pd.to_datetime(start_time)
        end_dt = pd.to_datetime(end_time)

        mask = (df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)
        filtered_data = df.loc[mask]

        # 选择需要的列
        columns_to_keep = ['timestamp', 'pH', 'COD', 'TN', 'NH3-N', 'TP', 'SS', 'flow_rate', 'discharge_volume']
        available_cols = [c for c in columns_to_keep if c in filtered_data.columns]

        result = filtered_data[available_cols].copy()

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
        print(f"[ERROR] 读取数据失败：{e}", file=sys.stderr)
        return []


def _infer_hours_from_task():
    """从 SESSION_DIR/task.json 的任务描述里确定性推断时间范围（小时）。

    LLM（ctgu-vlm）不一定可靠地把"一周"换成 --hours 168（时灵时不灵），这里做
    确定性兜底：只要任务描述里提到时间范围，就按规则换算。LLM 显式传了 --hours/--days
    时优先用显式值；没传时才走这里。
    """
    import re
    sd = os.environ.get('SESSION_DIR')
    if not sd:
        return None
    try:
        tj = Path(sd) / "task.json"
        if not tj.exists():
            return None
        data = json.load(open(tj, encoding='utf-8'))
        text = (data.get("task") or "")
        if isinstance(text, dict):
            text = json.dumps(text, ensure_ascii=False)
        text = str(text).strip()
        if not text:
            return None
    except Exception:
        return None

    # 明确数字：N 小时 / N 天
    m = re.search(r'(\d+)\s*小时', text)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:天|日)', text)
    if m:
        return int(m.group(1)) * 24
    # 中文范围词
    if re.search(r'两 ?周|14\s*天', text):
        return 336
    if re.search(r'一 ?周|本 ?周|七 ?天|7\s*天|近 ?一 ?周', text):
        return 168
    if re.search(r'本 ?月|一 ?个 ?月|近 ?一 ?个 ?月|30\s*天', text):
        return 720
    if re.search(r'昨', text):
        return 24
    return None


def main():
    parser = argparse.ArgumentParser(description='获取监测数据')
    parser.add_argument('--hours', type=int, help='最近N小时')
    parser.add_argument('--days', type=int, help='最近N天')
    parser.add_argument('--start', type=str, help='开始时间 (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, help='结束时间 (YYYY-MM-DD HH:MM:SS)')

    args = parser.parse_args()

    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 计算时间范围
    hours_back = None
    # 优先从任务描述确定性推断：LLM 不一定可靠地把"一周"换成 --hours 168（时灵时不灵），
    # 故只要任务里提到时间范围，就以任务为准——覆盖 LLM 可能传错的 --hours/--days。
    inferred = _infer_hours_from_task()
    if inferred:
        hours_back = inferred
        if args.hours or args.days:
            print(f"[推断] 任务描述含时间范围，以任务为准（{inferred} 小时），忽略 --hours/--days")
    elif args.hours:
        hours_back = args.hours
    elif args.days:
        hours_back = args.days * 24

    # 获取数据
    influent_data = []
    effluent_data = []
    influent_error = None
    effluent_error = None

    if hours_back:
        # 使用小时数获取数据
        print(f"获取最近 {hours_back} 小时的数据...")

        if INFLUENT_FILE.exists():
            influent_data = get_data_by_hours(INFLUENT_FILE, hours_back)
            if not influent_data:
                influent_error = "进水数据为空或读取失败"
        else:
            influent_error = f"进水数据文件不存在：{INFLUENT_FILE}"

        if EFFLUENT_FILE.exists():
            effluent_data = get_data_by_hours(EFFLUENT_FILE, hours_back)
            if not effluent_data:
                effluent_error = "出水数据为空或读取失败"
        else:
            effluent_error = f"出水数据文件不存在：{EFFLUENT_FILE}"

        time_range_str = f"最近{hours_back}小时"

    elif args.start and args.end:
        # 使用时间范围获取数据
        print(f"获取 {args.start} 至 {args.end} 的数据...")

        if INFLUENT_FILE.exists():
            influent_data = get_data_by_range(INFLUENT_FILE, args.start, args.end)
            if not influent_data:
                influent_error = "进水数据为空或读取失败"
        else:
            influent_error = f"进水数据文件不存在：{INFLUENT_FILE}"

        if EFFLUENT_FILE.exists():
            effluent_data = get_data_by_range(EFFLUENT_FILE, args.start, args.end)
            if not effluent_data:
                effluent_error = "出水数据为空或读取失败"
        else:
            effluent_error = f"出水数据文件不存在：{EFFLUENT_FILE}"

        time_range_str = f"{args.start} 至 {args.end}"

    else:
        # 默认24小时
        print(f"获取最近 24 小时的数据...")
        hours_back = 24

        if INFLUENT_FILE.exists():
            influent_data = get_data_by_hours(INFLUENT_FILE, hours_back)
            if not influent_data:
                influent_error = "进水数据为空或读取失败"
        else:
            influent_error = f"进水数据文件不存在：{INFLUENT_FILE}"

        if EFFLUENT_FILE.exists():
            effluent_data = get_data_by_hours(EFFLUENT_FILE, hours_back)
            if not effluent_data:
                effluent_error = "出水数据为空或读取失败"
        else:
            effluent_error = f"出水数据文件不存在：{EFFLUENT_FILE}"

        time_range_str = f"最近24小时"

    # 构建结果
    result = {
        "task_id": task_id,
        "status": "completed" if (influent_data or effluent_data) else "failed",
        "result": {
            "influent": influent_data,
            "effluent": effluent_data,
            "metadata": {
                "time_range": time_range_str,
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

    # 保存到会话目录（优先）或子智能体目录
    # 注意：不打印完整 JSON 到 stdout，避免 LLM 处理大量数据
    session_dir = os.environ.get('SESSION_DIR')
    if session_dir:
        output_file = Path(session_dir) / "data_result.json"
    else:
        output_file = Path("E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到：{output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

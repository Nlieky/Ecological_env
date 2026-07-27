#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双数据流发送器 - 发送进水和出水数据到Flask中间件
处理2小时时间滞后（脚本实现）
"""

import time
import logging
import requests
from datetime import datetime
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 配置
DATA_DIR = Path(__file__).resolve().parents[1] / 'shared' / 'data'
INFLUENT_FILE = 'pollution_water_in.csv'
EFFLUENT_FILE = 'pollution_water_out.csv'
API_ENDPOINT = 'http://localhost:5000/api/dual-stream'
LAG_HOURS = 2  # 出水滞后时间
SPEED_FACTOR = 60  # 加速因子（60倍 = 1分钟模拟1小时）
ALIGN_BY_TIME = True  # 是否按时间对齐（推荐：True）

# 数据间隔5分钟，计算滞后记录数
LAG_RECORDS = int(LAG_HOURS * 60 / 5)  # 2小时 = 24条记录


def load_data():
    """加载CSV数据"""
    influent_path = DATA_DIR / INFLUENT_FILE
    effluent_path = DATA_DIR / EFFLUENT_FILE

    logger.info(f"加载进水数据: {influent_path}")
    influent_df = pd.read_csv(influent_path)

    logger.info(f"加载出水数据: {effluent_path}")
    effluent_df = pd.read_csv(effluent_path)

    logger.info(f"进水记录: {len(influent_df)}, 出水记录: {len(effluent_df)}")
    logger.info(f"滞后配置: {LAG_HOURS}小时 = {LAG_RECORDS}条记录")

    # 检查时间戳范围
    if '监测时间' in influent_df.columns and '监测时间' in effluent_df.columns:
        influent_start = influent_df['监测时间'].iloc[0]
        influent_end = influent_df['监测时间'].iloc[-1]
        effluent_start = effluent_df['监测时间'].iloc[0]
        effluent_end = effluent_df['监测时间'].iloc[-1]

        logger.info(f"进水时间范围: {influent_start} ~ {influent_end}")
        logger.info(f"出水时间范围: {effluent_start} ~ {effluent_end}")

        # 警告时间不匹配
        if influent_start.split()[0] != effluent_start.split()[0]:
            logger.warning("⚠️  警告: 进水和出水数据的日期不匹配！")
            logger.warning(f"   进水起始日期: {influent_start.split()[0]}")
            logger.warning(f"   出水起始日期: {effluent_start.split()[0]}")
            logger.warning("   系统将按索引对齐，可能导致时间逻辑错误")

    return influent_df, effluent_df


def send_data(influent_row, effluent_row):
    """发送数据到Flask"""
    payload = {
        'influent': influent_row.to_dict(),
        'effluent': effluent_row.to_dict(),
        'timestamp': datetime.now().isoformat()
    }

    try:
        resp = requests.post(API_ENDPOINT, json=payload, timeout=5)
        if resp.status_code == 200:
            return True
        else:
            logger.warning(f"发送失败: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"发送错误: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("双数据流发送器启动")
    logger.info(f"API端点: {API_ENDPOINT}")
    logger.info(f"滞后: {LAG_HOURS}小时 ({LAG_RECORDS}条记录)")
    logger.info(f"对齐模式: 索引对齐（进水索引i对应出水索引i-{LAG_RECORDS}）")
    logger.info("=" * 50)

    influent_df, effluent_df = load_data()

    # 使用完整数据集
    logger.info(f"使用完整数据集: 进水{len(influent_df)}条, 出水{len(effluent_df)}条")

    # 显示时间范围
    if '监测时间' in influent_df.columns:
        logger.info(f"进水时间范围: {influent_df['监测时间'].iloc[0]} ~ {influent_df['监测时间'].iloc[-1]}")
    if '监测时间' in effluent_df.columns:
        logger.info(f"出水时间范围: {effluent_df['监测时间'].iloc[0]} ~ {effluent_df['监测时间'].iloc[-1]}")

    # 计算实际可发送的数据条数（考虑出水延迟）
    # 进水索引i对应出水索引i+LAG_RECORDS（2小时后）
    max_influent_idx = len(influent_df) - LAG_RECORDS - 1
    total = max(0, min(max_influent_idx, len(effluent_df) - LAG_RECORDS - 1))

    if total <= 0:
        logger.error(f"数据不足：无法进行时间对齐（需要至少{LAG_RECORDS+1}条出水数据）")
        return

    success = 0
    failed = 0

    for i in range(total):
        # 进水记录
        influent_row = influent_df.iloc[i]

        # 出水记录（工艺逻辑：进水时间T对应出水时间T+2小时）
        # 即：进水索引i对应出水索引i+LAG_RECORDS
        effluent_idx = i + LAG_RECORDS
        effluent_row = effluent_df.iloc[effluent_idx]

        # 发送
        if send_data(influent_row, effluent_row):
            success += 1
        else:
            failed += 1

        # 进度
        if (i + 1) % 50 == 0:
            logger.info(f"进度: {i+1}/{total}, 成功: {success}, 失败: {failed}")

        # 模拟时间间隔
        time.sleep(60 / SPEED_FACTOR)

    logger.info("=" * 50)
    logger.info(f"完成! 总计: {total}, 成功: {success}, 失败: {failed}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()

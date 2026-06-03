#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双数据流发送器
功能：读取进水和出水CSV文件，处理时间滞后，发送到Flask中间件

基于专利：主动监测模式的数据流模拟
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class DualStreamSimulator:
    """
    双数据流模拟器

    功能：
    1. 读取进水和出水CSV文件
    2. 处理时间滞后（可配置）
    3. 模拟实时数据流发送
    4. 支持异常注入（测试用）
    """

    def __init__(self, config=None):
        """初始化双数据流模拟器"""
        self.name = "双数据流模拟器"
        self.version = "2.0.0"

        # 默认配置
        default_config = {
            'data_dir': 'E:/project/Ecological_env/data',
            'influent_file': 'pollution_water_in.csv',
            'effluent_file': 'pollution_water_out.csv',
            'api_endpoint': 'http://localhost:5000/api/dual-stream',  # 修正API端点
            'lag_hours': 2,  # 出水滞后时间（小时）
            'speed_factor': 60,  # 加速因子（1=实时，60=1分钟模拟1小时）
            'batch_size': 1,  # 每次发送的记录数
            'infinite_loop': True,  # 是否无限循环
            'inject_anomalies': False,  # 是否注入异常数据
            'request_timeout': 5  # 请求超时时间（秒）
        }

        self.config = {**default_config, **(config or {})}

        # 数据文件路径
        self.influent_path = Path(self.config['data_dir']) / self.config['influent_file']
        self.effluent_path = Path(self.config['data_dir']) / self.config['effluent_file']

        # 数据
        self.influent_data = None
        self.effluent_data = None
        self.lag_records = None  # 滞后记录数

        logger.info(f"[INIT] {self.name} v{self.version} initialized")
        logger.info(f"[INIT] 进水文件: {self.influent_path}")
        logger.info(f"[INIT] 出水文件: {self.effluent_path}")
        logger.info(f"[INIT] 滞后时间: {self.config['lag_hours']} 小时")
        logger.info(f"[INIT] 加速因子: {self.config['speed_factor']}x")
        logger.info(f"[INIT] API端点: {self.config['api_endpoint']}")

    def load_data(self):
        """加载CSV数据"""
        logger.info("[LOAD] 加载数据文件...")

        try:
            # 读取进水数据
            if self.influent_path.exists():
                self.influent_data = pd.read_csv(self.influent_path)
                # 重命名时间列
                if '监测时间' in self.influent_data.columns:
                    self.influent_data.rename(columns={'监测时间': 'times'}, inplace=True)
                self.influent_data['times'] = pd.to_datetime(self.influent_data['times'])
                logger.info(f"[LOAD] 进水数据: {len(self.influent_data)} 条记录")
            else:
                raise FileNotFoundError(f"进水数据文件不存在: {self.influent_path}")

            # 读取出水数据
            if self.effluent_path.exists():
                self.effluent_data = pd.read_csv(self.effluent_path)
                # 重命名时间列
                if '监测时间' in self.effluent_data.columns:
                    self.effluent_data.rename(columns={'监测时间': 'times'}, inplace=True)
                self.effluent_data['times'] = pd.to_datetime(self.effluent_data['times'])
                logger.info(f"[LOAD] 出水数据: {len(self.effluent_data)} 条记录")
            else:
                raise FileNotFoundError(f"出水数据文件不存在: {self.effluent_path}")

            # 计算滞后记录数
            lag_minutes = self.config['lag_hours'] * 60
            # 假设数据间隔为5分钟
            records_per_minute = 1 / 5  # 每分钟0.2条记录
            self.lag_records = int(lag_minutes / 5)  # 滞后的记录数

            logger.info(f"[LOAD] 滞后记录数: {self.lag_records}")

        except Exception as e:
            logger.error(f"[LOAD] 加载数据失败: {e}")
            raise

    def inject_anomaly(self, data, anomaly_type='constant'):
        """
        注入异常数据（测试用）

        Args:
            data: 数据字典
            anomaly_type: 异常类型
                - 'constant': 恒定值（插瓶干扰）
                - 'spike': 突变
                - 'dilution': 稀释排放
        """
        if not self.config['inject_anomalies']:
            return data

        if anomaly_type == 'constant':
            # 恒定值异常（插瓶干扰）
            data['pH值'] = 7.2
            data['化学需氧量浓度（毫克/升）'] = 45.0

        elif anomaly_type == 'spike':
            # 突变异常
            data['化学需氧量浓度（毫克/升）'] *= 1.5

        elif anomaly_type == 'dilution':
            # 稀释排放
            for key in ['化学需氧量浓度（毫克/升）', '总氮浓度（毫克/升）',
                       '氨氮浓度（毫克/升）', '总磷浓度（毫克/升）']:
                if key in data:
                    data[key] *= 0.5

        return data

    def send_data(self, influent_record, effluent_record):
        """
        发送数据到Flask中间件

        Args:
            influent_record: 进水记录
            effluent_record: 出水记录
        """
        payload = {
            'influent': influent_record.to_dict(),
            'effluent': effluent_record.to_dict(),
            'timestamp': datetime.now().isoformat()
        }

        try:
            response = requests.post(
                self.config['api_endpoint'],
                json=payload,
                timeout=self.config['request_timeout']
            )

            if response.status_code == 200:
                logger.debug(f"[SEND] 数据发送成功: {payload['timestamp']}")
                return True
            else:
                logger.warning(f"[SEND] 发送失败: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"[SEND] 请求超时")
            return False
        except Exception as e:
            logger.error(f"[SEND] 发送失败: {e}")
            return False

    def simulate(self):
        """开始模拟数据流"""
        logger.info("=" * 60)
        logger.info("开始模拟双数据流")
        logger.info("=" * 60)

        # 加载数据
        self.load_data()

        # 数据长度
        min_length = min(len(self.influent_data), len(self.effluent_data))

        # 发送统计
        sent_count = 0
        success_count = 0
        failed_count = 0

        # 模拟循环
        loop_count = 0
        max_loops = float('inf') if self.config['infinite_loop'] else min_length

        while loop_count < max_loops:
            for i in range(min_length):
                # 获取进水记录
                influent_record = self.influent_data.iloc[i]

                # 获取出水记录（考虑滞后）
                effluent_index = max(0, i - self.lag_records)
                effluent_record = self.effluent_data.iloc[effluent_index]

                # 注入异常（如果启用）
                if self.config['inject_anomalies'] and i % 100 == 0:
                    influent_record = self.inject_anomaly(
                        influent_record.to_dict(),
                        anomaly_type='constant'
                    )
                    influent_record = pd.Series(influent_record)

                # 发送数据
                if self.send_data(influent_record, effluent_record):
                    success_count += 1
                else:
                    failed_count += 1

                sent_count += 1

                # 日志
                if sent_count % 10 == 0:
                    logger.info(f"[PROGRESS] 已发送: {sent_count} | "
                               f"成功: {success_count} | 失败: {failed_count}")

                # 模拟时间间隔（加速模式）
                if self.config['speed_factor'] > 1:
                    # 计算模拟延迟
                    delay = 60 / self.config['speed_factor']  # 秒
                    time.sleep(delay)
                else:
                    time.sleep(1)  # 实时模式，每秒发送一次

            loop_count += 1

            # 如果不是无限循环，退出
            if not self.config['infinite_loop']:
                break

            # 重新开始
            logger.info("[LOOP] 重新开始数据流循环...")

        # 最终统计
        logger.info("=" * 60)
        logger.info("模拟完成")
        logger.info(f"总计发送: {sent_count}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"成功率: {success_count/sent_count*100:.2f}%")
        logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='双数据流模拟器')
    parser.add_argument('--lag', type=float, default=2,
                       help='出水滞后时间（小时）')
    parser.add_argument('--speed', type=int, default=60,
                       help='加速因子（1=实时）')
    parser.add_argument('--once', action='store_true',
                       help='只发送一次数据后退出')
    parser.add_argument('--anomaly', action='store_true',
                       help='注入异常数据')

    args = parser.parse_args()

    # 创建配置
    config = {
        'lag_hours': args.lag,
        'speed_factor': args.speed,
        'infinite_loop': not args.once,
        'inject_anomalies': args.anomaly
    }

    # 创建模拟器
    simulator = DualStreamSimulator(config)

    # 开始模拟
    try:
        simulator.simulate()
    except KeyboardInterrupt:
        logger.info("\n[STOP] 用户中断，停止模拟")
    except Exception as e:
        logger.error(f"[ERROR] 模拟失败: {e}")
        raise


if __name__ == '__main__':
    main()

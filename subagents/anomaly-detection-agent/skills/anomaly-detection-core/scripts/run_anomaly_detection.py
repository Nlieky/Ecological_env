#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测执行脚本
功能：获取最近 24 小时数据并执行异常检测
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# 添加技能目录到路径
skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))

from scripts.anomaly_scorer import AnomalyScorer
from scripts.operator_mapping import OperatorMapping
from scripts.robust_estimator import RobustEstimator
from scripts.pattern_recognizer import PatternRecognizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_recent_data(hours: int = 24) -> dict:
    """
    加载最近 N 小时的进水出水数据
    
    Args:
        hours: 小时数
        
    Returns:
        包含 influent 和 effluent 数据的字典
    """
    data_dir = skill_dir.parent.parent / "data"
    inflow_file = data_dir / "pollution_water_in.csv"
    outflow_file = data_dir / "pollution_water_out.csv"
    
    logger.info(f"加载最近{hours}小时数据...")
    
    # 读取数据
    try:
        df_in = pd.read_csv(inflow_file, encoding='utf-8-sig')
        df_out = pd.read_csv(outflow_file, encoding='utf-8-sig')
    except Exception as e:
        logger.error(f"读取数据文件失败：{e}")
        return {"influent": [], "effluent": []}
    
    # 解析时间列
    time_col_in = '监测时间' if '监测时间' in df_in.columns else 'times'
    time_col_out = '监测时间' if '监测时间' in df_out.columns else 'times'
    
    df_in[time_col_in] = pd.to_datetime(df_in[time_col_in])
    df_out[time_col_out] = pd.to_datetime(df_out[time_col_out])
    
    # 获取最近 24 小时数据
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    df_in_recent = df_in[df_in[time_col_in] >= cutoff_time].copy()
    df_out_recent = df_out[df_out[time_col_out] >= cutoff_time].copy()
    
    logger.info(f"进水数据：{len(df_in_recent)} 条记录")
    logger.info(f"出水数据：{len(df_out_recent)} 条记录")
    
    # 转换为字典列表
    influent_data = df_in_recent.to_dict('records')
    effluent_data = df_out_recent.to_dict('records')
    
    return {
        "influent": influent_data,
        "effluent": effluent_data,
        "influent_df": df_in_recent,
        "effluent_df": df_out_recent
    }


def detect_anomalies(data: dict, indicators: list = None) -> dict:
    """
    执行异常检测
    
    Args:
        data: 数据字典
        indicators: 要检测的指标列表
        
    Returns:
        异常检测结果
    """
    logger.info("开始异常检测...")
    
    # 初始化组件
    scorer = AnomalyScorer()
    operator_mapper = OperatorMapping()
    estimator = RobustEstimator()
    pattern_recognizer = PatternRecognizer()
    
    all_anomalies = []
    
    # 处理进水和出水数据
    for data_type, df in [("influent", data.get("influent_df")), 
                          ("effluent", data.get("effluent_df"))]:
        if df is None or len(df) == 0:
            logger.warning(f"{data_type} 数据为空，跳过")
            continue
        
        # 确定要检测的指标
        if indicators is None:
            # 默认检测所有数值型指标
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            # 排除流量和排放量
            exclude_cols = ['流量（升/秒）', '排放量（吨）']
            available_indicators = [col for col in numeric_cols if col not in exclude_cols]
        else:
            available_indicators = [ind for ind in indicators if ind in df.columns]
        
        logger.info(f"检测指标：{available_indicators}")
        
        # 对每个指标执行异常检测
        for indicator in available_indicators:
            values = df[indicator].values
            
            if len(values) < 10:
                logger.warning(f"{indicator} 数据点不足（{len(values)}），跳过")
                continue
            
            # 使用多个算子检测
            operator_results = {}
            
            # 1. Z-score 算子
            zscore_result = operator_mapper.apply_operator('zscore', values)
            operator_results['zscore'] = zscore_result
            
            # 2. IQR 算子
            iqr_result = operator_mapper.apply_operator('iqr', values)
            operator_results['iqr'] = iqr_result
            
            # 3. 孤立森林算子
            if len(values) >= 100:
                if_result = operator_mapper.apply_operator('isolation_forest', values)
                operator_results['isolation_forest'] = if_result
            
            # 计算异常分数
            scores_result = scorer.calculate_scores(df[[indicator, '监测时间' if '监测时间' in df.columns else 'times']], 
                                                   operator_results)
            
            # 识别异常模式
            for anomaly_moment in scores_result.get('anomaly_moments', []):
                anomaly = {
                    "data_type": data_type,
                    "indicator": indicator,
                    "timestamp": str(anomaly_moment.get('times', '')),
                    "type": pattern_recognizer.recognize_pattern(values, anomaly_moment['index']),
                    "score": anomaly_moment['score'],
                    "value": float(values[anomaly_moment['index']]),
                    "expected_range": [
                        float(np.percentile(values, 25)),
                        float(np.percentile(values, 75))
                    ]
                }
                all_anomalies.append(anomaly)
    
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
        
        if not data['influent'] and not data['effluent']:
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
                    "influent": len(data.get('influent', [])),
                    "effluent": len(data.get('effluent', []))
                }
            }
        }
        
        # 4. 输出 JSON 结果
        print(json.dumps(output, ensure_ascii=False, indent=2))
        
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
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask中间件 - 接收双数据流，暴露Prometheus指标，实时异常检测
匹配现有Grafana仪表板 stream_01.json

基于Orchestrator架构：
- 数据到达 → RealtimeOrchestrator协调4个子智能体协同分析
- 数据治理子智能体 → 特征分析子智能体 → 异常检测子智能体 → 规则推理子智能体
"""

import logging
import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

# 添加realtime编排器路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests', 'realtime'))
from realtime_orchestrator import create_realtime_orchestrator, process_realtime_data_sync

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==================== Prometheus 指标 ====================

# 进水指标 (5个基础 + 流量 + 排放量)
influent_ph = Gauge('wastewater_influent_ph', '进水pH值')
influent_cod = Gauge('wastewater_influent_cod', '进水化学需氧量(mg/L)')
influent_tn = Gauge('wastewater_influent_tn', '进水总氮(mg/L)')
influent_an = Gauge('wastewater_influent_an', '进水氨氮(mg/L)')
influent_tp = Gauge('wastewater_influent_tp', '进水总磷(mg/L)')
influent_flow_rate = Gauge('wastewater_influent_flow_rate', '进水流量(升/秒)')
influent_discharge_volume = Gauge('wastewater_influent_discharge_volume', '进水排放量(吨)')

# 出水指标 (5个基础 + 流量 + 排放量 + 悬浮物)
effluent_ph = Gauge('wastewater_effluent_ph', '出水pH值')
effluent_cod = Gauge('wastewater_effluent_cod', '出水化学需氧量(mg/L)')
effluent_tn = Gauge('wastewater_effluent_tn', '出水总氮(mg/L)')
effluent_an = Gauge('wastewater_effluent_an', '出水氨氮(mg/L)')
effluent_tp = Gauge('wastewater_effluent_tp', '出水总磷(mg/L)')
effluent_flow_rate = Gauge('wastewater_effluent_flow_rate', '出水流量(升/秒)')
effluent_discharge_volume = Gauge('wastewater_effluent_discharge_volume', '出水排放量(吨)')
effluent_suspended_solids = Gauge('wastewater_effluent_suspended_solids', '出水悬浮物(mg/L)')

# 计数器
data_processed = Counter('wastewater_data_processed_total', '数据处理总数', ['status'])
anomaly_detected = Counter('wastewater_anomaly_detected_total', '异常检测总数', ['anomaly_type'])

# 实时分析告警计数器
alert_total = Counter('wastewater_alert_total', '实时告警总数', ['pattern_type', 'level'])

# 创建实时编排器实例（基于Orchestrator架构，协调4个子智能体）
realtime_orchestrator = create_realtime_orchestrator(window_size=24)


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'wastewater_middleware'
    })


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus指标端点"""
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


def safe_float(value, default=None):
    """安全转换为浮点数，处理缺失值"""
    if value is None:
        return default
    val_str = str(value).strip()
    if val_str in ['/', '', 'NA', 'N/A', 'null', 'None']:
        return default
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return default


@app.route('/api/dual-stream', methods=['POST'])
def receive_dual_stream():
    """
    接收双数据流并触发实时分析
    Body: {
        "influent": { "pH值": 7.5, "化学需氧量浓度（毫克/升）": 45, ... },
        "effluent": { "pH值": 7.8, "化学需氧量浓度（毫克/升）": 50, ... },
        "timestamp": "2024-01-01T00:00:00"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400

        influent = data.get('influent', {})
        effluent = data.get('effluent', {})

        # 更新进水指标
        ph_val = safe_float(influent.get('pH值'))
        if ph_val is not None:
            influent_ph.set(ph_val)

        cod_val = safe_float(influent.get('化学需氧量浓度（毫克/升）'))
        if cod_val is not None:
            influent_cod.set(cod_val)

        tn_val = safe_float(influent.get('总氮浓度（毫克/升）'))
        if tn_val is not None:
            influent_tn.set(tn_val)

        an_val = safe_float(influent.get('氨氮浓度（毫克/升）'))
        if an_val is not None:
            influent_an.set(an_val)

        tp_val = safe_float(influent.get('总磷浓度（毫克/升）'))
        if tp_val is not None:
            influent_tp.set(tp_val)

        flow_val = safe_float(influent.get('流量（升/秒）'))
        if flow_val is not None:
            influent_flow_rate.set(flow_val)

        vol_val = safe_float(influent.get('排放量（吨）'))
        if vol_val is not None:
            influent_discharge_volume.set(vol_val)

        # 更新出水指标
        ph_val = safe_float(effluent.get('pH值'))
        if ph_val is not None:
            effluent_ph.set(ph_val)

        cod_val = safe_float(effluent.get('化学需氧量浓度（毫克/升）'))
        if cod_val is not None:
            effluent_cod.set(cod_val)

        tn_val = safe_float(effluent.get('总氮浓度（毫克/升）'))
        if tn_val is not None:
            effluent_tn.set(tn_val)

        an_val = safe_float(effluent.get('氨氮浓度（毫克/升）'))
        if an_val is not None:
            effluent_an.set(an_val)

        tp_val = safe_float(effluent.get('总磷浓度（毫克/升）'))
        if tp_val is not None:
            effluent_tp.set(tp_val)

        flow_val = safe_float(effluent.get('流量（升/秒）'))
        if flow_val is not None:
            effluent_flow_rate.set(flow_val)

        vol_val = safe_float(effluent.get('排放量（吨）'))
        if vol_val is not None:
            effluent_discharge_volume.set(vol_val)

        ss_val = safe_float(effluent.get('悬浮物浓度（毫克/升）'))
        if ss_val is not None:
            effluent_suspended_solids.set(ss_val)

        # ========== 实时分析（基于Orchestrator架构） ==========
        # 协调4个子智能体协同分析：
        # 1. 数据治理子智能体：数据质量检查、清洗
        # 2. 特征分析子智能体：滑动窗口特征提取
        # 3. 异常检测子智能体：异常识别、模式匹配
        # 4. 规则推理子智能体：违规判定、嫌疑等级
        analysis_result = process_realtime_data_sync(realtime_orchestrator, influent, effluent)

        # 处理告警
        alerts = analysis_result.get('alerts', [])
        for alert in alerts:
            alert_total.labels(
                pattern_type=alert.get('type', 'unknown'),
                level=alert.get('level', 'medium')
            ).inc()

            logger.warning(f"[ALERT] {alert.get('type')} ({alert.get('level')}): {alert.get('message')}")

        # 处理异常
        for anomaly in analysis_result.get('anomalies', []):
            anomaly_type = anomaly.get('type', 'unknown')
            anomaly_detected.labels(anomaly_type=anomaly_type).inc()

        data_processed.labels(status='success').inc()

        logger.debug(f"接收数据: 进水pH={influent.get('pH值')}, 出水pH={effluent.get('pH值')}")

        # 返回分析结果
        return jsonify({
            'status': 'ok',
            'analysis': analysis_result
        })

    except Exception as e:
        logger.error(f"处理失败: {e}")
        data_processed.labels(status='error').inc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/stats', methods=['GET'])
def get_analyzer_stats():
    """获取实时编排器统计信息"""
    stats = realtime_orchestrator.get_statistics()
    return jsonify(stats)


@app.route('/api/analyze/reset', methods=['POST'])
def reset_analyzer():
    """重置实时编排器状态"""
    realtime_orchestrator.reset()
    alert_total.clear()
    logger.info("[RESET] 实时编排器已重置")
    return jsonify({'status': 'reset', 'message': '编排器状态已重置'})


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("启动Flask中间件（基于Orchestrator架构）...")
    logger.info("  - http://localhost:5000/health")
    logger.info("  - http://localhost:5000/metrics")
    logger.info("  - http://localhost:5000/api/dual-stream (数据接收+实时分析)")
    logger.info("  - http://localhost:5000/api/analyze/stats (统计信息)")
    logger.info("  - http://localhost:5000/api/analyze/reset (重置编排器)")
    logger.info("")
    logger.info("实时分析架构: Orchestrator协调4个子智能体协同分析")
    logger.info("  1. 数据治理子智能体: 数据质量检查、清洗")
    logger.info("  2. 特征分析子智能体: 滑动窗口特征提取")
    logger.info("  3. 异常检测子智能体: 异常识别、模式匹配")
    logger.info("  4. 规则推理子智能体: 违规判定、嫌疑等级")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)

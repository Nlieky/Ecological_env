#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask中间件 - 基于 Hermes Agent 框架的实时监测

架构说明：
1. 实时流（每秒）：Prometheus指标更新，立即响应
2. 底层框架：Hermes Agent (NousResearch/hermes-agent)
   - AIAgent.run_conversation() 处理查询
   - delegate_task 工具调用子智能体
   - LLM 自动解析意图并协调子智能体

数据缓冲 + 实时更新
"""

import logging
import sys
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from collections import deque

# 项目路径 - 获取脚本文件所在目录的父目录（项目根目录）
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "workspace"))

# multi-dimensional-data-perception-agent模块路径
agent_scripts = project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"
sys.path.insert(0, str(agent_scripts.resolve()))

# 清除可能的模块缓存，确保使用最新代码
cache_patterns = [
    'expert_reasoner', 'rule_reasoning_core', 'anomaly_detection_core',
    'feature_analysis_core', 'data_governance_core', 'execution_control',
    '__pycache__'
]
for key in list(sys.modules.keys()):
    for pattern in cache_patterns:
        if pattern in key:
            del sys.modules[key]
            break

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ==================== LLM 实时分析功能开关 ====================
# 通过环境变量 ENABLE_LLM_REALTIME_ANALYSIS 控制是否启用 LLM 分析
# 默认关闭，需要时通过环境变量启用
ENABLE_LLM_REALTIME_ANALYSIS = os.getenv('ENABLE_LLM_REALTIME_ANALYSIS', 'false').lower() == 'true'

if ENABLE_LLM_REALTIME_ANALYSIS:
    logger.info("[CONFIG] LLM 实时分析功能已启用")
else:
    logger.info("[CONFIG] LLM 实时分析功能已禁用（通过设置环境变量 ENABLE_LLM_REALTIME_ANALYSIS=true 启用）")

# 禁用 Flask (werkzeug) 的访问日志
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

logger.info(f"[PATH] 项目根目录: {project_root}")
logger.info(f"[PATH] Agent脚本目录: {agent_scripts}")

# 导入LLM客户端
from shared.configs.llm_client import get_llm_client

# 导入multi-dimensional-data-perception-agent流水线
try:
    from data_pipeline import MultiDimensionalDataPipeline
    data_pipeline = MultiDimensionalDataPipeline()
    logger.info("[INIT] 多维数据感知流水线已加载")
except Exception as e:
    logger.warning(f"[INIT] 流水线加载失败: {e}")
    data_pipeline = None

app = Flask(__name__)

# ==================== Prometheus 指标 ====================

# 进水指标
influent_ph = Gauge('wastewater_influent_ph', '进水pH值')
influent_cod = Gauge('wastewater_influent_cod', '进水化学需氧量(mg/L)')
influent_tn = Gauge('wastewater_influent_tn', '进水总氮(mg/L)')
influent_an = Gauge('wastewater_influent_an', '进水氨氮(mg/L)')
influent_tp = Gauge('wastewater_influent_tp', '进水总磷(mg/L)')
influent_flow_rate = Gauge('wastewater_influent_flow_rate', '进水流量(升/秒)')
influent_discharge_volume = Gauge('wastewater_influent_discharge_volume', '进水排放量(吨)')

# 出水指标
effluent_ph = Gauge('wastewater_effluent_ph', '出水pH值')
effluent_suspended_solids = Gauge('wastewater_effluent_suspended_solids', '出水悬浮物浓度(mg/L)')
effluent_cod = Gauge('wastewater_effluent_cod', '出水化学需氧量(mg/L)')
effluent_tn = Gauge('wastewater_effluent_tn', '出水总氮(mg/L)')
effluent_an = Gauge('wastewater_effluent_an', '出水氨氮(mg/L)')
effluent_tp = Gauge('wastewater_effluent_tp', '出水总磷(mg/L)')
effluent_flow_rate = Gauge('wastewater_effluent_flow_rate', '出水流量(升/秒)')
effluent_discharge_volume = Gauge('wastewater_effluent_discharge_volume', '出水排放量(吨)')

# 计数器
data_processed = Counter('wastewater_data_processed_total', '数据处理总数', ['status'])
anomaly_detected = Counter('wastewater_anomaly_detected_total', '异常检测总数', ['anomaly_type'])
alert_total = Counter('wastewater_alert_total', '实时告警总数', ['pattern_type', 'level'])

# ==================== Hermes 框架初始化 ====================

# 获取LLM客户端
try:
    llm_client = get_llm_client(
        env_path=str(project_root / "middleware" / ".env"),
        config_path=str(project_root / "shared" / "configs" / "llm_config.yaml")
    )
    logger.info("[INIT] LLM客户端已启用")
except Exception as e:
    logger.warning(f"[INIT] LLM客户端初始化失败: {e}，使用本地规则模式")
    llm_client = None

# Hermes 框架配置
# 注意：真正的 Hermes 使用方式是在需要时直接创建 AIAgent 实例
# 配置应在 .hermes/config.yaml 中设置

logger.info("[INIT] Hermes 框架就绪")
logger.info("[INIT] - 使用 AIAgent.run_conversation() 处理查询")
logger.info("[INIT] - LLM 通过 delegate_task 工具调用子智能体")

# ==================== 双流处理架构配置 ====================

# LLM分析配置
LLM_ANALYSIS_INTERVAL = 5 * 60  # 5分钟（秒）
DATA_BUFFER_SIZE = 1000  # 缓冲区大小

# 数据缓冲队列
data_buffer = deque(maxlen=DATA_BUFFER_SIZE)
buffer_lock = threading.Lock()

# LLM分析状态
last_llm_analysis_time = None
llm_analysis_in_progress = False

# 统计信息
total_data_received = 0
total_llm_analysis = 0
llm_analysis_results = []
request_count = 0
LOG_EVERY_N_REQUESTS = 50  # 每50条请求打印一次


# ========== 实时LLM分析功能（受功能开关控制） ==========
if ENABLE_LLM_REALTIME_ANALYSIS:
    def run_llm_analysis():
        """
        执行两层LLM分析

        取缓冲区中的最新数据进行分析
        """
        pass  # 功能待实现
#     """
#     global last_llm_analysis_time, llm_analysis_in_progress, total_llm_analysis
#
#     with buffer_lock:
#         if len(data_buffer) == 0:
#             logger.warning("[LLM-ANALYSIS] 缓冲区无数据，跳过分析")
#             return
#
#         # 取缓冲区中的所有数据进行时序分析
#         recent_data_list = list(data_buffer)
#
#         # 构建时序数据结构
#         recent_data = {
#             'timestamp': recent_data_list[-1].get('timestamp'),
#             'data_count': len(recent_data_list),
#             'influent_timeseries': [],
#             'effluent_timeseries': [],
#             'time_range': {
#                 'start': recent_data_list[0].get('timestamp'),
#                 'end': recent_data_list[-1].get('timestamp')
#             },
#             # 添加单点数据供task_receiving使用
#             'influent': recent_data_list[-1].get('influent', {}) if recent_data_list else {},
#             'effluent': recent_data_list[-1].get('effluent', {}) if recent_data_list else {},
#             # 添加显式的start_time和end_time
#             'start_time': recent_data_list[0].get('timestamp') if recent_data_list else None,
#             'end_time': recent_data_list[-1].get('timestamp') if recent_data_list else None
#         }
#
#         # 提取进水和出水时序数据
#         for data_point in recent_data_list:
#             if 'influent' in data_point:
#                 recent_data['influent_timeseries'].append(data_point['influent'])
#             if 'effluent' in data_point:
#                 recent_data['effluent_timeseries'].append(data_point['effluent'])
#
#     try:
#         llm_analysis_in_progress = True
#         analysis_start = datetime.now()
#
#         logger.info("")
#         logger.info("=" * 60)
#         logger.info("[LLM-ANALYSIS] 开始两层LLM分析")
#         logger.info(f"[LLM-ANALYSIS] 数据时间: {recent_data.get('timestamp')}")
#         logger.info(f"[LLM-ANALYSIS] 时序数据量: {recent_data.get('data_count', 0)}条")
#         logger.info(f"[LLM-ANALYSIS] 时间范围: {recent_data.get('time_range', {}).get('start')} ~ {recent_data.get('time_range', {}).get('end')}")
#         logger.info("=" * 60)
#
#         # ========== 阶段1: 任务接收与解析 ==========
#         logger.info("[STAGE 1/3] 任务接收与解析...")
#         parse_result = task_receiving_module.process(recent_data)
#
#         if parse_result['status'] != 'success':
#             logger.error(f"[ERROR] 任务解析失败: {parse_result}")
#             data_processed.labels(status='error').inc()
#             return
#
#         structured_task = parse_result['structured_task']
#         intent = parse_result['intent']
#         logger.info(f"[STAGE 1] 任务解析完成: {structured_task['task_id']}")
#
#         # ========== 阶段2: 大模型协调子智能体执行 ==========
#         logger.info("[STAGE 2/3] 大模型协调子智能体执行...")
#
#         execution_results = llm_coordinator.coordinate_all_agents(
#             task=structured_task,
#             analysis_scope="full"  # 强制执行完整分析，包含所有4个子智能体
#         )
#
#         logger.info(f"[STAGE 2] 子智能体执行完成: {len(execution_results)}个")
#
#         # ========== 阶段3: 结果解释输出 ==========
#         logger.info("[STAGE 3/3] 结果解释与报告生成...")
#
#         interpretation_result = result_interpretation.interpret_results(
#             execution_results=execution_results,
#             task_info={
#                 "task_id": structured_task['task_id'],
#                 "task_name": structured_task['task_name'],
#                 "timestamp": recent_data.get('timestamp')
#             }
#         )
#
#         logger.info("[STAGE 3] 报告生成完成")
#
#         # ========== 处理告警和异常 ==========
#         alerts = []
#         violations = []
#         anomalies = []
#
#         for agent_id, result in execution_results.items():
#             if result.get('status') == 'error':
#                 logger.error(f"[ERROR] {agent_id} 执行失败: {result.get('error')}")
#                 continue
#
#             if agent_id == 'anomaly-detection-agent':
#                 anomalies = result.get('anomalies', [])
#                 for anom in anomalies:
#                     anomaly_type = anom.get('type', 'unknown')
#                     anomaly_detected.labels(anomaly_type=anomaly_type).inc()
#
#             if agent_id == 'rule-reasoning-agent':
#                 violations = result.get('violations', [])
#
#                 # 如果没有violations字段，从reasoning结果中提取
#                 if not violations and 'reasoning' in result:
#                     reasoning = result['reasoning']
#                     # 从matched_patterns中提取违规
#                     matched_patterns = reasoning.get('matched_patterns', [])
#                     for pattern in matched_patterns:
#                         if pattern.get('suspicion_level') in ['high', 'critical']:
#                             violations.append({
#                                 'type': pattern.get('name', 'unknown'),
#                                 'level': pattern.get('suspicion_level', 'high'),
#                                 'message': f"{pattern.get('name')}: 匹配度{pattern.get('match_score', 0):.2%}, 置信度{pattern.get('confidence', 0):.2%}",
#                                 'confidence': pattern.get('confidence', 0.0)
#                             })
#
#                     # 从has_violation标志检查
#                     if result.get('has_violation') and result.get('suspicion_level') in ['high', 'critical']:
#                         if not violations:
#                             violations.append({
#                                 'type': result.get('violation_type', 'suspected_violation'),
#                                 'level': result.get('suspicion_level', 'high'),
#                                 'message': f"嫌疑等级: {result.get('suspicion_level')}, 置信度: {result.get('confidence', 0):.2%}",
#                                 'confidence': result.get('confidence', 0.0)
#                             })
#
#                 for vio in violations:
#                     alert_total.labels(
#                         pattern_type=vio.get('type', 'unknown'),
#                         level=vio.get('level', 'medium')
#                     ).inc()
#
#                     alert = {
#                         'type': vio.get('type'),
#                         'level': vio.get('level'),
#                         'message': vio.get('message'),
#                         'legal_reference': vio.get('legal_reference')
#                     }
#                     alerts.append(alert)
#
#                     logger.warning(f"[ALERT] {vio.get('type')} ({vio.get('level')}): {vio.get('message')}")
#
#         # 保存分析结果
#         analysis_result = {
#             'timestamp': recent_data.get('timestamp'),
#             'analysis_time': analysis_start.isoformat(),
#             'task_id': structured_task['task_id'],
#             'analysis': interpretation_result.get('analysis', {}),
#             'alerts': alerts,
#             'report': interpretation_result.get('report', ''),
#             'anomalies_count': len(anomalies),
#             'violations_count': len(violations)
#         }
#
#         with buffer_lock:
#             llm_analysis_results.append(analysis_result)
#             # 只保留最近10次分析结果
#             if len(llm_analysis_results) > 10:
#                 llm_analysis_results.pop(0)
#
#         total_llm_analysis += 1
#         last_llm_analysis_time = datetime.now()
#
#         analysis_duration = (datetime.now() - analysis_start).total_seconds()
#         logger.info("")
#         logger.info("=" * 60)
#         logger.info(f"[LLM-ANALYSIS] 分析完成，耗时: {analysis_duration:.1f}秒")
#         logger.info(f"[LLM-ANALYSIS] 异常: {len(anomalies)}, 违规: {len(violations)}")
#         logger.info("=" * 60)
#
#         # ========== 打印报告 ==========
#         report_text = interpretation_result.get('report', '')
#         if report_text:
#             logger.info("")
#             logger.info("=" * 60)
#             logger.info("[REPORT] 分析报告")
#             logger.info("=" * 60)
#             logger.info(report_text)
#             logger.info("=" * 60)
#             logger.info("")
#
#         data_processed.labels(status='success').inc()
#
#     except Exception as e:
#         logger.error(f"[ERROR] LLM分析失败: {e}")
#         import traceback
#         traceback.print_exc()
#         data_processed.labels(status='error').inc()
#
#     finally:
#         llm_analysis_in_progress = False
#
#
# def llm_analysis_worker():
#     """
#     后台线程：定期触发LLM分析
#
#     每10分钟检查一次是否需要进行分析
#     """
#     logger.info("[LLM-WORKER] LLM分析后台线程启动")
#     logger.info(f"[LLM-WORKER] 分析间隔: {LLM_ANALYSIS_INTERVAL}秒")
#
#     while True:
#         try:
#             time.sleep(LLM_ANALYSIS_INTERVAL)
#
#             # 检查是否有足够的数据
#             with buffer_lock:
#                 data_count = len(data_buffer)
#
#             if data_count > 0:
#                 logger.info(f"[LLM-WORKER] 触发LLM分析，缓冲区数据: {data_count}条")
#                 run_llm_analysis()
#             else:
#                 logger.debug("[LLM-WORKER] 无数据，跳过分析")
#
#         except Exception as e:
#             logger.error(f"[LLM-WORKER] 后台线程错误: {e}")
#             time.sleep(60)  # 出错后等待1分钟再重试
#
#
# # 启动后台线程
# llm_worker_thread = threading.Thread(target=llm_analysis_worker, daemon=True)
# llm_worker_thread.start()
#
# logger.info("[INIT] 双流处理架构启动")
# logger.info(f"[INIT] - Prometheus: 实时更新（每秒）")
# logger.info(f"[INIT] - LLM分析: 每{LLM_ANALYSIS_INTERVAL//60}分钟一次")
# logger.info(f"[INIT] - 数据缓冲: 最大{DATA_BUFFER_SIZE}条")

logger.info("[INIT] 单流处理架构启动")
logger.info(f"[INIT] - Prometheus: 实时更新（每秒）")
logger.info(f"[INIT] - LLM分析: 已禁用（待后续开发）")
logger.info(f"[INIT] - 数据缓冲: 最大{DATA_BUFFER_SIZE}条")


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'wastewater_hermes_middleware',
        'architecture': 'hermes-agent'
    })


@app.route('/api/simple', methods=['POST'])
def simple_test():
    """最简单的测试端点"""
    print("[SIMPLE] Request received!!!", flush=True)
    return jsonify({'status': 'ok', 'message': 'simple test works'})


@app.route('/routes', methods=['GET'])
def list_routes():
    """列出所有路由"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify({'routes': routes})


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus指标端点"""
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


def safe_float(value, default=None):
    """安全转换为浮点数"""
    if value is None:
        return default
    val_str = str(value).strip()
    if val_str in ['/', '', 'NA', 'N/A', 'null', 'None']:
        return default
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return default


def update_prometheus_metrics(influent, effluent):
    """更新Prometheus指标"""
    # 进水指标
    if (ph_val := safe_float(influent.get('pH值'))) is not None:
        influent_ph.set(ph_val)
    if (cod_val := safe_float(influent.get('化学需氧量浓度（毫克/升）'))) is not None:
        influent_cod.set(cod_val)
    if (tn_val := safe_float(influent.get('总氮浓度（毫克/升）'))) is not None:
        influent_tn.set(tn_val)
    if (an_val := safe_float(influent.get('氨氮浓度（毫克/升）'))) is not None:
        influent_an.set(an_val)
    if (tp_val := safe_float(influent.get('总磷浓度（毫克/升）'))) is not None:
        influent_tp.set(tp_val)
    if (flow_val := safe_float(influent.get('流量（升/秒）'))) is not None:
        influent_flow_rate.set(flow_val)
    if (discharge_val := safe_float(influent.get('排放量（吨）'))) is not None:
        influent_discharge_volume.set(discharge_val)

    # 出水指标
    if (ph_val := safe_float(effluent.get('pH值'))) is not None:
        effluent_ph.set(ph_val)
    if (ss_val := safe_float(effluent.get('悬浮物浓度（毫克/升）'))) is not None:
        effluent_suspended_solids.set(ss_val)
    if (cod_val := safe_float(effluent.get('化学需氧量浓度（毫克/升）'))) is not None:
        effluent_cod.set(cod_val)
    if (tn_val := safe_float(effluent.get('总氮浓度（毫克/升）'))) is not None:
        effluent_tn.set(tn_val)
    if (an_val := safe_float(effluent.get('氨氮浓度（毫克/升）'))) is not None:
        effluent_an.set(an_val)
    if (tp_val := safe_float(effluent.get('总磷浓度（毫克/升）'))) is not None:
        effluent_tp.set(tp_val)
    if (flow_val := safe_float(effluent.get('流量（升/秒）'))) is not None:
        effluent_flow_rate.set(flow_val)
    if (discharge_val := safe_float(effluent.get('排放量（吨）'))) is not None:
        effluent_discharge_volume.set(discharge_val)


@app.route('/api/dual-stream', methods=['POST'])
def receive_dual_stream():
    """
    接收双数据流 - 双流处理架构

    实时流（立即响应）：
    - 更新Prometheus指标
    - 数据存入缓冲区

    分析流（每10分钟）：
    - 后台线程触发两层LLM分析

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
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # ========== 实时流：立即更新Prometheus ==========
        update_prometheus_metrics(influent, effluent)

        # ========== 实时流：数据存入缓冲区 ==========
        with buffer_lock:
            data_buffer.append(data)
            current_buffer_size = len(data_buffer)

        global total_data_received, request_count
        total_data_received += 1
        request_count += 1
        data_processed.labels(status='received').inc()

        # 简化的日志（高频时不刷屏）
        if request_count % LOG_EVERY_N_REQUESTS == 0:
            logger.info(f"[API] 已接收 {request_count} 条数据，缓冲区: {current_buffer_size}")

        # ========== 调用multi-dimensional-data-perception-agent流水线 ==========
        # 已暂时禁用，待后续开发
        pipeline_result = None
        # if data_pipeline:
        #     try:
        #         pipeline_result = data_pipeline.process_stream_data(data)
        #         logger.debug(f"[PIPELINE] 流水线处理完成: {pipeline_result.get('status')}")
        #     except Exception as e:
        #         logger.error(f"[PIPELINE] 流水线处理失败: {e}")
        #         pipeline_result = {"status": "error", "error": str(e)}

        # ========== 返回快速响应 ==========
        # 获取最近一次分析结果（如果有的话）
        latest_analysis = None
        with buffer_lock:
            if llm_analysis_results:
                latest_analysis = llm_analysis_results[-1]

        response_data = {
            'status': 'received',
            'timestamp': timestamp,
            'buffer_size': current_buffer_size,
            'total_received': total_data_received,
            'message': '数据已接收，Prometheus已更新'
        }

        # 附加流水线处理结果
        if pipeline_result:
            response_data['pipeline_result'] = {
                'status': pipeline_result.get('status'),
                'stages_completed': pipeline_result.get('metrics', {}).get('stage_count', 0),
                'decomposed_types': pipeline_result.get('output', {}).get('decomposed_types', [])
            }
            if pipeline_result.get('status') == 'error':
                response_data['pipeline_result']['error'] = pipeline_result.get('error')

        # 附加最近分析结果信息
        if latest_analysis:
            response_data['last_analysis'] = {
                'timestamp': latest_analysis.get('timestamp'),
                'analysis_time': latest_analysis.get('analysis_time'),
                'anomalies_count': latest_analysis.get('anomalies_count'),
                'violations_count': latest_analysis.get('violations_count')
            }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[ERROR] 数据接收失败: {e}")
        import traceback
        traceback.print_exc()
        data_processed.labels(status='error').inc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/trigger', methods=['POST'])
def trigger_llm_analysis():
    """
    手动触发LLM分析

    用于测试或需要立即分析的场合
    """
    return jsonify({
        'status': 'disabled',
        'message': 'LLM实时分析功能已暂时禁用，待后续开发'
    }), 503

    # 以下代码已禁用，后续开发时取消注释
    #
    # try:
    #     if llm_analysis_in_progress:
    #         return jsonify({
    #             'status': 'busy',
    #             'message': 'LLM分析正在进行中'
    #         })
    #
    #     with buffer_lock:
    #         data_count = len(data_buffer)
    #
    #     if data_count == 0:
    #         return jsonify({
    #             'status': 'no_data',
    #             'message': '缓冲区无数据'
    #         })
    #
    #     # 在后台线程中执行分析
    #     def run_in_background():
    #         run_llm_analysis()
    #
    #     thread = threading.Thread(target=run_in_background)
    #     thread.start()
    #
    #     return jsonify({
    #         'status': 'triggered',
    #         'message': f'LLM分析已触发，缓冲区数据: {data_count}条'
    #     })
    #
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/results', methods=['GET'])
def get_analysis_results():
    """
    获取最近的LLM分析结果

    返回最近N次分析结果
    """
    return jsonify({
        'status': 'disabled',
        'message': 'LLM实时分析功能已暂时禁用，待后续开发',
        'total_analysis': 0,
        'last_analysis_time': None,
        'results': []
    })

    # 以下代码已禁用，后续开发时取消注释
    #
    # try:
    #     with buffer_lock:
    #         results = list(llm_analysis_results)
    #
    #     return jsonify({
    #         'status': 'ok',
    #         'total_analysis': total_llm_analysis,
    #         'last_analysis_time': last_llm_analysis_time.isoformat() if last_llm_analysis_time else None,
    #         'results': results
    #     })
    #
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/stats', methods=['GET'])
def get_analyzer_stats():
    """获取 Hermes 框架统计信息"""
    return jsonify({
        'module': 'hermes-agent',
        'framework': 'Hermes Agent Framework (NousResearch/hermes-agent)',
        'subagents': {
            'multi-dimensional-data-perception': '多维数据感知',
            'anomaly-detection': '异常检测',
            'rule-reasoning': '规则推理',
            'disposition-execution': '研判预警与处置执行'
        },
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/analyze/reset', methods=['POST'])
def reset_analyzer():
    """重置 Prometheus 指标状态"""
    alert_total.clear()
    logger.info("[RESET] Prometheus 指标已重置")
    return jsonify({'status': 'reset', 'message': 'Prometheus 指标已重置'})


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("启动Flask中间件（基于 Hermes Agent 框架）...")
    logger.info("")
    logger.info("端点:")
    logger.info("  - http://localhost:5000/health")
    logger.info("  - http://localhost:5000/metrics")
    logger.info("  - http://localhost:5000/api/dual-stream")
    logger.info("  - http://localhost:5000/api/analyze/stats")
    logger.info("  - http://localhost:5000/api/analyze/reset")
    logger.info("")
    logger.info("底层框架: Hermes Agent (NousResearch/hermes-agent)")
    logger.info("  - AIAgent.run_conversation() 处理查询")
    logger.info("  - LLM 通过 delegate_task 工具调用子智能体")
    logger.info("  - 子智能体: multi-dimensional-data-perception, anomaly-detection,")
    logger.info("              rule-reasoning, disposition-execution")
    logger.info("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)

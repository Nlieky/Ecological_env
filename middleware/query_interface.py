#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然语言查询接口 - LLM驱动版本

使用主智能体LLM驱动子智能体协调完成查询。
真正的LLM驱动架构：LLM解析意图 → LLM调度子智能体 → LLM整合结果
"""

import logging
import sys
import os
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request, Response, jsonify
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "workspace" / "skills" / "orchestrator-core" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "configs"))

# 导入主智能体LLM协调器
from execution_control import LLMAgentCoordinator, SubAgentIdentityLoader
from shared.configs.llm_client import get_llm_client

# 导入数据获取器
from historical_data_fetcher import HistoricalDataFetcher

# 使用简单的print代替logging，避免递归错误
import sys
def log_info(msg):
    try:
        print(f"[INFO] {msg}", flush=True)
    except (UnicodeEncodeError, UnicodeDecodeError):
        print(f"[INFO] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}", flush=True)
    sys.stdout.flush()

def log_error(msg):
    try:
        print(f"[ERROR] {msg}", flush=True)
    except (UnicodeEncodeError, UnicodeDecodeError):
        print(f"[ERROR] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}", flush=True)
    sys.stdout.flush()

def log_warning(msg):
    try:
        print(f"[WARNING] {msg}", flush=True)
    except (UnicodeEncodeError, UnicodeDecodeError):
        print(f"[WARNING] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}", flush=True)
    sys.stdout.flush()


# 自定义JSON编码器
class NumpyJSONEncoder(json.JSONEncoder):
    """JSON编码器，处理numpy和pandas类型"""
    def default(self, obj):
        import numpy as np
        import pandas as pd

        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Series, pd.DataFrame)):
            return obj.to_dict()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return super().default(obj)


def convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    import numpy as np
    import pandas as pd

    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {str(k): convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(v) for v in obj]
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    return obj

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


@app.before_request
def log_request():
    print(f"[FLASK] {request.method} {request.path}")
    print(f"[FLASK] Headers: {dict(request.headers)}")


@app.after_request
def log_response(response):
    print(f"[FLASK] Response status: {response.status_code}")
    print(f"[FLASK] Response type: {type(response)}")
    return response


# 全局错误处理器（临时禁用）
# @app.errorhandler(Exception)
# def handle_exception(e):
#     """处理所有未捕获的异常"""
#     import traceback
#     traceback.print_exc()
#     error_msg = str(e)
#     # 确保错误消息可以序列化
#     error_result = {
#         'status': 'error',
#         'error': error_msg
#     }
#     try:
#         json_str = json.dumps(error_result, ensure_ascii=False, cls=NumpyJSONEncoder)
#         return Response(json_str, mimetype='application/json', status=500)
#     except Exception as json_err:
#         # 如果连错误消息都无法序列化，返回一个简单的错误
#         return Response(json.dumps({'status': 'error', 'error': 'Internal server error'}), mimetype='application/json', status=500)


# 自定义JSON编码器，处理numpy类型
import numpy as np
class NumpyJSONEncoder(json.JSONEncoder):
    """JSON编码器，处理numpy类型"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

app.json_encoder = NumpyJSONEncoder

# 全局组件
llm_coordinator = None
data_fetcher = None
llm_client = None

# 分析报告存储（保存最近50次查询的分析报告）
analysis_reports = []
MAX_REPORTS = 50
reports_lock = threading.Lock()


def initialize_components():
    """初始化LLM驱动组件"""
    global llm_coordinator, data_fetcher, llm_client

    # 1. 初始化LLM客户端
    try:
        # 传递正确的路径参数
        llm_client = get_llm_client(
            env_path=str(PROJECT_ROOT / "middleware" / ".env"),
            config_path=str(PROJECT_ROOT / "shared" / "configs" / "llm_config.yaml")
        )
        log_info("[INIT] LLM客户端初始化成功")
    except Exception as e:
        log_error(f"[INIT] LLM客户端初始化失败: {e}")
        raise

    # 2. 初始化LLM协调器
    try:
        llm_coordinator = LLMAgentCoordinator(llm_client=llm_client)
        log_info("[INIT] LLM协调器初始化成功")
    except Exception as e:
        log_error(f"[INIT] LLM协调器初始化失败: {e}")
        raise

    # 3. 初始化数据获取器
    try:
        data_fetcher = HistoricalDataFetcher()
        log_info("[INIT] 数据获取器初始化成功")
    except Exception as e:
        log_error(f"[INIT] 数据获取器初始化失败: {e}")
        raise


@app.route('/api/query/health', methods=['GET'])
def health():
    """健康检查"""
    result = json.dumps({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'llm_query_interface',
        'llm_available': llm_client is not None
    }, cls=NumpyJSONEncoder)
    return Response(result, mimetype='application/json')


@app.route('/api/query/analysis', methods=['GET'])
def get_analysis_reports():
    """
    获取查询分析报告列表

    返回最近的查询分析报告
    """
    try:
        with reports_lock:
            reports = list(analysis_reports)

        return jsonify({
            'status': 'ok',
            'total': len(reports),
            'results': reports
        })
    except Exception as e:
        log_error(f"[ERROR] 获取分析报告失败: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/query', methods=['POST'])
def handle_query():
    """
    处理自然语言查询 - LLM驱动版本

    流程：
    1. LLM解析查询意图
    2. 获取历史数据
    3. LLM调度子智能体分析
    4. LLM整合结果生成报告
    """
    try:
        print(f"[REQUEST] Received request")
        print(f"[REQUEST] Content-Type: {request.content_type}")

        # 手动解析JSON
        import json as json_mod
        raw_data = request.get_data(as_text=True)
        print(f"[REQUEST] Raw data: {raw_data[:100]}")

        data = json_mod.loads(raw_data)
        print(f"[REQUEST] Parsed data type: {type(data)}")
        print(f"[REQUEST] Parsed data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")

        if not data or 'query' not in data:
            result = json.dumps({
                'status': 'error',
                'error': 'Missing query parameter'
            }, cls=NumpyJSONEncoder)
            return Response(result, mimetype='application/json', status=400)

        query = data['query']
        log_info(f"[QUERY] 收到查询: {query[:50]}...")

        # ========== 步骤1: LLM解析查询意图 ==========
        log_info("[STEP 1] LLM解析查询意图...")
        intent = llm_parse_query_intent(query)
        log_info(f"[STEP 1] 解析结果: {json.dumps(intent, ensure_ascii=False)}")

        # ========== 步骤2: 获取历史数据 ==========
        log_info("[STEP 2] 获取历史数据...")
        historical_data = fetch_data_for_query(intent)
        log_info(f"[STEP 2] 数据获取: influent={len(historical_data['influent'])}, effluent={len(historical_data['effluent'])}")

        # ========== 步骤3: LLM调度子智能体分析 ==========
        log_info("[STEP 3] LLM调度子智能体分析...")

        # 3.1 调用多维数据感知子智能体
        log_info("=" * 60)
        log_info("[STEP 3.1] 调用多维数据感知子智能体")
        log_info(f"[STEP 3.1] 任务ID: query_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        log_info(f"[STEP 3.1] 查询内容: {query[:100]}...")
        log_info(f"[STEP 3.1] 数据量: influent={len(historical_data.get('influent', []))}, effluent={len(historical_data.get('effluent', []))}")
        log_info("=" * 60)

        perception_result = llm_coordinator.coordinate_agent_execution(
            agent_id="multi-dimensional-data-perception-agent",
            task={
                "task_id": f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "description": f"查询处理: {query}",
                "query": query,
                "intent": intent,
                "data": historical_data,
                "metadata": {
                    "data_count": len(historical_data.get('influent', [])),
                    "indicators": intent.get('indicators', []),
                    "analysis_types": intent.get('analysis_types', []),
                    # 将历史数据转换为时序格式以便注入
                    "influent_timeseries": historical_data.get('influent', []),
                    "effluent_timeseries": historical_data.get('effluent', [])
                }
            }
        )

        log_info("=" * 60)
        log_info(f"[STEP 3.1] 多维数据感知子智能体完成")
        log_info(f"[STEP 3.1] 状态: {perception_result.get('status', 'unknown')}")
        if perception_result.get('status') == 'success':
            log_info(f"[STEP 3.1] 结果摘要: {str(perception_result.get('summary', ''))[:200]}...")
        log_info("=" * 60)

        # 3.2 调用异常检测子智能体（如果需要）
        anomaly_result = None
        if 'anomaly' in intent.get('analysis_types', []) or 'correlation' in intent.get('analysis_types', []):
            log_info("=" * 60)
            log_info("[STEP 3.2] 调用异常检测子智能体")
            log_info(f"[STEP 3.2] 分析类型: {intent.get('analysis_types', [])}")
            log_info("=" * 60)

            # NEW: Extract preprocessed data from perception result
            processed_data = historical_data  # 默认使用原始数据
            if perception_result and isinstance(perception_result, dict):
                # 尝试从感知结果中获取cleaned_data
                if "result" in perception_result:
                    result_data = perception_result["result"]
                    if isinstance(result_data, dict):
                        # 路径1: result.cleaned_data
                        if "cleaned_data" in result_data:
                            cleaned = result_data["cleaned_data"]
                            if isinstance(cleaned, dict) and "influent" in cleaned and "effluent" in cleaned:
                                processed_data = {
                                    "influent": cleaned["influent"],
                                    "effluent": cleaned["effluent"]
                                }
                                log_info(f"[STEP 3.2] 使用感知子智能体预处理后的数据: influent={len(processed_data['influent'])}, effluent={len(processed_data['effluent'])}")
                        # 路径2: result.aligned_data
                        elif "aligned_data" in result_data:
                            aligned = result_data["aligned_data"]
                            if isinstance(aligned, dict):
                                processed_data = aligned
                                log_info(f"[STEP 3.2] 使用感知子智能体对齐后的数据")
                # 路径3: processed_data直接路径
                elif "processed_data" in perception_result:
                    processed = perception_result["processed_data"]
                    if isinstance(processed, dict):
                        processed_data = processed
                        log_info(f"[STEP 3.2] 使用感知子智能体处理后的数据")

            anomaly_result = llm_coordinator.coordinate_agent_execution(
                agent_id="anomaly-detection-agent",
                task={
                    "task_id": f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}_anomaly",
                    "description": "异常检测和相关性分析",
                    "query": query,
                    "intent": intent,
                    "data": processed_data,  # 使用预处理后的数据
                    "metadata": {
                        "data_count": len(processed_data.get('influent', [])),
                        "indicators": intent.get('indicators', []),
                        "analysis_types": intent.get('analysis_types', []),
                        "data_source": "preprocessed" if processed_data is not historical_data else "raw",
                        "influent_timeseries": processed_data.get('influent', []),
                        "effluent_timeseries": processed_data.get('effluent', [])
                    },
                    "previous_results": {"perception": perception_result}
                },
                previous_results={"perception": perception_result}
            )

            log_info("=" * 60)
            log_info(f"[STEP 3.2] 异常检测子智能体完成")
            log_info(f"[STEP 3.2] 状态: {anomaly_result.get('status', 'unknown')}")
            log_info(f"[STEP 3.2] 结果keys: {list(anomaly_result.keys()) if isinstance(anomaly_result, dict) else 'N/A'}")

            # 调试：深入查看result字段
            if anomaly_result and isinstance(anomaly_result, dict):
                result_field = anomaly_result.get('result', {})
                if result_field:
                    log_info(f"[STEP 3.2] result字段类型: {type(result_field)}")
                    if isinstance(result_field, dict):
                        log_info(f"[STEP 3.2] result.keys: {list(result_field.keys())}")
                        if 'anomalies' in result_field:
                            anomalies = result_field.get('anomalies', [])
                            log_info(f"[STEP 3.2] result.anomalies: {len(anomalies)} 个")
                            if anomalies and len(anomalies) > 0:
                                log_info(f"[STEP 3.2] 第一个异常示例: {str(anomalies[0])[:200]}...")
                        if 'output' in result_field:
                            output = result_field.get('output', {})
                            log_info(f"[STEP 3.2] result.output类型: {type(output)}, keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
                            if isinstance(output, dict) and 'anomalies' in output:
                                anomalies = output.get('anomalies', [])
                                log_info(f"[STEP 3.2] result.output.anomalies: {len(anomalies)} 个")

            if anomaly_result.get('anomalies'):
                anomalies = anomaly_result.get('anomalies', [])
                log_info(f"[STEP 3.2] 检测到 {len(anomalies)} 个异常点")
                for idx, anom in enumerate(anomalies[:3]):  # 只显示前3个异常
                    log_info(f"[STEP 3.2]   异常{idx+1}: {anom.get('indicator', 'N/A')} - {anom.get('pattern', 'N/A')} (严重度: {anom.get('severity', 'N/A')})")
                if len(anomalies) > 3:
                    log_info(f"[STEP 3.2]   ... 还有 {len(anomalies) - 3} 个异常点")
            log_info("=" * 60)
        else:
            log_info("[STEP 3.2] 跳过异常检测（未请求相关分析类型）")

        # ========== 步骤4: LLM整合结果生成报告 ==========
        log_info("[STEP 4] LLM整合结果生成报告...")
        summary = llm_generate_summary(query, intent, perception_result, anomaly_result)

        # ========== 返回结果 ==========
        try:
            # 构建完整的结果响应
            result = {
                'status': 'success',
                'query': str(query),
                'data_info': {
                    'influent_count': int(len(historical_data.get('influent', []))),
                    'effluent_count': int(len(historical_data.get('effluent', [])))
                },
                'summary': str(summary) if summary else ''
            }

            # ========== 添加透明度信息 ==========
            # 从 intent 中获取时间范围信息
            hours_back = intent.get('hours_back', 24)
            query_time_desc = f"过去{hours_back}小时" if hours_back >= 24 else f"过去{hours_back}小时"

            # 尝试从 historical_data 的 metadata 中获取实际时间范围
            actual_time_range = "N/A"
            if isinstance(historical_data, dict) and 'metadata' in historical_data:
                metadata = historical_data['metadata']
                if isinstance(metadata, dict) and 'time_range' in metadata:
                    tr = metadata['time_range']
                    if isinstance(tr, dict):
                        start = tr.get('start', '')
                        end = tr.get('end', '')
                        if start and end:
                            actual_time_range = f"{start} ~ {end}"

            # 从异常检测结果中获取算子信息
            operators_used = ['zscore', 'iqr', 'isolation_forest']  # 默认算子
            if anomaly_result and isinstance(anomaly_result, dict):
                # 尝试从 metadata 中获取算子信息
                if 'metadata' in anomaly_result:
                    meta = anomaly_result['metadata']
                    if isinstance(meta, dict) and 'operators_used' in meta:
                        operators_used = meta['operators_used']

            # 构建透明度信息
            result['process_info'] = {
                'query_time_range': query_time_desc,
                'actual_time_range': actual_time_range,
                'actual_data_count': {
                    'influent': int(len(processed_data.get('influent', []))),
                    'effluent': int(len(processed_data.get('effluent', [])))
                },
                'anomaly_count': 0,  # 将在后面更新
                'operators_used': operators_used
            }

            # ========== 添加时序数据（用于前端图表绘制）==========
            # 使用预处理后的数据以确保与异常检测使用的数据一致
            result['timeseries_data'] = {
                'influent': processed_data.get('influent', historical_data.get('influent', [])),
                'effluent': processed_data.get('effluent', historical_data.get('effluent', []))
            }

            # ========== 添加异常详情（用于前端标注异常点）==========
            result['anomaly_details'] = []
            if anomaly_result:
                # 从异常检测结果中提取异常点详情
                # 数据结构可能是: anomaly_result['result']['anomalies'] 或 anomaly_result['result']['output']['anomalies']
                anomalies = []

                # 尝试多种路径
                if 'result' in anomaly_result and isinstance(anomaly_result['result'], dict):
                    result_field = anomaly_result['result']
                    # 路径1: result.anomalies
                    if 'anomalies' in result_field:
                        anomalies = result_field['anomalies']
                        log_info(f"[QUERY] 从 result.anomalies 提取异常数据")
                    # 路径2: result.output.anomalies
                    elif 'output' in result_field and isinstance(result_field['output'], dict) and 'anomalies' in result_field['output']:
                        anomalies = result_field['output']['anomalies']
                        log_info(f"[QUERY] 从 result.output.anomalies 提取异常数据")
                    else:
                        log_info(f"[QUERY] result字段中未找到anomalies数据，result keys: {list(result_field.keys())}")

                # 路径3: 直接的 anomalies (备用)
                if not anomalies and 'anomalies' in anomaly_result:
                    anomalies = anomaly_result['anomalies']
                    log_info(f"[QUERY] 从 anomaly_result.anomalies 提取异常数据")

                if anomalies:
                    # 构建时间戳到索引的映射（为每个数据源构建一次）
                    def build_timestamp_mapping(ts_data):
                        """构建时间戳到索引的映射，检测重复时间戳"""
                        timestamp_to_index = {}
                        duplicates = []
                        for idx, record in enumerate(ts_data):
                            if isinstance(record, dict) and "timestamp" in record:
                                timestamp = record["timestamp"]
                                if timestamp in timestamp_to_index:
                                    duplicates.append((timestamp, timestamp_to_index[timestamp], idx))
                                else:
                                    timestamp_to_index[timestamp] = idx

                        if duplicates:
                            log_info(f"[QUERY] 警告: 发现{len(duplicates)}个重复时间戳，使用最后出现的索引")
                            for dup_ts, old_idx, new_idx in duplicates[:3]:  # 只记录前3个
                                log_info(f"[QUERY]   时间戳'{dup_ts}'在索引{old_idx}和{new_idx}重复")

                        return timestamp_to_index

                    # 为influent和effluent分别构建映射
                    influent_data = processed_data.get("influent", historical_data.get("influent", []))
                    effluent_data = processed_data.get("effluent", historical_data.get("effluent", []))

                    influent_mapping = build_timestamp_mapping(influent_data)
                    effluent_mapping = build_timestamp_mapping(effluent_data)

                    # 批量处理所有异常点（一次性处理而非逐个处理）
                    def select_mapping_and_data(anomaly):
                        """根据indicator选择对应的映射和数据"""
                        indicator = anomaly.get("indicator", "")
                        if "influent" in indicator.lower():
                            return influent_mapping, influent_data
                        else:
                            return effluent_mapping, effluent_data

                    # 处理所有异常点
                    matched_anomalies = []
                    for anomaly in anomalies:
                        if not isinstance(anomaly, dict):
                            continue

                        times_value = anomaly.get("times", "")
                        if not times_value:
                            log_info(f"[QUERY] 跳过空times的异常点: indicator={anomaly.get('indicator', 'unknown')}")
                            continue

                        ts_mapping, ts_data = select_mapping_and_data(anomaly)

                        # 检查是否为整数索引
                        try:
                            times_int = int(times_value)
                            if 0 <= times_int < len(ts_data):
                                record = ts_data[times_int]
                                if isinstance(record, dict) and "timestamp" in record:
                                    anomaly_copy = dict(anomaly)
                                    anomaly_copy["times"] = record["timestamp"]
                                    anomaly_copy["data_index"] = times_int
                                    matched_anomalies.append(anomaly_copy)
                                    continue
                        except (ValueError, TypeError):
                            pass

                        # 如果times是时间戳字符串，查找对应的索引
                        if times_value in ts_mapping:
                            anomaly_copy = dict(anomaly)
                            anomaly_copy["data_index"] = ts_mapping[times_value]
                            matched_anomalies.append(anomaly_copy)
                        else:
                            # 时间戳不匹配，保留原异常点
                            log_info(f"[QUERY] 时间戳未匹配: times={times_value}, indicator={anomaly.get('indicator', 'unknown')}")
                            matched_anomalies.append(anomaly)

                    # 转换为前端格式
                    for anomaly in matched_anomalies:
                        index_value = anomaly.get('index', anomaly.get('data_index', -1))
                        result['anomaly_details'].append({
                            'indicator': anomaly.get('indicator', ''),
                            'times': anomaly.get('times', ''),
                            'index': index_value,  # 新增：优先使用 index
                            'score': anomaly.get('score', 0),
                            'pattern': anomaly.get('pattern', ''),
                            'severity': anomaly.get('severity', 'medium'),
                            'data_index': anomaly.get('data_index', anomaly.get('index', -1))  # 保持兼容性
                        })
                        # 调试：打印每个异常点的关键信息
                        log_info(f"[QUERY] 异常点: indicator={anomaly.get('indicator')}, times={anomaly.get('times')}, index={index_value}")
                    log_info(f"[QUERY] 提取异常点详情: {len(result['anomaly_details'])} 个")

                    # 更新透明度信息中的异常点数量
                    if 'process_info' in result:
                        result['process_info']['anomaly_count'] = len(result['anomaly_details'])

            # ========== 添加分析结果 ==========
            result['analysis_results'] = {}
            if anomaly_result:
                # 相关性分析结果
                if 'correlation' in anomaly_result:
                    result['analysis_results']['correlation'] = anomaly_result['correlation']
                # 趋势分析结果
                if 'trends' in anomaly_result:
                    result['analysis_results']['trends'] = anomaly_result['trends']
                # 模式统计
                if 'patterns' in anomaly_result:
                    result['analysis_results']['patterns'] = anomaly_result['patterns']

            # ========== 状态字段 ==========
            if perception_result:
                result['perception_status'] = 'success'
            else:
                result['perception_status'] = 'skipped'

            if anomaly_result:
                result['anomaly_status'] = 'success'
            else:
                result['anomaly_status'] = 'skipped'

            log_info("[QUERY] 查询完成，准备序列化")
            log_info(f"[QUERY] Result keys: {list(result.keys())}")
            log_info(f"[QUERY] 时序数据: influent={len(result['timeseries_data']['influent'])}, effluent={len(result['timeseries_data']['effluent'])}")
            log_info(f"[QUERY] 异常点: {len(result['anomaly_details'])} 个")

            # ========== 保存分析报告 ==========
            report = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'summary': result.get('summary', ''),
                'anomalies_count': len(result.get('anomaly_details', [])),
                'violations_count': 0,  # 暂时不统计违规
                'report': result.get('summary', ''),
                'data_info': result.get('data_info', {}),
                'process_info': result.get('process_info', {}),
                'indicators': intent.get('indicators', []),
                'time_range': intent.get('hours_back', 24)
            }

            with reports_lock:
                analysis_reports.append(report)
                # 只保留最近MAX_REPORTS次报告
                if len(analysis_reports) > MAX_REPORTS:
                    analysis_reports.pop(0)
                log_info(f"[REPORT] 分析报告已保存，当前共 {len(analysis_reports)} 份报告")

            json_str = json.dumps(result, ensure_ascii=False, cls=NumpyJSONEncoder)
            log_info("[QUERY] JSON序列化成功")
            return Response(json_str, mimetype='application/json')
        except Exception as convert_err:
            log_error(f"[JSON] 转换失败: {convert_err}")
            import traceback
            traceback.print_exc()
            error_result = {
                'status': 'error',
                'error': f'JSON转换失败: {str(convert_err)}'
            }
            json_str = json.dumps(error_result, ensure_ascii=False, cls=NumpyJSONEncoder)
            return Response(json_str, mimetype='application/json', status=500)

    except Exception as e:
        log_error(f"[QUERY] 查询处理失败: {e}")
        import traceback
        traceback.print_exc()
        error_result = {
            'status': 'error',
            'error': str(e)
        }
        json_str = json.dumps(error_result, ensure_ascii=False, cls=NumpyJSONEncoder)
        return Response(json_str, mimetype='application/json', status=500)


def llm_parse_query_intent(query: str) -> dict:
    """
    使用LLM解析查询意图

    Args:
        query: 自然语言查询

    Returns:
        解析后的意图参数
    """
    system_prompt = """你是废水监测系统的查询意图解析器。

你的任务是分析用户的自然语言查询，提取以下信息：

1. **hours_back**: 查询时间跨度（小时数）
   - 必须返回具体的数字，表示从现在往回推多少小时
   - 例如：24小时 = 24，3天 = 72，7天 = 168，1周 = 168
   - 默认值：24

2. **indicators**: 监测指标列表
   - 必须使用以下精确的指标名称（区分大小写）：
   - pH (注意：p是小写，H是大写)
   - COD (全部大写)
   - TN (全部大写)
   - NH3-N (注意：NH3是大写，N是大写，中间有连字符)
   - TP (全部大写)

3. **analysis_types**: 分析类型列表（correlation相关性, anomaly异常检测, trend趋势分析）

4. **data_source**: 数据源（influent进水, effluent出水, both两者）

**重要规则**：
- pH必须写为"pH"（不是"PH"也不是"ph"）
- NH3-N必须写为"NH3-N"（有连字符）
- 其他指标全部大写：COD, TN, TP
- 必须将时间表达转换为具体的小时数

请返回JSON格式，不要有任何其他文字。"""

    prompt = f"""请解析以下查询：

{query}

返回JSON格式：
{{
    "hours_back": 查询时间跨度的小时数（数字）,
    "indicators": ["指标1", "指标2"],
    "analysis_types": ["分析类型1", "分析类型2"],
    "data_source": "influent/effluent/both",
    "reasoning": "解析原因"
}}"""

    try:
        response = llm_client.chat(
            message=prompt,
            system_prompt=system_prompt,
            model_type="fast",
            temperature=0.0
        )

        # 解析JSON响应
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        intent = json.loads(response)
        log_info(f"[LLM_PARSE] 解析成功: {intent.get('reasoning', 'N/A')}")
        return intent

    except Exception as e:
        log_warning(f"[LLM_PARSE] LLM解析失败: {e}，使用默认值")
        return {
            "hours_back": 24,
            "indicators": ["pH", "COD"],
            "analysis_types": ["correlation", "anomaly"],
            "data_source": "both",
            "reasoning": "LLM解析失败，使用默认值"
        }


def fetch_data_for_query(intent: dict) -> dict:
    """
    根据意图获取数据

    将CSV的2024年数据映射为当前年份的实时数据

    Args:
        intent: 解析后的意图

    Returns:
        历史数据
    """
    # 从LLM解析结果中直接获取小时数
    hours_back = intent.get('hours_back', 24)  # 默认24小时
    log_info(f"[DATA] LLM解析的时间跨度: {hours_back}小时")

    # 获取CSV数据的实际时间范围
    data_time_range = data_fetcher.get_time_range("influent")

    if data_time_range and data_time_range.get('start'):
        # 将2024年的数据映射为当前年份
        data_start = datetime.fromisoformat(data_time_range['start'])
        data_end = datetime.fromisoformat(data_time_range['end'])

        # 计算数据跨度（天数）
        data_span_days = (data_end - data_start).days
        data_span_hours = data_span_days * 24

        # 使用当前时间作为结束时间，开始时间 = 当前时间 - 查询小时数
        current_time = datetime.now()
        end_time = current_time
        start_time = current_time - timedelta(hours=hours_back)

        # 如果查询时间超过数据范围，使用整个数据范围
        if hours_back > data_span_hours:
            log_info(f"[DATA] 查询时间({hours_back}小时)超过数据范围({data_span_hours}小时)，使用全部数据")
            mapped_start = current_time - timedelta(days=data_span_days)
            time_range = {"start": mapped_start, "end": current_time}
        else:
            log_info(f"[DATA] 查询时间范围（最近{hours_back}小时）: {start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')}")
            time_range = {"start": start_time, "end": end_time}
    else:
        # 回退到相对时间
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        time_range = {"start": start_time, "end": end_time}
        log_info(f"[DATA] 使用相对时间范围: {start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')}")

    # 获取数据
    indicators = intent.get('indicators', ["pH", "COD"])
    data_source = intent.get('data_source', 'both')

    return data_fetcher.fetch_data(
        time_range=time_range,
        indicators=indicators,
        data_source=data_source
    )


def llm_generate_summary(query: str, intent: dict, perception_result: dict, anomaly_result: dict) -> str:
    """
    使用LLM生成自然语言摘要

    Args:
        query: 原始查询
        intent: 解析意图
        perception_result: 感知子智能体结果
        anomaly_result: 异常检测子智能体结果

    Returns:
        自然语言摘要
    """
    system_prompt = """你是废水监测系统的报告生成助手。

你的任务是基于子智能体的分析结果，生成面向监管人员的自然语言报告。
报告应该：
1. 简洁明了，突出重点
2. 使用专业的监测术语
3. 给出明确的结论和建议"""

    prompt = f"""请基于以下分析结果生成报告：

用户查询: {query}

分析结果:
- 感知分析: {json.dumps(perception_result, ensure_ascii=False, cls=NumpyJSONEncoder)[:500] if perception_result else '无'}
- 异常检测: {json.dumps(anomaly_result, ensure_ascii=False, cls=NumpyJSONEncoder)[:500] if anomaly_result else '无'}

请生成一份简洁的监测报告，包括：
1. 数据概况
2. 主要发现
3. 异常情况
4. 建议措施

报告："""

    try:
        response = llm_client.chat(
            message=prompt,
            system_prompt=system_prompt,
            model_type="primary",
            temperature=0.3
        )

        return response.strip()

    except Exception as e:
        log_warning(f"[LLM_SUMMARY] 生成摘要失败: {e}")
        return "报告生成失败，请查看详细分析结果。"


if __name__ == '__main__':
    # 初始化组件
    initialize_components()

    # 启动Flask应用
    port = int(os.getenv('QUERY_PORT', 5001))
    log_info("=" * 50)
    log_info("启动LLM驱动的自然语言查询接口...")
    log_info(f"  - http://localhost:{port}/api/query/health")
    log_info(f"  - http://localhost:{port}/api/query")
    log_info("")
    log_info("架构: LLM解析 → LLM调度 → LLM整合")
    log_info("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
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
from datetime import datetime, timedelta
from flask import Flask, request, Response
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
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_warning(msg):
    print(f"[WARNING] {msg}")


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


def initialize_components():
    """初始化LLM驱动组件"""
    global llm_coordinator, data_fetcher, llm_client

    # 1. 初始化LLM客户端
    try:
        llm_client = get_llm_client()
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

        # 3.2 调用异常检测子智能体（如果需要）
        anomaly_result = None
        if 'anomaly' in intent.get('analysis_types', []) or 'correlation' in intent.get('analysis_types', []):
            anomaly_result = llm_coordinator.coordinate_agent_execution(
                agent_id="anomaly-detection-agent",
                task={
                    "task_id": f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}_anomaly",
                    "description": "异常检测和相关性分析",
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
                    },
                    "previous_results": {"perception": perception_result}
                },
                previous_results={"perception": perception_result}
            )

        # ========== 步骤4: LLM整合结果生成报告 ==========
        log_info("[STEP 4] LLM整合结果生成报告...")
        summary = llm_generate_summary(query, intent, perception_result, anomaly_result)

        # ========== 返回结果 ==========
        try:
            # 简化结果，避免numpy类型
            result = {
                'status': 'success',
                'query': str(query),
                'data_info': {
                    'influent_count': int(len(historical_data.get('influent', []))),
                    'effluent_count': int(len(historical_data.get('effluent', [])))
                },
                'summary': str(summary) if summary else ''
            }

            # 只包含perception和anomaly的状态，不包含详细结果
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
            log_info(f"[QUERY] Result types: {[(k, type(v).__name__) for k, v in result.items()]}")

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
1. **time_range**: 时间范围（相对时间或绝对时间）
2. **indicators**: 监测指标列表（pH, COD, NH3-N, TN, TP等）
3. **analysis_types**: 分析类型列表（correlation相关性, anomaly异常检测, trend趋势分析）
4. **data_source**: 数据源（influent进水, effluent出水, both两者）

请返回JSON格式，不要有任何其他文字。"""

    prompt = f"""请解析以下查询：

{query}

返回JSON格式：
{{
    "time_range": {{"start": "说明开始时间", "end": "说明结束时间"}},
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
            "time_range": {"start": "now - 24h", "end": "now"},
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
    # 解析时间范围 - 从LLM响应中提取小时数
    time_range_str = intent.get('time_range', {})
    start_str = time_range_str.get('start', 'now - 24h')
    end_str = time_range_str.get('end', 'now')

    # 解析相对时间（如 "now - 48h"）
    hours_back = 24  # 默认24小时
    if '48' in str(start_str) or '48' in str(time_range_str):
        hours_back = 48
    elif '小时' in str(start_str):
        import re
        match = re.search(r'(\d+)\s*小时', str(start_str))
        if match:
            hours_back = int(match.group(1))

    # 获取CSV数据的实际时间范围
    data_time_range = data_fetcher.get_time_range("influent")

    if data_time_range and data_time_range.get('start'):
        # 将2024年的数据映射为当前年份
        data_start = datetime.fromisoformat(data_time_range['start'])
        data_end = datetime.fromisoformat(data_time_range['end'])

        # 计算数据跨度（天数）
        data_span_days = (data_end - data_start).days

        # 使用当前时间作为结束时间，开始时间 = 当前时间 - 数据跨度
        current_time = datetime.now()
        mapped_end = current_time
        mapped_start = current_time - timedelta(days=data_span_days)

        # 如果查询指定了更短的时间范围，使用查询的时间范围
        if hours_back < data_span_days * 24:
            # 使用查询的时间范围（最近的N小时）
            end_time = current_time
            start_time = current_time - timedelta(hours=hours_back)

            log_info(f"[DATA] 查询时间范围（最近{hours_back}小时）: {start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')}")
            time_range = {"start": start_time, "end": end_time}
        else:
            # 使用整个数据范围
            log_info(f"[DATA] 使用全部数据范围: {mapped_start.strftime('%Y-%m-%d')} ~ {mapped_end.strftime('%Y-%m-%d')} (映射自2024年数据)")
            time_range = {"start": mapped_start, "end": mapped_end}
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
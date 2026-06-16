#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面服务器 - 提供静态文件服务和API聚合

整合现有的query_interface和app_orchestrator功能，
为Web界面提供统一的API接口。
"""

import os
import sys
import requests
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "middleware"))

app = Flask(__name__, static_folder='static')
app.config['JSON_SORT_KEYS'] = False

# ==================== 静态文件路由 ====================

@app.route('/')
def index():
    """主页面"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件服务"""
    return send_from_directory(app.static_folder, path)


# ==================== 健康检查 ====================

@app.route('/api/web/health', methods=['GET'])
def health():
    """健康检查"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'web_interface'
    })


# ==================== API代理 ====================

@app.route('/api/web/query', methods=['POST'])
def proxy_query():
    """代理查询请求到query_interface"""
    try:
        data = request.get_json()
        query = data.get('query')

        if not query:
            return jsonify({'error': 'Missing query'}), 400

        print(f"[WEB] 收到查询请求: {query[:50]}...")

        # 转发到query_interface
        response = requests.post(
            'http://localhost:5001/api/query',
            json={'query': query},
            timeout=300
        )

        print(f"[WEB] 查询响应状态: {response.status_code}")

        return jsonify(response.json()), response.status_code

    except requests.exceptions.ConnectionError:
        print("[WEB] 错误: 查询服务未启动")
        return jsonify({
            'status': 'error',
            'error': '查询服务未启动，请先运行: python middleware/query_interface.py'
        }), 503
    except Exception as e:
        print(f"[WEB] 查询代理错误: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/web/monitoring/metrics', methods=['GET'])
def proxy_monitoring_metrics():
    """代理监控指标请求"""
    try:
        response = requests.get('http://localhost:5000/metrics', timeout=10)
        return response.text, response.status_code, {'Content-Type': response.headers.get('Content-Type')}
    except requests.exceptions.ConnectionError:
        return jsonify({'error': '监控服务未启动'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/web/monitoring/analysis', methods=['GET'])
def proxy_monitoring_analysis():
    """
    代理分析结果请求

    优先从查询接口获取分析报告（方案2），
    如果没有则尝试从监控服务获取
    """
    try:
        # 首先尝试从查询接口获取
        response = requests.get('http://localhost:5001/api/query/analysis', timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 将查询报告转换为前端期望的格式
            results = []
            for report in data.get('results', []):
                results.append({
                    'timestamp': report.get('timestamp'),
                    'anomalies_count': report.get('anomalies_count', 0),
                    'violations_count': report.get('violations_count', 0),
                    'report': report.get('report', report.get('summary', '')),
                    'query': report.get('query', ''),
                    'alerts': []  # 查询接口暂不提供alerts
                })
            return jsonify({
                'status': 'ok',
                'total': len(results),
                'results': results
            })
    except requests.exceptions.ConnectionError:
        pass  # 继续尝试监控服务
    except Exception as e:
        pass  # 继续尝试监控服务

    # 如果查询接口失败，尝试监控服务
    try:
        response = requests.get('http://localhost:5000/api/analyze/results', timeout=10)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({'status': 'ok', 'total': 0, 'results': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/web/status', methods=['GET'])
def get_services_status():
    """获取所有服务状态"""
    services = {
        'web': {'status': 'running', 'port': 8080},
        'query_interface': check_service('http://localhost:5001/api/query/health'),
        'monitoring': check_service('http://localhost:5000/health')
    }
    return jsonify(services)


def check_service(url):
    """检查服务是否可用"""
    try:
        response = requests.get(url, timeout=2)
        return {'status': 'running' if response.status_code == 200 else 'error'}
    except:
        return {'status': 'stopped'}


# ==================== 启动服务器 ====================

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8080))

    print("=" * 60)
    print("  废水监测系统 - Web界面服务器")
    print("=" * 60)
    print(f"  访问地址: http://localhost:{port}")
    print(f"  静态文件: {Path(__file__).parent / 'static'}")
    print("")
    print("  依赖服务:")
    print("    - 查询接口 (端口5001): python middleware/query_interface.py")
    print("    - 监控接口 (端口5000): python middleware/app_orchestrator.py")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=False)

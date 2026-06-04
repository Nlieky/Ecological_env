# Web界面与可视化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建现代化的Web界面，替代终端CLI，提供自然语言查询和实时监控可视化

**Architecture:** Flask后端 + HTML/CSS/JS前端，使用Chart.js实现数据可视化

**Tech Stack:** Python Flask, HTML5, CSS3, Vanilla JavaScript, Chart.js, Axios

---

## 任务概览

1. 创建Web后端服务器 (`web_interface.py`)
2. 创建HTML主页面
3. 实现查询界面和结果可视化
4. 实现实时监控仪表板
5. 样式美化和响应式设计

---

## Task 1: 创建Web后端服务器

**Files:**
- Create: `middleware/web_interface.py`
- Modify: `middleware/app_orchestrator.py` (添加CORS支持)

- [ ] **Step 1: 创建基础的Flask Web服务器**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面服务器 - 提供静态文件服务和API聚合

整合现有的query_interface和app_orchestrator功能，
为Web界面提供统一的API接口。
"""

import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, Response
from flask_cors import CORS

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "middleware"))

app = Flask(__name__, static_folder='static')
CORS(app)  # 启用跨域支持

# 静态文件路由
@app.route('/')
def index():
    """主页面"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """静态文件服务"""
    return send_from_directory(app.static_folder, path)

# 健康检查
@app.route('/api/web/health', methods=['GET'])
def health():
    """健康检查"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'web_interface'
    })

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8080))
    print(f"[WEB] 启动Web界面服务器: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
```

保存文件: `middleware/web_interface.py`

- [ ] **Step 2: 运行测试**

```bash
cd E:/project/Ecological_env
python middleware/web_interface.py
```

预期输出:
```
[WEB] 启动Web界面服务器: http://localhost:8080
 * Running on http://0.0.0.0:8080
```

- [ ] **Step 3: 创建static目录结构**

```bash
mkdir -p middleware/static/css
mkdir -p middleware/static/js
touch middleware/static/index.html
```

- [ ] **Step 4: 提交初始实现**

```bash
git add middleware/web_interface.py
git commit -m "feat(web): 添加Web界面服务器基础框架"
```

---

## Task 2: 创建HTML主页面

**Files:**
- Create: `middleware/static/index.html`

- [ ] **Step 1: 创建基础HTML结构**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>废水虚假排放智能监测系统</title>
    <link rel="stylesheet" href="/css/styles.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <!-- Axios -->
    <script src="https://cdn.jsdelivr.net/npm/axios@1.6.0/dist/axios.min.js"></script>
</head>
<body>
    <div class="container">
        <!-- 头部导航 -->
        <header class="header">
            <div class="logo">
                <h1>🏭 废水虚假排放智能监测系统</h1>
                <p class="subtitle">LLM驱动的多智能体协同分析平台</p>
            </div>
            <nav class="tabs">
                <button class="tab-btn active" data-tab="query">🔍 智能查询</button>
                <button class="tab-btn" data-tab="monitoring">📊 实时监控</button>
                <button class="tab-btn" data-tab="analysis">📈 分析报告</button>
            </nav>
        </header>

        <!-- 查询模式面板 -->
        <section id="query-panel" class="panel active">
            <div class="query-section">
                <div class="query-input-wrapper">
                    <textarea id="query-input" placeholder="请输入查询问题...

示例查询：
• 过去24小时pH和COD之间的相关性怎么样？
• 检测最近一周的数据异常
• 分析氨氮和总磷的变化趋势"></textarea>
                    <div class="query-actions">
                        <button id="query-btn" class="btn btn-primary">
                            <span class="btn-icon">🔍</span>
                            <span class="btn-text">开始分析</span>
                        </button>
                        <button id="clear-btn" class="btn btn-secondary">
                            <span class="btn-text">清空</span>
                        </button>
                    </div>
                </div>

                <!-- 查询状态 -->
                <div id="query-status" class="status-box hidden">
                    <div class="status-indicator">
                        <div class="spinner"></div>
                        <span class="status-text">正在分析中...</span>
                    </div>
                    <div class="progress-steps">
                        <div class="step" data-step="parse">
                            <span class="step-icon">📝</span>
                            <span class="step-text">解析意图</span>
                        </div>
                        <div class="step" data-step="fetch">
                            <span class="step-icon">📊</span>
                            <span class="step-text">获取数据</span>
                        </div>
                        <div class="step" data-step="analyze">
                            <span class="step-icon">🤖</span>
                            <span class="step-text">智能分析</span>
                        </div>
                        <div class="step" data-step="report">
                            <span class="step-icon">📋</span>
                            <span class="step-text">生成报告</span>
                        </div>
                    </div>
                </div>

                <!-- 查询结果 -->
                <div id="query-result" class="result-box hidden">
                    <div class="result-header">
                        <h3>📊 分析结果</h3>
                    </div>
                    <div class="result-content">
                        <div class="result-summary" id="result-summary"></div>
                        <div class="result-charts" id="result-charts"></div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 实时监控面板 -->
        <section id="monitoring-panel" class="panel">
            <div class="monitoring-section">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-title">进水 pH</div>
                        <div class="metric-value" id="influent-ph">--</div>
                        <div class="metric-unit">pH</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">进水 COD</div>
                        <div class="metric-value" id="influent-cod">--</div>
                        <div class="metric-unit">mg/L</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">进水 TN</div>
                        <div class="metric-value" id="influent-tn">--</div>
                        <div class="metric-unit">mg/L</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">出水 pH</div>
                        <div class="metric-value" id="effluent-ph">--</div>
                        <div class="metric-unit">pH</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">出水 COD</div>
                        <div class="metric-value" id="effluent-cod">--</div>
                        <div class="metric-unit">mg/L</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">系统状态</div>
                        <div class="metric-value" id="system-status">--</div>
                        <div class="metric-unit">状态</div>
                    </div>
                </div>

                <div class="charts-grid">
                    <div class="chart-container">
                        <canvas id="realtime-chart"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- 分析报告面板 -->
        <section id="analysis-panel" class="panel">
            <div class="analysis-section">
                <h2>📈 最近分析报告</h2>
                <div id="analysis-list" class="analysis-list">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        </section>
    </div>

    <script src="/js/app.js"></script>
    <script src="/js/charts.js"></script>
    <script src="/js/monitoring.js"></script>
</body>
</html>
```

保存文件: `middleware/static/index.html`

- [ ] **Step 2: 测试页面加载**

启动Web服务器并访问 `http://localhost:8080`，验证页面能正常加载。

- [ ] **Step 3: 提交**

```bash
git add middleware/static/index.html
git commit -m "feat(web): 添加HTML主页面结构"
```

---

## Task 3: 实现CSS样式

**Files:**
- Create: `middleware/static/css/styles.css`

- [ ] **Step 1: 创建样式文件**

```css
/* ========== 全局样式 ========== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --success-color: #22c55e;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --bg-color: #f8fafc;
    --card-bg: #ffffff;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --border-color: #e2e8f0;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    background-color: var(--bg-color);
    color: var(--text-primary);
    line-height: 1.6;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

/* ========== 头部导航 ========== */
.header {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-md);
}

.logo h1 {
    font-size: 28px;
    margin-bottom: 4px;
}

.subtitle {
    font-size: 14px;
    opacity: 0.9;
}

.tabs {
    display: flex;
    gap: 8px;
    margin-top: 20px;
}

.tab-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s ease;
}

.tab-btn:hover {
    background: rgba(255, 255, 255, 0.2);
}

.tab-btn.active {
    background: white;
    color: var(--primary-color);
    border-color: white;
}

/* ========== 面板 ========== */
.panel {
    display: none;
}

.panel.active {
    display: block;
}

/* ========== 查询界面 ========== */
.query-section {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow-md);
}

.query-input-wrapper {
    margin-bottom: 20px;
}

#query-input {
    width: 100%;
    min-height: 120px;
    padding: 16px;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    font-size: 16px;
    font-family: inherit;
    resize: vertical;
    transition: border-color 0.3s ease;
}

#query-input:focus {
    outline: none;
    border-color: var(--primary-color);
}

.query-actions {
    display: flex;
    gap: 12px;
    margin-top: 12px;
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 8px;
}

.btn-primary {
    background: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

.btn-secondary {
    background: var(--secondary-color);
    color: white;
}

.btn-secondary:hover {
    background: #475569;
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* ========== 状态指示 ========== */
.status-box {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}

.status-box.hidden {
    display: none;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 3px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.progress-steps {
    display: flex;
    justify-content: space-between;
    gap: 8px;
}

.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    opacity: 0.5;
    transition: opacity 0.3s ease;
}

.step.active {
    opacity: 1;
}

.step-icon {
    font-size: 24px;
}

.step-text {
    font-size: 12px;
    color: var(--text-secondary);
}

/* ========== 结果展示 ========== */
.result-box {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 20px;
    margin-top: 20px;
}

.result-box.hidden {
    display: none;
}

.result-header {
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 12px;
    margin-bottom: 16px;
}

.result-summary {
    margin-bottom: 20px;
    line-height: 1.8;
}

.result-charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
}

.chart-wrapper {
    background: var(--bg-color);
    border-radius: 8px;
    padding: 16px;
}

.chart-wrapper canvas {
    max-height: 300px;
}

/* ========== 实时监控 ========== */
.monitoring-section {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow-md);
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.metric-card {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}

.metric-title {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.metric-value {
    font-size: 28px;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 4px;
}

.metric-unit {
    font-size: 12px;
    color: var(--text-secondary);
}

.charts-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
}

.chart-container {
    background: var(--bg-color);
    border-radius: 8px;
    padding: 16px;
    min-height: 400px;
}

/* ========== 分析报告 ========== */
.analysis-section {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow-md);
}

.analysis-section h2 {
    margin-bottom: 20px;
    color: var(--text-primary);
}

.analysis-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.analysis-item {
    background: var(--bg-color);
    border-radius: 8px;
    padding: 16px;
    border-left: 4px solid var(--primary-color);
}

.analysis-item.alert {
    border-left-color: var(--danger-color);
}

.analysis-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
}

.analysis-time {
    font-size: 14px;
    color: var(--text-secondary);
}

.analysis-content {
    font-size: 14px;
    line-height: 1.6;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
    .container {
        padding: 12px;
    }

    .header {
        padding: 16px 20px;
    }

    .logo h1 {
        font-size: 20px;
    }

    .tabs {
        flex-wrap: wrap;
    }

    .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .result-charts {
        grid-template-columns: 1fr;
    }
}

/* ========== 工具类 ========== */
.hidden {
    display: none !important;
}

.loading {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}

.error {
    color: var(--danger-color);
    background: #fef2f2;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #fecaca;
}
```

保存文件: `middleware/static/css/styles.css`

- [ ] **Step 2: 提交**

```bash
git add middleware/static/css/styles.css
git commit -m "feat(web): 添加CSS样式"
```

---

## Task 4: 实现核心JavaScript功能

**Files:**
- Create: `middleware/static/js/app.js`
- Create: `middleware/static/js/charts.js`
- Create: `middleware/static/js/monitoring.js`

- [ ] **Step 1: 创建主应用逻辑 (app.js)**

```javascript
// ========== 配置 ==========
const API_BASE = window.location.origin;
const QUERY_API = 'http://localhost:5001/api/query';
const MONITORING_API = 'http://localhost:5000';

// ========== 状态管理 ==========
const state = {
    currentTab: 'query',
    queryInProgress: false,
    lastQueryResult: null
};

// ========== DOM 元素 ==========
const elements = {
    queryInput: null,
    queryBtn: null,
    clearBtn: null,
    queryStatus: null,
    queryResult: null,
    resultSummary: null,
    resultCharts: null,
    tabButtons: null,
    panels: null
};

// ========== 初始化 ==========
function init() {
    // 获取DOM元素
    elements.queryInput = document.getElementById('query-input');
    elements.queryBtn = document.getElementById('query-btn');
    elements.clearBtn = document.getElementById('clear-btn');
    elements.queryStatus = document.getElementById('query-status');
    elements.queryResult = document.getElementById('query-result');
    elements.resultSummary = document.getElementById('result-summary');
    elements.resultCharts = document.getElementById('result-charts');
    elements.tabButtons = document.querySelectorAll('.tab-btn');
    elements.panels = document.querySelectorAll('.panel');

    // 绑定事件
    elements.queryBtn.addEventListener('click', handleQuery);
    elements.clearBtn.addEventListener('click', handleClear);
    elements.tabButtons.forEach(btn => {
        btn.addEventListener('click', handleTabSwitch);
    });

    // 加载历史分析报告
    loadAnalysisReports();

    console.log('[APP] 应用初始化完成');
}

// ========== 标签切换 ==========
function handleTabSwitch(e) {
    const tabId = e.target.dataset.tab;
    if (!tabId) return;

    // 更新状态
    state.currentTab = tabId;

    // 更新UI
    elements.tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    elements.panels.forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabId}-panel`);
    });

    // 如果切换到监控面板，启动监控
    if (tabId === 'monitoring') {
        startMonitoring();
    }

    // 如果切换到分析面板，刷新报告
    if (tabId === 'analysis') {
        loadAnalysisReports();
    }
}

// ========== 查询处理 ==========
async function handleQuery() {
    const query = elements.queryInput.value.trim();
    if (!query) {
        alert('请输入查询内容');
        return;
    }

    if (state.queryInProgress) {
        console.log('[APP] 查询正在进行中，忽略重复请求');
        return;
    }

    try {
        state.queryInProgress = true;
        updateQueryUI('loading', '正在处理查询...');

        // 发送查询请求
        const response = await axios.post(QUERY_API, { query }, {
            timeout: 300000 // 5分钟超时
        });

        if (response.data.status === 'success') {
            state.lastQueryResult = response.data;
            updateQueryUI('success', response.data);
        } else {
            updateQueryUI('error', response.data.error || '查询失败');
        }

    } catch (error) {
        console.error('[APP] 查询失败:', error);
        updateQueryUI('error', error.message || '网络错误，请检查服务是否启动');
    } finally {
        state.queryInProgress = false;
    }
}

// ========== 清空查询 ==========
function handleClear() {
    elements.queryInput.value = '';
    elements.queryResult.classList.add('hidden');
    elements.queryStatus.classList.add('hidden');
    state.lastQueryResult = null;
}

// ========== 更新查询UI ==========
function updateQueryUI(status, data) {
    switch (status) {
        case 'loading':
            elements.queryStatus.classList.remove('hidden');
            elements.queryResult.classList.add('hidden');
            elements.queryBtn.disabled = true;
            updateProgressSteps(['parse']);
            break;

        case 'success':
            elements.queryStatus.classList.add('hidden');
            elements.queryResult.classList.remove('hidden');
            elements.queryBtn.disabled = false;

            // 显示摘要
            elements.resultSummary.innerHTML = formatSummary(data);

            // 创建图表（如果有数据）
            if (data.analysis) {
                createCharts(data.analysis);
            }
            break;

        case 'error':
            elements.queryStatus.classList.add('hidden');
            elements.queryResult.classList.remove('hidden');
            elements.queryBtn.disabled = false;
            elements.resultSummary.innerHTML = `<div class="error">❌ ${data}</div>`;
            break;
    }
}

// ========== 更新进度步骤 ==========
function updateProgressSteps(steps) {
    const allSteps = ['parse', 'fetch', 'analyze', 'report'];
    document.querySelectorAll('.step').forEach(step => {
        const stepName = step.dataset.step;
        const isActive = steps.includes(stepName);
        step.classList.toggle('active', isActive);
    });
}

// ========== 格式化摘要 ==========
function formatSummary(data) {
    let html = '';

    if (data.summary) {
        html += `<div class="summary-text">${data.summary}</div>`;
    }

    if (data.data_info) {
        html += `
            <div class="data-info">
                <h4>📊 数据概况</h4>
                <p>进水数据: ${data.data_info.influent_count || 0} 条</p>
                <p>出水数据: ${data.data_info.effluent_count || 0} 条</p>
            </div>
        `;
    }

    return html;
}

// ========== 创建图表 ==========
function createCharts(analysisData) {
    elements.resultCharts.innerHTML = '';

    // 相关性图表
    if (analysisData.correlation) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-wrapper';
        chartDiv.innerHTML = '<canvas id="correlation-chart"></canvas>';
        elements.resultCharts.appendChild(chartDiv);

        setTimeout(() => {
            createCorrelationChart('correlation-chart', analysisData.correlation);
        }, 100);
    }

    // 异常图表
    if (analysisData.anomaly) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-wrapper';
        chartDiv.innerHTML = '<canvas id="anomaly-chart"></canvas>';
        elements.resultCharts.appendChild(chartDiv);

        setTimeout(() => {
            createAnomalyChart('anomaly-chart', analysisData.anomaly);
        }, 100);
    }
}

// ========== 加载分析报告 ==========
async function loadAnalysisReports() {
    const listElement = document.getElementById('analysis-list');
    if (!listElement) return;

    try {
        const response = await axios.get(`${MONITORING_API}/api/analyze/results`);
        const results = response.data.results || [];

        if (results.length === 0) {
            listElement.innerHTML = '<div class="loading">暂无分析报告</div>';
            return;
        }

        listElement.innerHTML = results.slice().reverse().map(result => `
            <div class="analysis-item ${result.alerts?.length > 0 ? 'alert' : ''}">
                <div class="analysis-header">
                    <div class="analysis-time">${formatTime(result.timestamp)}</div>
                    <div class="analysis-counts">
                        异常: ${result.anomalies_count || 0} |
                        违规: ${result.violations_count || 0}
                    </div>
                </div>
                <div class="analysis-content">
                    ${formatReportText(result.report || '无报告内容')}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('[APP] 加载报告失败:', error);
        listElement.innerHTML = '<div class="error">加载失败，请检查服务是否启动</div>';
    }
}

// ========== 格式化时间 ==========
function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN');
}

// ========== 格式化报告文本 ==========
function formatReportText(text) {
    if (!text) return '';
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

// ========== 监控控制 ==========
let monitoringInterval = null;

function startMonitoring() {
    if (monitoringInterval) return;

    updateMetrics();
    monitoringInterval = setInterval(updateMetrics, 5000); // 每5秒更新
}

function stopMonitoring() {
    if (monitoringInterval) {
        clearInterval(monitoringInterval);
        monitoringInterval = null;
    }
}

async function updateMetrics() {
    try {
        const response = await axios.get(`${MONITORING_API}/api/analyze/results`);
        const latest = response.data.results?.[0];

        if (latest) {
            // 更新指标卡片
            document.getElementById('influent-ph').textContent = latest.influent_ph || '--';
            document.getElementById('influent-cod').textContent = latest.influent_cod || '--';
            document.getElementById('influent-tn').textContent = latest.influent_tn || '--';
            document.getElementById('effluent-ph').textContent = latest.effluent_ph || '--';
            document.getElementById('effluent-cod').textContent = latest.effluent_cod || '--';
            document.getElementById('system-status').textContent = latest.status || '正常';
        }
    } catch (error) {
        console.error('[APP] 更新监控数据失败:', error);
    }
}

// ========== 启动应用 ==========
document.addEventListener('DOMContentLoaded', init);
```

保存文件: `middleware/static/js/app.js`

- [ ] **Step 2: 创建图表功能 (charts.js)**

```javascript
// 图表实例存储
const chartInstances = {};

// ========== 相关性散点图 ==========
function createCorrelationChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;

    // 销毁旧图表
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 准备数据
    const labels = data.timestamps || [];
    const xData = data.x_values || [];
    const yData = data.y_values || [];

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: `${data.indicator_x || 'X'} vs ${data.indicator_y || 'Y'}`,
                data: xData.map((x, i) => ({ x, y: yData[i] })),
                backgroundColor: 'rgba(37, 99, 235, 0.6)',
                borderColor: 'rgba(37, 99, 235, 1)',
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `相关性分析 (r=${data.correlation || 'N/A'})`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.x.toFixed(2)}, ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: data.indicator_x || 'X'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: data.indicator_y || 'Y'
                    }
                }
            }
        }
    });
}

// ========== 异常检测图表 ==========
function createAnomalyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const anomalies = data.anomalies || [];
    const labels = anomalies.map((a, i) => a.time || `T${i}`);
    const scores = anomalies.map(a => a.score || 0);

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '异常分数',
                data: scores,
                backgroundColor: scores.map(s =>
                    s > 0.8 ? 'rgba(239, 68, 68, 0.6)' :
                    s > 0.5 ? 'rgba(245, 158, 11, 0.6)' :
                    'rgba(34, 197, 94, 0.6)'
                ),
                borderColor: scores.map(s =>
                    s > 0.8 ? 'rgba(239, 68, 68, 1)' :
                    s > 0.5 ? 'rgba(245, 158, 11, 1)' :
                    'rgba(34, 197, 94, 1)'
                ),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `异常检测结果 (共 ${anomalies.length} 个异常点)`
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    title: {
                        display: true,
                        text: '异常分数'
                    }
                }
            }
        }
    });
}

// ========== 时序趋势图 ==========
function createTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const labels = data.timestamps || [];
    const datasets = (data.series || []).map((series, index) => ({
        label: series.name || `系列 ${index + 1}`,
        data: series.values || [],
        borderColor: getColor(index),
        backgroundColor: getColor(index, 0.2),
        tension: 0.4,
        fill: false
    }));

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: data.title || '时序趋势'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: data.unit || ''
                    }
                }
            }
        }
    });
}

// ========== 工具函数 ==========
function getColor(index, alpha = 1) {
    const colors = [
        `rgba(37, 99, 235, ${alpha})`,   // blue
        `rgba(34, 197, 94, ${alpha})`,   // green
        `rgba(245, 158, 11, ${alpha})`,  // amber
        `rgba(239, 68, 68, ${alpha})`,   // red
        `rgba(168, 85, 247, ${alpha})`,  // purple
        `rgba(236, 72, 153, ${alpha})`   // pink
    ];
    return colors[index % colors.length];
}
```

保存文件: `middleware/static/js/charts.js`

- [ ] **Step 3: 创建监控功能 (monitoring.js)**

```javascript
// 实时监控管理器
class MonitoringManager {
    constructor() {
        this.intervalId = null;
        this.updateInterval = 5000; // 5秒更新
        this.chartInstance = null;
    }

    start() {
        if (this.intervalId) {
            console.log('[MONITOR] 监控已在运行');
            return;
        }

        console.log('[MONITOR] 启动实时监控');
        this.update();
        this.intervalId = setInterval(() => this.update(), this.updateInterval);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('[MONITOR] 停止实时监控');
        }
    }

    async update() {
        try {
            // 获取最新数据
            const [metricsData, analysisData] = await Promise.all([
                this.fetchMetrics(),
                this.fetchAnalysisData()
            ]);

            // 更新指标卡片
            this.updateMetricCards(metricsData);

            // 更新图表
            this.updateRealtimeChart(analysisData);

        } catch (error) {
            console.error('[MONITOR] 更新失败:', error);
        }
    }

    async fetchMetrics() {
        try {
            const response = await axios.get('http://localhost:5000/metrics');
            // 解析Prometheus文本格式
            return this.parsePrometheusMetrics(response.data);
        } catch (error) {
            console.error('[MONITOR] 获取指标失败:', error);
            return {};
        }
    }

    parsePrometheusMetrics(text) {
        const metrics = {};
        const lines = text.split('\n');

        for (const line of lines) {
            if (line.startsWith('#') || !line.trim()) continue;

            const match = line.match(/^wastewater_(\w+)\{([^}]*)\}\s+(.+)$/);
            if (match) {
                const [, name, labels, value] = match;
                metrics[name] = parseFloat(value);
            }
        }

        return metrics;
    }

    async fetchAnalysisData() {
        try {
            const response = await axios.get('http://localhost:5000/api/analyze/results');
            return response.data.results || [];
        } catch (error) {
            console.error('[MONITOR] 获取分析数据失败:', error);
            return [];
        }
    }

    updateMetricCards(metrics) {
        const elements = {
            'influent-ph': metrics.influent_ph,
            'influent-cod': metrics.influent_cod,
            'influent-tn': metrics.influent_tn,
            'effluent-ph': metrics.effluent_ph,
            'effluent-cod': metrics.effluent_cod
        };

        for (const [id, value] of Object.entries(elements)) {
            const el = document.getElementById(id);
            if (el && value !== undefined) {
                el.textContent = value.toFixed(2);
            }
        }

        // 更新系统状态
        const statusEl = document.getElementById('system-status');
        if (statusEl) {
            const hasAlerts = metrics.wastewater_alert_total > 0;
            statusEl.textContent = hasAlerts ? '告警' : '正常';
            statusEl.style.color = hasAlerts ? '#ef4444' : '#22c55e';
        }
    }

    updateRealtimeChart(analysisData) {
        const canvas = document.getElementById('realtime-chart');
        if (!canvas) return;

        // 准备时序数据
        const labels = analysisData.map(d => {
            const date = new Date(d.timestamp);
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        });

        const anomalyCounts = analysisData.map(d => d.anomalies_count || 0);
        const violationCounts = analysisData.map(d => d.violations_count || 0);

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const ctx = canvas.getContext('2d');
        this.chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.slice(-20), // 最近20个数据点
                datasets: [
                    {
                        label: '异常数',
                        data: anomalyCounts.slice(-20),
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: '违规数',
                        data: violationCounts.slice(-20),
                        borderColor: 'rgba(239, 68, 68, 1)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '实时监控 - 异常与违规趋势'
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

// 创建全局监控实例
const monitoring = new MonitoringManager();

// 监听标签切换事件
document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab;

            if (tabId === 'monitoring') {
                monitoring.start();
            } else {
                monitoring.stop();
            }
        });
    });
});
```

保存文件: `middleware/static/js/monitoring.js`

- [ ] **Step 4: 提交**

```bash
git add middleware/static/js/
git commit -m "feat(web): 添加JavaScript功能"
```

---

## Task 5: 完善Web后端API

**Files:**
- Modify: `middleware/web_interface.py`

- [ ] **Step 1: 添加API代理功能**

在 `web_interface.py` 中添加：

```python
# 在文件顶部添加导入
import requests
from datetime import datetime

# ========== API代理 ==========

@app.route('/api/web/query', methods=['POST'])
def proxy_query():
    """代理查询请求到query_interface"""
    try:
        data = request.get_json()
        query = data.get('query')

        if not query:
            return jsonify({'error': 'Missing query'}), 400

        # 转发到query_interface
        response = requests.post(
            'http://localhost:5001/api/query',
            json={'query': query},
            timeout=300
        )
        return jsonify(response.json()), response.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({'error': '查询服务未启动，请先启动 query_interface.py'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    """代理监控分析结果请求"""
    try:
        response = requests.get('http://localhost:5000/api/analyze/results', timeout=10)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({'error': '监控服务未启动'}), 503
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
```

- [ ] **Step 2: 更新前端API配置**

修改 `app.js` 中的 API 配置：

```javascript
// 在文件顶部修改配置
const API_BASE = window.location.origin;
// 使用相对路径，由web_interface代理
```

- [ ] **Step 3: 提交**

```bash
git add middleware/web_interface.py
git commit -m "feat(web): 添加API代理功能"
```

---

## Task 6: 测试和优化

**Files:**
- Create: `tests/integration/test_web_interface.py`

- [ ] **Step 1: 创建集成测试**

```python
"""测试Web界面功能"""

import pytest
import requests
import time
from subprocess import Popen, PIPE


class TestWebInterface:
    """Web界面集成测试"""

    @pytest.fixture(scope='class')
    def web_server(self):
        """启动Web服务器"""
        proc = Popen(
            ['python', 'middleware/web_interface.py'],
            stdout=PIPE,
            stderr=PIPE
        )
        time.sleep(3)  # 等待启动
        yield 'http://localhost:8080'
        proc.terminate()

    def test_health_endpoint(self, web_server):
        """测试健康检查"""
        response = requests.get(f'{web_server}/api/web/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'

    def test_static_files(self, web_server):
        """测试静态文件服务"""
        response = requests.get(f'{web_server}/')
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('Content-Type', '')

    def test_services_status(self, web_server):
        """测试服务状态检查"""
        response = requests.get(f'{web_server}/api/web/status')
        assert response.status_code == 200
        data = response.json()
        assert 'web' in data
        assert data['web']['status'] == 'running'
```

- [ ] **Step 2: 运行测试**

```bash
cd E:/project/Ecological_env
pytest tests/integration/test_web_interface.py -v
```

- [ ] **Step 3: 手动测试**

1. 启动所有服务：
   ```bash
   # 终端1 - Web界面
   python middleware/web_interface.py

   # 终端2 - 查询接口
   python middleware/query_interface.py

   # 终端3 - 监控接口
   python middleware/app_orchestrator.py
   ```

2. 访问 `http://localhost:8080` 并测试：
   - 自然语言查询功能
   - 实时监控仪表板
   - 分析报告查看
   - 响应式布局（调整浏览器窗口）

- [ ] **Step 4: 提交**

```bash
git add tests/integration/test_web_interface.py
git commit -m "test(web): 添加Web界面集成测试"
```

---

## Task 7: 文档和部署

**Files:**
- Create: `docs/user-guide/web-interface.md`

- [ ] **Step 1: 创建用户指南**

```markdown
# Web界面用户指南

## 快速开始

### 1. 启动服务

```bash
# 启动Web界面服务器
python middleware/web_interface.py

# 启动查询接口
python middleware/query_interface.py

# 启动监控接口
python middleware/app_orchestrator.py
```

### 2. 访问界面

打开浏览器访问: http://localhost:8080

## 功能说明

### 智能查询

支持自然语言查询废水监测数据。

**示例查询：**
- "过去24小时pH和COD之间的相关性怎么样？"
- "检测最近一周的数据异常"
- "分析氨氮和总磷的变化趋势"

### 实时监控

- 查看实时指标数值
- 监控异常和违规趋势
- 系统状态检查

### 分析报告

- 查看历史分析报告
- 违规和异常详情
- LLM生成的智能建议

## 故障排除

### 无法连接到服务

检查对应端口的服务是否启动：
- Web界面: 8080
- 查询接口: 5001
- 监控接口: 5000

### 查询无响应

1. 检查查询接口是否启动
2. 查看浏览器控制台错误信息
3. 确认API配置正确
```

- [ ] **Step 2: 提交**

```bash
git add docs/user-guide/web-interface.md
git commit -m "docs(web): 添加Web界面用户指南"
```

- [ ] **Step 3: 创建README更新**

在项目根目录 `README.md` 中添加Web界面说明。

---

## 验收标准

完成后：
- ✅ Web界面能正常访问 (http://localhost:8080)
- ✅ 自然语言查询功能正常工作
- ✅ 实时监控数据正确显示
- ✅ 图表可视化正确渲染
- ✅ 响应式设计在不同屏幕尺寸下正常显示
- ✅ 所有测试通过
- ✅ 用户文档完整

---

## 下一步

Web界面完成后，可以考虑：
1. 添加更多可视化类型（热力图、树图等）
2. 实现WebSocket实时推送
3. 添加用户认证和权限管理
4. 优化移动端体验

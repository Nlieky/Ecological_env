// ========== 配置 ==========
const API_BASE = window.location.origin;
const QUERY_API = `${API_BASE}/api/web/query`;
const MONITORING_API = `${API_BASE}/api/web/monitoring`;

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

    // 检查服务状态
    checkServicesStatus();

    console.log('[APP] 应用初始化完成');
}

// ========== 检查服务状态 ==========
async function checkServicesStatus() {
    try {
        const response = await axios.get(`${API_BASE}/api/web/status`);
        const services = response.data;

        console.log('[APP] 服务状态:', services);

        // 显示服务状态警告
        if (services.query_interface.status === 'stopped') {
            showServiceWarning('查询服务未启动，查询功能将不可用。请运行: python middleware/query_interface.py');
        }
        if (services.monitoring.status === 'stopped') {
            showServiceWarning('监控服务未启动，监控功能将不可用。请运行: python middleware/app_orchestrator.py');
        }
    } catch (error) {
        console.error('[APP] 检查服务状态失败:', error);
    }
}

function showServiceWarning(message) {
    // 在页面顶部显示警告
    const warning = document.createElement('div');
    warning.className = 'service-warning';
    warning.textContent = '⚠️ ' + message;
    warning.style.cssText = `
        background: #fef3c7;
        color: #92400e;
        padding: 12px 20px;
        margin-bottom: 16px;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
    `;
    document.querySelector('.container').insertBefore(
        warning,
        document.querySelector('.header').nextSibling
    );
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
        if (typeof startMonitoring === 'function') {
            startMonitoring();
        }
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
            updateQueryUI('error', response.data.error || response.data.summary || '查询完成，但未返回预期结果');
        }

    } catch (error) {
        console.error('[APP] 查询失败:', error);
        let errorMsg = '网络错误，请检查服务是否启动';

        if (error.response) {
            errorMsg = error.response.data?.error || errorMsg;
        } else if (error.code === 'ECONNREFUSED') {
            errorMsg = '无法连接到服务器，请确认服务已启动';
        }

        updateQueryUI('error', errorMsg);
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
            updateProgressSteps(['parse', 'fetch', 'analyze', 'report']);
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
        // 在加载状态下，所有步骤都显示为活跃
        step.classList.toggle('active', true);
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

    // 添加处理状态
    if (data.perception_status || data.anomaly_status) {
        html += `
            <div class="data-info">
                <h4>🔧 处理状态</h4>
                <p>数据感知: ${data.perception_status === 'success' ? '✅ 已完成' : '⏭️ 已跳过'}</p>
                <p>异常检测: ${data.anomaly_status === 'success' ? '✅ 已完成' : '⏭️ 已跳过'}</p>
            </div>
        `;
    }

    return html;
}

// ========== 创建图表 ==========
function createCharts(analysisData) {
    elements.resultCharts.innerHTML = '';

    // 如果没有分析数据，显示提示
    const hasData = analysisData && (
        analysisData.correlation ||
        analysisData.anomaly ||
        analysisData.trends
    );

    if (!hasData) {
        elements.resultCharts.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">暂无图表数据</p>';
        return;
    }

    // 相关性图表
    if (analysisData.correlation) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-wrapper';
        chartDiv.innerHTML = '<canvas id="correlation-chart"></canvas>';
        elements.resultCharts.appendChild(chartDiv);

        setTimeout(() => {
            if (typeof createCorrelationChart === 'function') {
                createCorrelationChart('correlation-chart', analysisData.correlation);
            }
        }, 100);
    }

    // 异常图表
    if (analysisData.anomaly) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-wrapper';
        chartDiv.innerHTML = '<canvas id="anomaly-chart"></canvas>';
        elements.resultCharts.appendChild(chartDiv);

        setTimeout(() => {
            if (typeof createAnomalyChart === 'function') {
                createAnomalyChart('anomaly-chart', analysisData.anomaly);
            }
        }, 100);
    }

    // 趋势图表
    if (analysisData.trends && analysisData.trends.length > 0) {
        analysisData.trends.forEach((trend, index) => {
            const chartDiv = document.createElement('div');
            chartDiv.className = 'chart-wrapper';
            chartDiv.innerHTML = `<canvas id="trend-chart-${index}"></canvas>`;
            elements.resultCharts.appendChild(chartDiv);

            setTimeout(() => {
                if (typeof createTrendChart === 'function') {
                    createTrendChart(`trend-chart-${index}`, trend);
                }
            }, 100);
        });
    }
}

// ========== 加载分析报告 ==========
async function loadAnalysisReports() {
    const listElement = document.getElementById('analysis-list');
    if (!listElement) return;

    try {
        const response = await axios.get(`${MONITORING_API}/analysis`);
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
        listElement.innerHTML = '<div class="error">加载失败，请检查监控服务是否启动</div>';
    }
}

// ========== 格式化时间 ==========
function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ========== 格式化报告文本 ==========
function formatReportText(text) {
    if (!text) return '';
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

// ========== 启动应用 ==========
document.addEventListener('DOMContentLoaded', init);

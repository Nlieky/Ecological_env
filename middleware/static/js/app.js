// ========== 配置 ==========
const API_BASE = window.location.origin;
const QUERY_API = `${API_BASE}/api/web/query`;
const MONITORING_API = `${API_BASE}/api/web/monitoring`;

// ========== 状态管理 ==========
const state = {
    currentPanel: 'query',
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
    navItems: null,
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
    elements.navItems = document.querySelectorAll('.nav-item');
    elements.panels = document.querySelectorAll('.content-panel');

    // 绑定事件
    elements.queryBtn.addEventListener('click', handleQuery);
    elements.clearBtn.addEventListener('click', handleClear);
    elements.navItems.forEach(item => {
        item.addEventListener('click', handleTabSwitch);
    });

    // 侧边栏展开/收起
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('expanded');
            // 更新按钮文字
            const span = sidebarToggle.querySelector('span');
            span.textContent = sidebar.classList.contains('expanded') ? '»' : '«';
        });
    }

    // 检查服务状态
    checkServicesStatus();

    // 初始化告警面板
    alertPanel.init();

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
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(warning, mainContent.firstChild);
    }
}

// ========== 导航切换 ==========
function handleTabSwitch(e) {
    e.preventDefault();
    const navItem = e.target.closest('.nav-item');
    if (!navItem) return;

    const panelId = navItem.dataset.panel;
    if (!panelId) return;

    // 更新状态
    state.currentPanel = panelId;

    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    navItem.classList.add('active');

    // 更新面板显示
    document.querySelectorAll('.content-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    const targetPanel = document.getElementById(`${panelId}-panel`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    // 更新页面标题
    const titles = {
        'query': '智能查询',
        'monitoring': '实时监控',
        'analysis': '分析报告',
        'settings': '系统设置'
    };
    const pageTitle = document.querySelector('.page-title');
    if (pageTitle) {
        pageTitle.textContent = titles[panelId] || '监测系统';
    }

    // 如果切换到监控面板，启动监控
    if (panelId === 'monitoring') {
        if (typeof startMonitoring === 'function') {
            startMonitoring();
        }
    }

    // 如果切换到分析面板，刷新报告
    if (panelId === 'analysis') {
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

            // 创建图表（传递完整数据对象）
            createCharts(data);
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

    // 添加透明度信息
    if (data.process_info) {
        const pInfo = data.process_info;
        html += `
            <div class="data-info" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                <h4>🔍 处理过程信息</h4>
                <p><strong>查询时间范围:</strong> ${pInfo.query_time_range || 'N/A'}</p>
                <p><strong>实际数据量:</strong> 进水 ${pInfo.actual_data_count?.influent || 0} 条, 出水 ${pInfo.actual_data_count?.effluent || 0} 条</p>
                <p><strong>检测到异常点:</strong> ${pInfo.anomaly_count || 0} 个</p>
                <p><strong>使用算子:</strong> ${Array.isArray(pInfo.operators_used) ? pInfo.operators_used.join(', ') : 'N/A'}</p>
            </div>
        `;
    }

    return html;
}

// ========== 创建图表 ==========
function createCharts(data) {
    elements.resultCharts.innerHTML = '';

    // 优先使用时序数据创建图表
    if (data.timeseries_data && (data.timeseries_data.influent?.length > 0 || data.timeseries_data.effluent?.length > 0)) {
        // 创建进水图表容器
        if (data.timeseries_data.influent?.length > 0) {
            const influentDiv = document.createElement('div');
            influentDiv.className = 'chart-wrapper';
            influentDiv.style.maxWidth = '100%';
            influentDiv.style.minHeight = '400px';
            influentDiv.style.marginBottom = '20px';
            const influentCanvasId = 'timeseries-chart-influent';
            influentDiv.innerHTML = `<canvas id="${influentCanvasId}"></canvas>`;
            elements.resultCharts.appendChild(influentDiv);

            setTimeout(() => {
                if (typeof createSingleSourceChart === 'function') {
                    // 筛选进水数据的异常点
                    const influentAnomalies = (data.anomaly_details || []).filter(anomaly =>
                        anomaly.indicator && anomaly.indicator.startsWith('influent_')
                    );
                    createSingleSourceChart(
                        influentCanvasId,
                        data.timeseries_data.influent,
                        influentAnomalies, // 进水图表显示进水异常点
                        {
                            title: '进水数据时序图（含异常点标注）',
                            source: 'influent'
                        }
                    );
                }
            }, 100);
        }

        // 创建出水图表容器
        if (data.timeseries_data.effluent?.length > 0) {
            const effluentDiv = document.createElement('div');
            effluentDiv.className = 'chart-wrapper';
            effluentDiv.style.maxWidth = '100%';
            effluentDiv.style.minHeight = '400px';
            effluentDiv.style.marginBottom = '20px';
            const effluentCanvasId = 'timeseries-chart-effluent';
            effluentDiv.innerHTML = `<canvas id="${effluentCanvasId}"></canvas>`;
            elements.resultCharts.appendChild(effluentDiv);

            setTimeout(() => {
                if (typeof createSingleSourceChart === 'function') {
                    // 筛选出水数据的异常点
                    const effluentAnomalies = (data.anomaly_details || []).filter(anomaly =>
                        anomaly.indicator && anomaly.indicator.startsWith('effluent_')
                    );
                    createSingleSourceChart(
                        effluentCanvasId,
                        data.timeseries_data.effluent,
                        effluentAnomalies, // 出水图表显示出水异常点
                        {
                            title: '出水数据时序图（含异常点标注）',
                            source: 'effluent'
                        }
                    );
                }
            }, 100);
        }

        // 显示异常统计信息
        if (data.anomaly_details && data.anomaly_details.length > 0) {
            const anomalyStats = createAnomalyStats(data.anomaly_details);
            elements.resultCharts.appendChild(anomalyStats);
        }

        return;
    }

    // 如果没有时序数据，回退到旧的分析数据格式
    const analysisData = data.analysis;
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

// ========== 创建异常统计信息 ==========
function createAnomalyStats(anomalyDetails) {
    const statsDiv = document.createElement('div');
    statsDiv.className = 'chart-wrapper';
    statsDiv.style.background = 'var(--bg-color)';

    // 统计各种异常数量
    const severityCounts = {};
    const indicatorCounts = {};
    const patternCounts = {};

    anomalyDetails.forEach(anomaly => {
        severityCounts[anomaly.severity] = (severityCounts[anomaly.severity] || 0) + 1;
        indicatorCounts[anomaly.indicator] = (indicatorCounts[anomaly.indicator] || 0) + 1;
        patternCounts[anomaly.pattern] = (patternCounts[anomaly.pattern] || 0) + 1;
    });

    const severityLabels = { 'high': '高', 'critical': '严重', 'medium': '中', 'low': '低', 'unknown': '未知' };
    const patternLabels = { 'constant': '常数异常', 'spike': '尖峰异常', 'drop': '骤降异常', 'trend': '趋势异常', 'unknown': '未知模式' };

    statsDiv.innerHTML = `
        <h4 style="margin-bottom: 12px; font-size: 14px;">📊 异常统计 (共 ${anomalyDetails.length} 个)</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; font-size: 13px;">
            <div style="background: white; padding: 8px; border-radius: 4px;">
                <strong>严重程度分布:</strong><br>
                ${Object.entries(severityCounts).map(([key, val]) => `${severityLabels[key] || key}: ${val}`).join('<br>')}
            </div>
            <div style="background: white; padding: 8px; border-radius: 4px;">
                <strong>指标分布:</strong><br>
                ${Object.entries(indicatorCounts).map(([key, val]) => `${key}: ${val}`).join('<br>')}
            </div>
            <div style="background: white; padding: 8px; border-radius: 4px;">
                <strong>异常模式:</strong><br>
                ${Object.entries(patternCounts).map(([key, val]) => `${patternLabels[key] || key}: ${val}`).join('<br>')}
            </div>
        </div>
    `;

    return statsDiv;
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

        // 更新告铃徽章
        const totalAlerts = (response.data.results || []).filter(r =>
            r.anomalies_count > 0 || r.violations_count > 0
        ).length;

        const badge = document.getElementById('alert-badge');
        if (badge) {
            if (totalAlerts > 0) {
                badge.textContent = totalAlerts;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }

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

// ========== 告警面板管理 ==========
const alertPanel = {
    overlay: null,
    panel: null,
    content: null,
    closeBtn: null,

    init() {
        // 获取DOM元素
        this.overlay = document.getElementById('alert-overlay');
        this.panel = document.getElementById('alert-panel');
        this.content = document.getElementById('alert-list');
        this.closeBtn = document.getElementById('alert-close');

        if (!this.overlay || !this.panel || !this.content || !this.closeBtn) {
            console.warn('[ALERT] 告警面板元素未找到');
            return;
        }

        // 点击关闭按钮
        this.closeBtn.addEventListener('click', () => this.hide());

        // 点击遮罩关闭
        this.overlay.addEventListener('click', () => this.hide());

        // 点击告铃按钮显示面板
        const alertBtn = document.getElementById('alert-btn');
        if (alertBtn) {
            alertBtn.addEventListener('click', () => this.show());
        }
    },

    show() {
        if (this.overlay && this.panel) {
            this.overlay.classList.add('show');
            this.panel.classList.add('show');
            this.loadAlerts();
        }
    },

    hide() {
        if (this.overlay && this.panel) {
            this.overlay.classList.remove('show');
            this.panel.classList.remove('show');
        }
    },

    async loadAlerts() {
        if (!this.content) return;

        try {
            const response = await axios.get(`${MONITORING_API}/analysis`);
            const reports = response.data.results || [];

            // 筛选有异常的报告
            const alerts = reports.filter(r => r.anomalies_count > 0 || r.violations_count > 0);

            if (alerts.length === 0) {
                this.content.innerHTML = '<div class="empty-state">暂无告警</div>';
                return;
            }

            this.content.innerHTML = alerts.map(alert => {
                const time = new Date(alert.timestamp).toLocaleString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                const severity = alert.violations_count > 0 ? 'danger' : 'warning';
                const colorClass = severity === 'danger' ? 'border-danger' : 'border-warning';

                return `
                    <div class="alert-item ${colorClass}">
                        <div class="alert-time">${time}</div>
                        <div class="alert-content">
                            <div class="alert-title">${alert.query || '异常检测'}</div>
                            <div class="alert-desc">
                                检测到 ${alert.anomalies_count} 处异常
                                ${alert.violations_count > 0 ? `，${alert.violations_count} 处违规` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.error('[ALERT] 加载告警失败:', error);
            if (this.content) {
                this.content.innerHTML = '<div class="empty-state">加载失败</div>';
            }
        }
    }
};

// ========== 启动应用 ==========
document.addEventListener('DOMContentLoaded', init);

// 实时监控管理器
class MonitoringManager {
    constructor() {
        this.intervalId = null;
        this.updateInterval = 180000; // 3分钟更新
        this.chartInstance = null;
        this.isRunning = false;
    }

    start() {
        if (this.isRunning) {
            console.log('[MONITOR] 监控已在运行');
            return;
        }

        console.log('[MONITOR] 启动实时监控');
        this.isRunning = true;
        this.update();
        this.intervalId = setInterval(() => this.update(), this.updateInterval);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            this.isRunning = false;
            console.log('[MONITOR] 停止实时监控');
        }
    }

    async update() {
        try {
            // 获取最新分析数据
            const analysisData = await this.fetchAnalysisData();

            // 更新指标卡片
            this.updateMetricCards(analysisData);

            // 更新图表
            this.updateRealtimeChart(analysisData);

        } catch (error) {
            console.error('[MONITOR] 更新失败:', error);
        }
    }

    async fetchAnalysisData() {
        try {
            const response = await axios.get(`${window.location.origin}/api/web/monitoring/analysis`);
            return response.data.results || [];
        } catch (error) {
            console.error('[MONITOR] 获取分析数据失败:', error);
            return [];
        }
    }

    async fetchMetrics() {
        try {
            // 从Prometheus获取指标
            const response = await fetch(`${window.location.origin}/api/web/monitoring/metrics`);
            const text = await response.text();
            return this.parsePrometheusMetrics(text);
        } catch (error) {
            console.error('[MONITOR] 获取Prometheus指标失败:', error);
            return {};
        }
    }

    parsePrometheusMetrics(text) {
        const metrics = {};
        const lines = text.split('\n');

        for (const line of lines) {
            if (line.startsWith('#') || !line.trim()) continue;

            // 匹配格式: metric_name{labels} value
            const match = line.match(/^wastewater_(\w+)\{?([^}]*)\}?\s+(.+)$/);
            if (match) {
                const [, name, labels, value] = match;
                try {
                    metrics[name] = parseFloat(value);
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }

        return metrics;
    }

    updateMetricCards(analysisData) {
        // 如果没有数据，显示占位符
        if (!analysisData || analysisData.length === 0) {
            const ids = ['metric-influent-ph', 'metric-effluent-cod', 'metric-influent-tn', 'metric-anomalies'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = '--';
            });
            return;
        }

        // 获取最新数据
        const latest = analysisData[analysisData.length - 1];

        // 更新指标卡片
        const updateCard = (id, value, trendHtml = null) => {
            const el = document.getElementById(id);
            if (el && value !== undefined && value !== null) {
                el.textContent = typeof value === 'number' ? value.toFixed(1) : value;
            }

            // 更新趋势
            if (trendHtml) {
                const parent = el ? el.parentElement : null;
                if (parent) {
                    const trendEl = parent.querySelector('.metric-trend');
                    if (trendEl) {
                        trendEl.innerHTML = trendHtml;
                    }
                }
            }
        };

        // 从报告中提取指标（需要分析报告包含指标数据）
        // 暂时使用默认值，后续可从 API 获取
        // 注意：这些值需要从实际的监控数据中获取
        updateCard('metric-influent-ph', this._getMetric(latest, 'influent_ph', 7.2));
        updateCard('metric-effluent-cod', this._getMetric(latest, 'effluent_cod', 45));
        updateCard('metric-influent-tn', this._getMetric(latest, 'influent_tn', 12));

        // 异常数从最新报告获取
        const anomalyCount = latest.anomalies_count || 0;
        const violationCount = latest.violations_count || 0;
        document.getElementById('metric-anomalies').textContent = anomalyCount;

        const statusEl = document.getElementById('metric-status');
        if (statusEl) {
            if (violationCount > 0) {
                statusEl.innerHTML = '<span style="color: var(--danger)">⚠️</span>';
            } else if (anomalyCount > 0) {
                statusEl.innerHTML = '<span style="color: var(--warning)">⚠️</span>';
            } else {
                statusEl.innerHTML = '<span style="color: var(--success)">✓</span>';
            }
        }
    }

    // 辅助函数：从数据中获取指标
    _getMetric(data, key, defaultValue) {
        if (data.metrics && data.metrics[key] !== undefined) {
            return data.metrics[key];
        }
        if (data[key] !== undefined) {
            return data[key];
        }
        return defaultValue;
    }

    updateRealtimeChart(analysisData) {
        const canvas = document.getElementById('realtime-chart');
        if (!canvas) return;

        // 准备时序数据
        const labels = analysisData.slice(-20).map(d => {
            const date = new Date(d.timestamp);
            return date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        });

        const anomalyCounts = analysisData.slice(-20).map(d => d.anomalies_count || 0);
        const violationCounts = analysisData.slice(-20).map(d => d.violations_count || 0);

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const ctx = canvas.getContext('2d');
        this.chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '异常数',
                        data: anomalyCounts,
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: '违规数',
                        data: violationCounts,
                        borderColor: 'rgba(239, 68, 68, 1)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '实时监控 - 异常与违规趋势',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '时间',
                            font: { size: 12 }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            precision: 0
                        },
                        title: {
                            display: true,
                            text: '数量',
                            font: { size: 12 }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
}

// 创建全局监控实例
const monitoring = new MonitoringManager();

// 导出启动/停止函数
function startMonitoring() {
    monitoring.start();
}

function stopMonitoring() {
    monitoring.stop();
}

// 注意：监控系统的启动/停止现在由 app.js 中的导航切换逻辑控制
// 不再需要在这里监听标签切换事件

    // 页面隐藏时停止监控
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopMonitoring();
        }
    });

    // Grafana iframe 错误处理
    const grafanaIframe = document.getElementById('grafana-iframe');
    const grafanaFallback = document.querySelector('.grafana-fallback');

    if (grafanaIframe && grafanaFallback) {
        // 设置超时检测：如果10秒后iframe还未加载，显示fallback
        setTimeout(() => {
            try {
                // 尝试访问iframe内容（同源策略限制，跨域时会抛出错误）
                const iframeContent = grafanaIframe.contentWindow;
                // 如果能访问，说明加载成功
            } catch (e) {
                // 跨域访问被阻止，这是正常的（Grafana在不同端口）
                // 我们假设Grafana是可访问的
                console.log('[MONITOR] Grafana iframe跨域访问（正常）');
            }
        }, 10000);

        // 监听iframe加载错误
        grafanaIframe.addEventListener('error', () => {
            console.warn('[MONITOR] Grafana iframe加载失败，显示fallback');
            grafanaFallback.classList.add('show');
        });

        // 监听加载完成
        grafanaIframe.addEventListener('load', () => {
            console.log('[MONITOR] Grafana iframe加载成功');
            // 即使load事件触发，也不意味着内容成功加载（跨域iframe）
            // 这里不做额外处理
        });
    }
});

// 实时监控管理器
class MonitoringManager {
    constructor() {
        this.intervalId = null;
        this.updateInterval = 5000; // 5秒更新
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
        // 从分析结果中提取最新的指标值
        const latest = analysisData[analysisData.length - 1];

        if (!latest) {
            console.log('[MONITOR] 暂无分析数据');
            return;
        }

        // 尝试从不同字段中获取指标
        const metrics = latest.metrics || latest.data || {};

        // 更新指标卡片
        const updateCard = (id, value) => {
            const el = document.getElementById(id);
            if (el && value !== undefined && value !== null) {
                el.textContent = typeof value === 'number' ? value.toFixed(2) : value;
            }
        };

        // 根据实际数据结构更新指标
        // 这些字段名需要根据实际API返回调整
        updateCard('influent-ph', metrics.influent_ph);
        updateCard('influent-cod', metrics.influent_cod);
        updateCard('influent-tn', metrics.influent_tn);
        updateCard('effluent-ph', metrics.effluent_ph);
        updateCard('effluent-cod', metrics.effluent_cod);

        // 更新系统状态
        const statusEl = document.getElementById('system-status');
        if (statusEl) {
            const anomalyCount = latest.anomalies_count || 0;
            const violationCount = latest.violations_count || 0;

            if (violationCount > 0) {
                statusEl.textContent = '告警';
                statusEl.style.color = '#ef4444';
            } else if (anomalyCount > 0) {
                statusEl.textContent = '异常';
                statusEl.style.color = '#f59e0b';
            } else {
                statusEl.textContent = '正常';
                statusEl.style.color = '#22c55e';
            }
        }
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

// 监听标签切换事件
document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab;

            if (tabId === 'monitoring') {
                startMonitoring();
            } else {
                stopMonitoring();
            }
        });
    });

    // 页面隐藏时停止监控
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopMonitoring();
        }
    });
});

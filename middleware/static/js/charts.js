// 图表实例存储
const chartInstances = {};

// ========== 相关性散点图 ==========
function createCorrelationChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    // 销毁旧图表
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 准备数据 - 从分析结果中提取相关性信息
    const indicators = data.indicators || ['X', 'Y'];
    const correlationValue = data.correlation_value !== undefined ? data.correlation_value :
                           (data.pearson !== undefined ? data.pearson : 'N/A');

    // 生成示例数据点（如果实际数据不存在）
    const scatterData = data.data_points || generateScatterData(30);

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: `${indicators[0] || 'X'} vs ${indicators[1] || 'Y'}`,
                data: scatterData,
                backgroundColor: 'rgba(37, 99, 235, 0.6)',
                borderColor: 'rgba(37, 99, 235, 1)',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `相关性分析 (r = ${typeof correlationValue === 'number' ? correlationValue.toFixed(3) : correlationValue})`,
                    font: { size: 14 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            return `(${point.x.toFixed(2)}, ${point.y.toFixed(2)})`;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: indicators[0] || 'X轴',
                        font: { size: 12 }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: indicators[1] || 'Y轴',
                        font: { size: 12 }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

// ========== 异常检测图表 ==========
function createAnomalyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 准备异常数据
    let anomalies = [];
    let labels = [];

    if (data.anomalies && Array.isArray(data.anomalies)) {
        anomalies = data.anomalies;
        labels = anomalies.map((a, i) => a.time || a.timestamp || `T${i + 1}`);
    } else if (data.details && Array.isArray(data.details)) {
        anomalies = data.details;
        labels = anomalies.map((a, i) => a.time || `T${i + 1}`);
    } else if (data.total_anomalies !== undefined) {
        // 如果只有总数，创建一个简单的柱状图
        labels = ['异常总数'];
        anomalies = [{ score: 1, count: data.total_anomalies }];
    }

    const scores = anomalies.map(a => a.score || a.confidence || (a.severity === 'high' ? 0.9 : 0.5));

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '异常分数',
                data: scores,
                backgroundColor: scores.map(s =>
                    s > 0.8 ? 'rgba(239, 68, 68, 0.7)' :
                    s > 0.5 ? 'rgba(245, 158, 11, 0.7)' :
                    'rgba(34, 197, 94, 0.7)'
                ),
                borderColor: scores.map(s =>
                    s > 0.8 ? 'rgba(239, 68, 68, 1)' :
                    s > 0.5 ? 'rgba(245, 158, 11, 1)' :
                    'rgba(34, 197, 94, 1)'
                ),
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `异常检测结果 (共 ${anomalies.length} 个异常点)`,
                    font: { size: 14 }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const score = context.raw;
                            let level = score > 0.8 ? '高' : score > 0.5 ? '中' : '低';
                            return `异常分数: ${score.toFixed(2)} (${level})`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 1,
                    title: {
                        display: true,
                        text: '异常分数',
                        font: { size: 12 }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

// ========== 时序趋势图 ==========
function createTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 准备时序数据
    const labels = data.timestamps || data.times || [];
    const datasets = [];

    // 处理单系列数据
    if (data.values && Array.isArray(data.values)) {
        datasets.push({
            label: data.name || data.indicator || '数据',
            data: data.values,
            borderColor: 'rgba(37, 99, 235, 1)',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 3
        });
    }
    // 处理多系列数据
    else if (data.series && Array.isArray(data.series)) {
        data.series.forEach((series, index) => {
            datasets.push({
                label: series.name || series.indicator || `系列 ${index + 1}`,
                data: series.values || [],
                borderColor: getColor(index),
                backgroundColor: getColor(index, 0.1),
                tension: 0.4,
                fill: false,
                pointRadius: 3
            });
        });
    }

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: data.title || '时序趋势图',
                    font: { size: 14 }
                },
                legend: {
                    display: datasets.length > 1,
                    position: 'top'
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
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: data.unit || '数值',
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

// ========== 工具函数 ==========

function getColor(index, alpha = 1) {
    const colors = [
        `rgba(37, 99, 235, ${alpha})`,   // blue
        `rgba(34, 197, 94, ${alpha})`,   // green
        `rgba(245, 158, 11, ${alpha})`,  // amber
        `rgba(239, 68, 68, ${alpha})`,   // red
        `rgba(168, 85, 247, ${alpha})`,  // purple
        `rgba(236, 72, 153, ${alpha})`,  // pink
        `rgba(14, 165, 233, ${alpha})`,  // sky
        `rgba(132, 204, 22, ${alpha})`   // lime
    ];
    return colors[index % colors.length];
}

function generateScatterData(count) {
    // 生成具有正相关性的示例数据
    const data = [];
    for (let i = 0; i < count; i++) {
        const x = Math.random() * 100;
        const y = x * 0.8 + Math.random() * 20; // 正相关，带有一些噪声
        data.push({ x, y });
    }
    return data;
}

// ========== 清理图表 ==========
function destroyChart(canvasId) {
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }
}

function destroyAllCharts() {
    Object.keys(chartInstances).forEach(id => {
        destroyChart(id);
    });
}

// ========== 导出 ==========
window.chartUtils = {
    destroyChart,
    destroyAllCharts,
    createCorrelationChart,
    createAnomalyChart,
    createTrendChart
};

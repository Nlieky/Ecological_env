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

// ========== 时序图表（带异常点标注） ==========
function createTimeseriesChartWithAnomalies(canvasId, timeseriesData, anomalyDetails, options = {}) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 合并进水和出水数据
    const allData = [
        ...(timeseriesData.influent || []).map(d => ({...d, source: '进水'})),
        ...(timeseriesData.effluent || []).map(d => ({...d, source: '出水'}))
    ];

    // 按时间排序
    allData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // 提取时间标签
    const labels = allData.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    // 获取指标列表
    const indicators = options.indicators || ['pH', 'COD', 'TN', 'NH3-N', 'TP'];
    const baseColor = options.baseColor || 'rgba(37, 99, 235, 1)';
    const baseFillColor = options.baseFillColor || 'rgba(37, 99, 235, 0.1)';

    // 创建异常点索引映射（用于快速查找）
    const anomalyMap = new Map();
    if (anomalyDetails && Array.isArray(anomalyDetails)) {
        anomalyDetails.forEach(anomaly => {
            const anomalyTime = new Date(anomaly.times).getTime();
            const dataIndex = allData.findIndex(d => new Date(d.timestamp).getTime() === anomalyTime);
            if (dataIndex >= 0) {
                anomalyMap.set(dataIndex, anomaly);
            }
        });
    }

    // 准备数据集 - 主时序线
    const datasets = [];

    // 为每个指标创建一条线
    indicators.forEach((indicator, idx) => {
        // 从带前缀的字段中提取值（influent_pH, effluent_pH）
        const values = allData.map(d => {
            const influentKey = `influent_${indicator}`;
            const effluentKey = `effluent_${indicator}`;

            if (d[influentKey] !== null && d[influentKey] !== undefined) {
                return d[influentKey];
            } else if (d[effluentKey] !== null && d[effluentKey] !== undefined) {
                return d[effluentKey];
            } else if (d[indicator] !== null && d[indicator] !== undefined) {
                return d[indicator];
            }
            return null;
        });

        // 主数据集（连续线）
        datasets.push({
            label: indicator,
            data: values,
            borderColor: getColor(idx, 1),
            backgroundColor: getColor(idx, 0.1),
            tension: 0.3,
            fill: false,
            pointRadius: allData.map((_, i) => anomalyMap.has(i) ? 8 : 2),
            pointBackgroundColor: allData.map((_, i) => {
                if (anomalyMap.has(i)) {
                    const anomaly = anomalyMap.get(i);
                    return getSeverityColor(anomaly.severity);
                }
                return getColor(idx, 1);
            }),
            pointBorderColor: allData.map((_, i) => {
                if (anomalyMap.has(i)) {
                    return '#ffffff';
                }
                return getColor(idx, 1);
            }),
            pointBorderWidth: allData.map((_, i) => anomalyMap.has(i) ? 2 : 0),
            pointStyle: allData.map((_, i) => {
                if (anomalyMap.has(i)) {
                    const anomaly = anomalyMap.get(i);
                    return getSeverityPointStyle(anomaly.severity);
                }
                return 'circle';
            }),
            yAxisID: `y-${idx}`
        });

        // 异常点数据集（用于tooltip显示详细信息）
        if (anomalyDetails && anomalyDetails.length > 0) {
            const anomalyValues = allData.map((d, i) => {
                if (anomalyMap.has(i)) {
                    const anomaly = anomalyMap.get(i);
                    // 从带前缀的字段中提取值
                    const influentKey = `influent_${indicator}`;
                    const effluentKey = `effluent_${indicator}`;

                    if (d[influentKey] !== null && d[influentKey] !== undefined) {
                        return d[influentKey];
                    } else if (d[effluentKey] !== null && d[effluentKey] !== undefined) {
                        return d[effluentKey];
                    }
                    return d[indicator] || null;
                }
                return null;
            });

            datasets.push({
                label: `${indicator} 异常点`,
                data: anomalyValues,
                backgroundColor: anomalyDetails.map(a => getSeverityColor(a.severity, 0.7)),
                pointRadius: 10,
                pointHoverRadius: 14,
                pointStyle: 'rectRot',
                type: 'scatter',
                yAxisID: `y-${idx}`,
                hidden: false,
                tooltipCallbacks: {
                    label: function(context) {
                        const idx = context.dataIndex;
                        if (anomalyMap.has(idx)) {
                            const anomaly = anomalyMap.get(idx);
                            const severity = getSeverityLabel(anomaly.severity);
                            return [
                                `异常指标: ${anomaly.indicator}`,
                                `异常分数: ${(anomaly.score * 100).toFixed(1)}%`,
                                `异常模式: ${getPatternLabel(anomaly.pattern)}`,
                                `严重程度: ${severity}`
                            ];
                        }
                        return '';
                    }
                }
            });
        }
    });

    // 创建Y轴配置
    const scales = {
        x: {
            title: {
                display: true,
                text: '时间',
                font: { size: 12 }
            },
            grid: {
                color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
                maxTicksLimit: 20
            }
        }
    };

    // 为每个指标添加独立的Y轴
    indicators.forEach((indicator, idx) => {
        scales[`y-${idx}`] = {
            type: 'linear',
            display: idx === 0, // 只显示第一个Y轴标签
            position: idx === 0 ? 'left' : 'right',
            title: {
                display: idx === 0,
                text: '数值',
                font: { size: 12 }
            },
            grid: {
                color: 'rgba(0, 0, 0, 0.05)',
                drawOnChartArea: idx === 0 // 只为第一个Y轴绘制网格
            }
        };
    });

    // 创建图表
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: options.title || '时序数据与异常点标注',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        filter: function(legendItem, chartData) {
                            // 隐藏异常点图例项
                            return !legendItem.text.includes('异常点');
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const dataset = context.dataset;
                            const idx = context.dataIndex;

                            // 检查是否有自定义tooltip回调
                            if (dataset.tooltipCallbacks && dataset.tooltipCallbacks.label) {
                                return dataset.tooltipCallbacks.label(context);
                            }

                            // 默认tooltip
                            if (context.parsed.y !== null) {
                                const value = context.parsed.y;
                                if (dataset.label.includes('异常点')) {
                                    // 对于异常点，显示特殊信息
                                    if (anomalyMap.has(idx)) {
                                        const anomaly = anomalyMap.get(idx);
                                        const severity = getSeverityLabel(anomaly.severity);
                                        return [
                                            `🚨 ${dataset.label.replace(' 异常点', '')}: ${value.toFixed(2)}`,
                                            `   严重程度: ${severity}`,
                                            `   异常分数: ${(anomaly.score * 100).toFixed(1)}%`,
                                            `   异常模式: ${getPatternLabel(anomaly.pattern)}`
                                        ];
                                    }
                                }
                                return `${dataset.label}: ${value.toFixed(2)}`;
                            }
                            return '';
                        },
                        afterBody: function(context) {
                            // 在tooltip底部显示额外信息
                            const idx = context[0]?.dataIndex;
                            if (idx !== undefined && allData[idx]) {
                                const dataPoint = allData[idx];
                                return `\n数据来源: ${dataPoint.source || 'N/A'}`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: scales
        }
    });

    console.log(`[CHARTS] 创建时序图表: ${canvasId}, ${labels.length} 个数据点, ${anomalyMap.size} 个异常点`);
}

// ========== 异常点严重程度颜色 ==========
function getSeverityColor(severity, alpha = 1) {
    const colors = {
        'high': `rgba(239, 68, 68, ${alpha})`,      // 红色
        'critical': `rgba(220, 38, 38, ${alpha})`,   // 深红色
        'medium': `rgba(245, 158, 11, ${alpha})`,    // 橙色
        'low': `rgba(34, 197, 94, ${alpha})`,        // 绿色
        'unknown': `rgba(107, 114, 128, ${alpha})`   // 灰色
    };
    return colors[severity] || colors['unknown'];
}

function getSeverityPointStyle(severity) {
    const styles = {
        'high': 'triangle',
        'critical': 'star',
        'medium': 'rect',
        'low': 'circle',
        'unknown': 'circle'
    };
    return styles[severity] || styles['unknown'];
}

function getSeverityLabel(severity) {
    const labels = {
        'high': '高',
        'critical': '严重',
        'medium': '中',
        'low': '低',
        'unknown': '未知'
    };
    return labels[severity] || labels['unknown'];
}

function getPatternLabel(pattern) {
    // 模式标签与后端 pattern_recognizer.py 保持一致
    const labels = {
        'constant': '恒定异常',
        'spike': '突变异常',
        'trend': '趋势异常',
        'periodic': '周期异常',
        'high_freq_volatility': '高频波动异常',
        'unknown': '未知模式'
    };
    return labels[pattern] || labels['unknown'];
}

// ========== 单数据源时序图表（进水或出水） ==========
function createSingleSourceChart(canvasId, timeseriesData, anomalyDetails, options = {}) {
    console.log(`[CHARTS] 创建${options.source || 'unknown'}图表开始`);
    console.log(`[CHARTS] 数据长度: ${timeseriesData?.length || 0}`);
    console.log(`[CHARTS] 异常点数量: ${anomalyDetails?.length || 0}`);

    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 过滤和排序数据
    const data = timeseriesData || [];
    const sortedData = data
        .filter(d => d.timestamp)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    if (sortedData.length === 0) {
        console.log(`[CHARTS] 没有有效数据`);
        return;
    }

    // 提取时间标签
    const labels = sortedData.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    // 提取指标名称（不带前缀）
    const sample = sortedData[0];
    const indicators = [];
    Object.keys(sample).forEach(key => {
        if (key !== 'timestamp' && key !== 'source' && key !== '监测时间') {
            indicators.push(key);
        }
    });

    console.log(`[CHARTS] 提取的指标: ${indicators}`);

    // 指标名称和颜色配置
    const indicatorNames = {
        'pH': 'pH值',
        'COD': '化学需氧量',
        'TN': '总氮',
        'NH3-N': '氨氮',
        'TP': '总磷'
    };

    const indicatorColors = {
        'pH': { border: 'rgba(34, 197, 94, 1)', bg: 'rgba(34, 197, 94, 0.05)' },
        'COD': { border: 'rgba(59, 130, 246, 1)', bg: 'rgba(59, 130, 246, 0.05)' },
        'TN': { border: 'rgba(168, 85, 247, 1)', bg: 'rgba(168, 85, 247, 0.05)' },
        'NH3-N': { border: 'rgba(249, 115, 22, 1)', bg: 'rgba(249, 115, 22, 0.05)' },
        'TP': { border: 'rgba(236, 72, 153, 1)', bg: 'rgba(236, 72, 153, 0.05)' }
    };

    // 创建异常点映射（支持进水和出水数据）
    const anomalyMapByIndicator = new Map();
    if (anomalyDetails && Array.isArray(anomalyDetails)) {
        console.log(`[CHARTS] 开始处理异常点（${options.source}图表）`);

        anomalyDetails.forEach((anomaly, idx) => {
            // 提取基础指标名
            let indicator = anomaly.indicator;
            if (typeof indicator === 'string') {
                while (indicator.startsWith('influent_') || indicator.startsWith('effluent_')) {
                    indicator = indicator.replace(/^(influent|effluent)_/, '');
                }
            }

            if (!anomalyMapByIndicator.has(indicator)) {
                anomalyMapByIndicator.set(indicator, new Map());
            }

            // 优先使用 index 字段
            let dataIndex = -1;
            if (anomaly.index !== undefined && anomaly.index !== null && anomaly.index >= 0) {
                dataIndex = anomaly.index;
            } else {
                // 回退到时间戳匹配
                const anomalyTime = new Date(anomaly.times).getTime();
                dataIndex = sortedData.findIndex(d => new Date(d.timestamp).getTime() === anomalyTime);
            }

            console.log(`[CHARTS] 异常${idx + 1}: indicator="${indicator}", index=${dataIndex}`);

            if (dataIndex >= 0) {
                anomalyMapByIndicator.get(indicator).set(dataIndex, anomaly);
            }
        });
    }

    // 构建数据集
    const datasets = [];

    indicators.forEach(indicator => {
        const color = indicatorColors[indicator] || { border: 'rgba(100, 100, 100, 1)', bg: 'rgba(100, 100, 100, 0.05)' };
        const values = sortedData.map(d => d[indicator]);

        // 检查是否有数据
        const hasData = values.some(v => v !== null && v !== undefined && v !== '');
        if (!hasData) {
            console.log(`[CHARTS] 跳过指标 ${indicator}: 无有效数据`);
            return;
        }

        // 主数据集
        datasets.push({
            label: indicatorNames[indicator] || indicator,
            data: values,
            borderColor: color.border,
            backgroundColor: color.bg,
            borderWidth: 2,
            tension: 0.3,
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHitRadius: 10
        });

        // 如果有异常点，添加异常点数据集
        const anomalyMap = anomalyMapByIndicator.get(indicator);
        if (anomalyMap && anomalyMap.size > 0) {
            datasets.push({
                label: `${indicatorNames[indicator] || indicator} 异常点`,
                data: values.map((v, i) => anomalyMap.has(i) ? v : null),
                backgroundColor: 'rgba(239, 68, 68, 0.9)',
                borderColor: '#ffffff',
                borderWidth: 2,
                pointRadius: 8,
                pointHoverRadius: 12,
                pointStyle: 'circle',
                type: 'scatter',
                showLine: false
            });
            console.log(`[CHARTS] 为指标 ${indicator} 添加异常点: ${anomalyMap.size} 个`);
        }
    });

    console.log(`[CHARTS] 图表创建完成，共 ${datasets.length} 个数据集`);

    // 创建图表
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: options.title || '时序数据',
                    font: { size: 16, weight: 'bold' },
                    padding: { top: 10, bottom: 15 },
                    color: '#1e293b'
                },
                legend: {
                    display: true,
                    position: 'top',
                    align: 'center',
                    labels: {
                        usePointStyle: true,
                        padding: 12,
                        font: { size: 12 },
                        color: '#475569'
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '时间',
                        font: { size: 12 },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        maxTicksLimit: 12,
                        font: { size: 11 },
                        color: '#64748b'
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: '数值',
                        font: { size: 12 },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });

    console.log(`[CHARTS] ${options.source || 'unknown'}图表创建完成`);
}

// ========== 多指标时序图表（带异常点标注） ==========
function createMultiIndicatorChart(canvasId, timeseriesData, anomalyDetails, options = {}) {
    console.log('[CHARTS] 创建图表开始');
    console.log('[CHARTS] timeseriesData.influent 长度:', (timeseriesData.influent || []).length);
    console.log('[CHARTS] timeseriesData.effluent 长度:', (timeseriesData.effluent || []).length);
    console.log('[CHARTS] anomalyDetails 长度:', (anomalyDetails || []).length);

    if (timeseriesData.influent && timeseriesData.influent.length > 0) {
        console.log('[CHARTS] influent 样本数据:', timeseriesData.influent[0]);
        console.log('[CHARTS] influent 字段:', Object.keys(timeseriesData.influent[0]));
    }

    if (timeseriesData.effluent && timeseriesData.effluent.length > 0) {
        console.log('[CHARTS] effluent 样本数据:', timeseriesData.effluent[0]);
        console.log('[CHARTS] effluent 字段:', Object.keys(timeseriesData.effluent[0]));
    }

    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // 分别处理进水和出水数据（不合并）
    const influentData = (timeseriesData.influent || []).map(d => ({...d, source: 'influent'}));
    const effluentData = (timeseriesData.effluent || []).map(d => ({...d, source: 'effluent'}));

    // 按时间排序
    influentData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    effluentData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // 过滤掉没有时间戳的数据
    const validInfluent = influentData.filter(d => d.timestamp);
    const validEffluent = effluentData.filter(d => d.timestamp);

    // 提取所有带前缀的指标（influent_pH, effluent_pH, influent_COD, effluent_COD, 等）
    const prefixedIndicators = new Set();

    validInfluent.forEach(d => {
        Object.keys(d).forEach(key => {
            if (key !== 'timestamp' && key !== 'source' && key !== '监测时间' && d[key] !== null && d[key] !== undefined) {
                prefixedIndicators.add(key);
            }
        });
    });

    validEffluent.forEach(d => {
        Object.keys(d).forEach(key => {
            if (key !== 'timestamp' && key !== 'source' && key !== '监测时间' && d[key] !== null && d[key] !== undefined) {
                prefixedIndicators.add(key);
            }
        });
    });

    console.log('[CHARTS] 提取的带前缀指标列表:', Array.from(prefixedIndicators));

    // 获取所有时间标签（合并两个数据源的时间）
    const allTimestamps = new Set([
        ...validInfluent.map(d => d.timestamp),
        ...validEffluent.map(d => d.timestamp)
    ]);
    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => new Date(a) - new Date(b));

    const labels = sortedTimestamps.map(ts => {
        const date = new Date(ts);
        return date.toLocaleTimeString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    // 指标名称映射
    const getIndicatorName = (prefixedIndicator) => {
        // 提取基础指标名（如 influent_pH -> pH）
        const parts = prefixedIndicator.split('_');
        const baseIndicator = parts[parts.length - 1];
        const source = parts.slice(0, -1).join('_'); // influent 或 effluent

        const names = {
            'pH': 'pH值',
            'COD': '化学需氧量',
            'TN': '总氮',
            'NH3-N': '氨氮',
            'TP': '总磷'
        };

        const sourceName = source === 'influent' ? '进水' : '出水';
        return `${sourceName}${names[baseIndicator] || baseIndicator}`;
    };

    // 指标颜色映射
    const getIndicatorColor = (prefixedIndicator) => {
        const parts = prefixedIndicator.split('_');
        const baseIndicator = parts[parts.length - 1];
        const source = parts[0]; // influent 或 effluent

        const colors = {
            'pH': 'rgba(34, 197, 94, 1)',
            'COD': 'rgba(59, 130, 246, 1)',
            'TN': 'rgba(168, 85, 247, 1)',
            'NH3-N': 'rgba(249, 115, 22, 1)',
            'TP': 'rgba(236, 72, 153, 1)'
        };

        const baseColor = colors[baseIndicator] || 'rgba(100, 100, 100, 1)';

        // 进水使用实线，出水使用虚线
        if (source === 'effluent') {
            return {
                border: baseColor.replace('1)', '0.7)'), // 稍浅的颜色
                bg: baseColor.replace('1)', '0.05)'),
                borderDash: [5, 5] // 虚线
            };
        }
        return {
            border: baseColor,
            bg: baseColor.replace('1)', '0.05)'),
            borderDash: undefined // 实线
        };
    };

    // 创建异常点映射（按带前缀的指标分组）
    const anomalyMapByIndicator = new Map();
    console.log('[CHARTS] 开始处理异常点，总数:', anomalyDetails?.length || 0);

    if (anomalyDetails && Array.isArray(anomalyDetails)) {
        console.log('[CHARTS] anomalyDetails 示例:', anomalyDetails[0]);
        anomalyDetails.forEach((anomaly, idx) => {
            let indicator = anomaly.indicator;
            if (typeof indicator === 'string') {
                // 移除所有前缀 (可能有多层前缀，如 effluent_effluent_pH -> pH)
                while (indicator.startsWith('influent_') || indicator.startsWith('effluent_')) {
                    indicator = indicator.replace(/^(influent|effluent)_/, '');
                }
            }

            if (!anomalyMapByIndicator.has(indicator)) {
                anomalyMapByIndicator.set(indicator, new Map());
            }

            // 优先使用 index 字段进行匹配
            let dataIndex = -1;
            if (anomaly.index !== undefined && anomaly.index !== null && anomaly.index >= 0) {
                dataIndex = anomaly.index;
                console.log(`[CHARTS] 异常${idx + 1}: 使用 index 字段匹配: ${dataIndex}`);
            } else {
                // 回退到时间戳匹配
                const anomalyTime = new Date(anomaly.times).getTime();
                // 在合并的时间轴中查找
                dataIndex = sortedTimestamps.findIndex(ts => new Date(ts).getTime() === anomalyTime);
                console.log(`[CHARTS] 异常${idx + 1}: 使用时间戳匹配, times=${anomaly.times}, dataIndex=${dataIndex}`);
            }

            console.log(`[CHARTS] 异常${idx + 1}: indicator="${anomaly.indicator}" -> "${indicator}", times=${anomaly.times}, dataIndex=${dataIndex}`);

            if (dataIndex >= 0) {
                anomalyMapByIndicator.get(indicator).set(dataIndex, anomaly);
            }
        });

        // 打印匹配结果
        console.log('[CHARTS] 异常点匹配结果:');
        anomalyMapByIndicator.forEach((map, indicator) => {
            console.log(`  ${indicator}: ${map.size} 个异常点`);
        });
    }

    // 统计异常点数量
    let totalAnomalies = 0;
    anomalyMapByIndicator.forEach(map => totalAnomalies += map.size);
    console.log(`[CHARTS] 综合图表: ${sortedTimestamps.length} 个数据点, ${totalAnomalies} 个异常点`);

    // 构建数据集
    const datasets = [];

    // 为每个带前缀的指标创建一条线
    prefixedIndicators.forEach(prefixedIndicator => {
        const source = prefixedIndicator.startsWith('influent_') ? 'influent' : 'effluent';
        const data = source === 'influent' ? validInfluent : validEffluent;
        const color = getIndicatorColor(prefixedIndicator);

        // 提取值数组（按照合并后的时间轴）
        const values = sortedTimestamps.map(ts => {
            const dataPoint = data.find(d => d.timestamp === ts);
            return dataPoint ? dataPoint[prefixedIndicator] : null;
        });

        // 检查是否有数据
        const hasData = values.some(v => v !== null && v !== undefined && v !== '');
        if (!hasData) {
            console.log(`[CHARTS] 跳过指标 ${prefixedIndicator}: 无有效数据`);
            return;
        }

        // 提取基础指标名（用于匹配异常点）
        const parts = prefixedIndicator.split('_');
        const baseIndicator = parts[parts.length - 1];

        // 获取该指标的异常点映射
        const anomalyMap = anomalyMapByIndicator.get(baseIndicator) || new Map();

        // 主数据集
        const dataset = {
            label: getIndicatorName(prefixedIndicator),
            data: values,
            borderColor: color.border,
            backgroundColor: color.bg,
            borderWidth: 2,
            tension: 0.3,
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHitRadius: 10
        };

        // 只有当borderDash有值时才添加该属性
        if (color.borderDash) {
            dataset.borderDash = color.borderDash;
            console.log(`[CHARTS] ${prefixedIndicator} 使用虚线: ${color.borderDash}`);
        } else {
            console.log(`[CHARTS] ${prefixedIndicator} 使用实线`);
        }

        datasets.push(dataset);

        // 如果有异常点，添加异常点数据集
        if (anomalyMap.size > 0) {
            datasets.push({
                label: `${getIndicatorName(prefixedIndicator)} 异常点`,
                data: values.map((v, i) => anomalyMap.has(i) ? v : null),
                backgroundColor: 'rgba(239, 68, 68, 0.9)',
                borderColor: '#ffffff',
                borderWidth: 2,
                pointRadius: 8,
                pointHoverRadius: 12,
                pointStyle: 'circle',
                type: 'scatter',
                showLine: false
            });
        }
    });

    console.log(`[CHARTS] 综合图表创建完成，共 ${datasets.length} 个数据集`);

    // 创建图表
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: options.title || '时序数据与异常点标注',
                    font: { size: 18, weight: 'bold' },
                    padding: { top: 10, bottom: 20 },
                    color: '#1e293b'
                },
                legend: {
                    display: true,
                    position: 'top',
                    align: 'center',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 12 },
                        color: '#475569',
                        boxWidth: 10,
                        boxHeight: 10,
                        // 默认情况下，点击图例可以切换显示/隐藏
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const value = context.parsed.y;

                            // 如果是异常点数据集
                            if (context.dataset.label.includes('异常点')) {
                                const indicatorName = context.dataset.label.replace(' 异常点', '');
                                return `🔴 ${indicatorName} 异常: ${value.toFixed(2)}`;
                            }

                            // 普通数据点
                            return `${context.dataset.label}: ${value !== null ? value.toFixed(2) : 'N/A'}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间',
                        font: { size: 13, weight: '500' },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 12,
                        font: { size: 11 },
                        color: '#64748b',
                        maxRotation: 0,
                        minRotation: 0
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: '数值',
                        font: { size: 13, weight: '500' },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#64748b'
                    }
                }
            }
        }
    });
}

// ========== 单指标时序图表（带异常点标注） ==========
function createSingleIndicatorChart(canvasId, timeseriesData, anomalyDetails, options = {}) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx) {
        console.error(`[CHARTS] 找不到图表容器: ${canvasId}`);
        return;
    }

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    const indicator = options.indicator || 'pH';
    const indicatorName = options.indicatorName || indicator;

    // 合并进水和出水数据
    const allData = [
        ...(timeseriesData.influent || []).map(d => {
            // 尝试从带前缀的字段中提取值
            const influentKey = `influent_${indicator}`;
            const value = d[influentKey] !== null && d[influentKey] !== undefined ? d[influentKey] : d[indicator];
            return {...d, source: '进水', value: value};
        }),
        ...(timeseriesData.effluent || []).map(d => {
            // 尝试从带前缀的字段中提取值
            const effluentKey = `effluent_${indicator}`;
            const value = d[effluentKey] !== null && d[effluentKey] !== undefined ? d[effluentKey] : d[indicator];
            return {...d, source: '出水', value: value};
        })
    ];

    // 按时间排序
    allData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // 过滤掉没有该指标值的数据点
    const validData = allData.filter(d => d.value !== null && d.value !== undefined && d.value !== '');

    // 提取时间标签
    const labels = validData.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    // 提取数值
    const values = validData.map(d => d.value);

    // 创建异常点映射
    const anomalyMap = new Map();
    const anomalyPoints = [];

    if (anomalyDetails && Array.isArray(anomalyDetails)) {
        anomalyDetails.forEach(anomaly => {
            if (anomaly.indicator === indicator) {
                const anomalyTime = new Date(anomaly.times).getTime();
                const dataIndex = validData.findIndex(d => new Date(d.timestamp).getTime() === anomalyTime);
                if (dataIndex >= 0) {
                    anomalyMap.set(dataIndex, anomaly);
                    anomalyPoints.push({
                        index: dataIndex,
                        value: validData[dataIndex].value,
                        anomaly: anomaly
                    });
                }
            }
        });
    }

    console.log(`[CHARTS] ${indicatorName}: ${validData.length} 个数据点, ${anomalyPoints.length} 个异常点`);

    // 为每个指标定义颜色
    const indicatorColors = {
        'pH': { border: 'rgba(34, 197, 94, 1)', bg: 'rgba(34, 197, 94, 0.05)' },      // 绿色
        'COD': { border: 'rgba(59, 130, 246, 1)', bg: 'rgba(59, 130, 246, 0.05)' },   // 蓝色
        'TN': { border: 'rgba(168, 85, 247, 1)', bg: 'rgba(168, 85, 247, 0.05)' },     // 紫色
        'NH3-N': { border: 'rgba(249, 115, 22, 1)', bg: 'rgba(249, 115, 22, 0.05)' }, // 橙色
        'TP': { border: 'rgba(236, 72, 153, 1)', bg: 'rgba(236, 72, 153, 0.05)' }     // 粉色
    };

    const color = indicatorColors[indicator] || { border: 'rgba(37, 99, 235, 1)', bg: 'rgba(37, 99, 235, 0.05)' };

    // 构建异常点数组
    const anomalyPointValues = [];
    const anomalyPointIndices = [];

    values.forEach((v, i) => {
        if (anomalyMap.has(i)) {
            anomalyPointValues.push(v);
            anomalyPointIndices.push(i);
        }
    });

    // 构建数据集 - 主时序线（不带普通数据点）
    const datasets = [{
        label: indicatorName,
        data: values,
        borderColor: color.border,
        backgroundColor: color.bg,
        borderWidth: 2.5,
        tension: 0.3,
        fill: true,
        pointRadius: 0,           // 移除普通数据点
        pointHoverRadius: 6,      // 悬停时显示点
        pointHitRadius: 20        // 增加点击检测范围
    }];

    // 如果有异常点，添加异常点数据集
    if (anomalyPointValues.length > 0) {
        datasets.push({
            label: '异常点',
            data: values.map((v, i) => anomalyMap.has(i) ? v : null),
            backgroundColor: 'rgba(239, 68, 68, 0.9)',    // 红色
            borderColor: '#ffffff',
            borderWidth: 2,
            pointRadius: 10,
            pointHoverRadius: 14,
            pointStyle: 'circle',
            type: 'scatter',
            showLine: false
        });
    }

    // 创建图表
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: options.title || `${indicatorName} 时序数据`,
                    font: { size: 18, weight: 'bold' },
                    padding: { top: 10, bottom: 20 }
                },
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 12 },
                        color: '#475569',
                        boxWidth: 8,
                        boxHeight: 8,
                        filter: function(legendItem, chartData) {
                            // 隐藏异常点图例项
                            return !legendItem.text.includes('异常点');
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const value = context.parsed.y;

                            if (anomalyMap.has(idx) && context.dataset.label === '异常点') {
                                const anomaly = anomalyMap.get(idx);
                                return [
                                    `🔴 异常: ${value.toFixed(2)}`,
                                    `   ${getPatternLabel(anomaly.pattern)} | 严重度: ${getSeverityLabel(anomaly.severity)}`
                                ];
                            }

                            if (context.dataset.label !== '异常点') {
                                return `${indicatorName}: ${value.toFixed(2)}`;
                            }
                            return null;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间',
                        font: { size: 13, weight: '500' },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 12,
                        font: { size: 11 },
                        color: '#64748b',
                        maxRotation: 0,
                        minRotation: 0
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: '数值',
                        font: { size: 13, weight: '500' },
                        color: '#64748b'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#64748b'
                    }
                }
            }
        }
    });

    console.log(`[CHARTS] ${indicatorName} 图表创建完成`);
}

// ========== 时序图表（带异常点标注）[已弃用，使用createSingleIndicatorChart] ==========
function createTimeseriesChartWithAnomalies(canvasId, timeseriesData, anomalyDetails, options = {}) {
    // 此函数已弃用，请使用 createSingleIndicatorChart 代替
    console.warn('[CHARTS] createTimeseriesChartWithAnomalies 已弃用，请使用 createSingleIndicatorChart');
}

// ========== 工具函数 ==========

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
    createTrendChart,
    createMultiIndicatorChart,
    createSingleIndicatorChart,
    createTimeseriesChartWithAnomalies
};

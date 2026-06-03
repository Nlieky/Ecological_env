# 废水监测监控系统 - 使用现有Grafana仪表板

## 现有仪表板
- [stream_01.json](dashboards/stream_01.json) - 已配置好的双数据流监控仪表板

## Prometheus指标列表

### 进水指标 (7个)
| 指标 | 说明 |
|------|------|
| `wastewater_influent_ph` | 进水pH值 |
| `wastewater_influent_cod` | 进水化学需氧量(mg/L) |
| `wastewater_influent_tn` | 进水总氮(mg/L) |
| `wastewater_influent_an` | 进水氨氮(mg/L) |
| `wastewater_influent_tp` | 进水总磷(mg/L) |
| `wastewater_influent_flow_rate` | 进水流量(升/秒) |
| `wastewater_influent_discharge_volume` | 进水排放量(吨) |

### 出水指标 (8个)
| 指标 | 说明 |
|------|------|
| `wastewater_effluent_ph` | 出水pH值 |
| `wastewater_effluent_cod` | 出水化学需氧量(mg/L) |
| `wastewater_effluent_tn` | 出水总氮(mg/L) |
| `wastewater_effluent_an` | 出水氨氮(mg/L) |
| `wastewater_effluent_tp` | 出水总磷(mg/L) |
| `wastewater_effluent_flow_rate` | 出水流量(升/秒) |
| `wastewater_effluent_discharge_volume` | 出水排放量(吨) |
| `wastewater_effluent_suspended_solids` | 出水悬浮物(mg/L) |

### 计数器 (2个)
| 指标 | 说明 |
|------|------|
| `wastewater_data_processed_total` | 数据处理总数 |
| `wastewater_anomaly_detected_total` | 异常检测总数 |

## 启动流程

```bash
# 1. 启动Flask中间件
cd middleware
python app.py

# 2. 启动数据流发送器（新终端）
cd stream
python dual_data_stream.py

# 3. 配置Prometheus抓取
# prometheus.yml 添加:
# scrape_configs:
#   - job_name: 'wastewater'
#     static_configs:
#       - targets: ['localhost:5000']
#     scrape_interval: 10s
```

## Grafana导入

1. 访问 Grafana (默认 http://localhost:3000)
2. 左侧菜单 → Dashboards → Import
3. 上传 `grafana/dashboards/stream_01.json`
4. 选择 Prometheus 数据源

## 端点说明

| 端点 | 方法 | 说明 |
|------|------|------|
| /health | GET | 健康检查 |
| /metrics | GET | Prometheus指标 |
| /api/dual-stream | POST | 接收双数据流 |

## 数据滞后处理

- **滞后时间**: 2小时
- **滞后记录**: 24条（按5分钟间隔计算）
- **实现方式**: 脚本直接处理出水索引 `effluent_idx = max(0, i - LAG_RECORDS)`

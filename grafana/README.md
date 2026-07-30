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

> 注：旧的 `stream/dual_data_stream.py` + Flask 中间件(5000) 数据流已废弃，监测数据现由 InfluxDB 提供，Prometheus 直接抓 backend 的 `/metrics`。

```bash
# 1. 启动 backend(FastAPI 8000，暴露 /metrics 给 Prometheus)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2. Prometheus 已在 prometheus/prometheus.yml 配好抓 backend:8000(容器化时用服务名)
#    docker-compose 里 prometheus 服务会自动抓取

# 3. Grafana 导入下面的仪表板，数据源选 Prometheus
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
| /metrics | GET | Prometheus指标(backend:8000) |

## 数据滞后处理

- **滞后时间**: 2小时
- **滞后记录**: 24条（按5分钟间隔计算）
- **实现方式**: 脚本直接处理出水索引 `effluent_idx = max(0, i - LAG_RECORDS)`

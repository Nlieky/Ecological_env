# 报告可视化设计

> 2026-07-28 · brainstorm 产出 · 独立功能(跨数据感知+异常检测+后端+前端)

## 背景

当前智能体报告只有文字 + 表格。作为"有数据、做异常、做违规判别"的监控系统,报告应输出**数据曲线**——尤其异常查询,曲线上标出异常点,一目了然。

`QueryResponse` 已预留 `chartData` 字段(ECharts 配置),但 `query.py` 硬编码 `None` 没用。本设计把它打通:报告自动带时间趋势曲线(进水/出水双线)+ 异常 markPoint 标注。

## 设计原则

1. **主智能体(LLM)不生成图**:ECharts JSON 配置复杂、数据多,LLM 易错/幻觉。交给确定性代码
2. **确定性代码构造 chartData**:共享工具 `shared/viz/build_chart.py`
3. **后端自动触发**:本轮有数据结果就出图,不靠主智能体/用户明示
4. **不归一化**(符合监控理念):每个指标独立子图,量纲不混

## 图形态

- **时间趋势曲线**,每个指标一个子图(垂直排列)
- 每图:**进水/出水双线**(同指标,看 HRT 前后变化)
- 异常查询时:异常点 **markPoint + 悬停 tooltip**(类型/时间/值/得分)

## 数据流

```
数据感知 get_data.py → build_chart(records, anomalies=None) → data_result.chartData
异常检测 run_anomaly → build_chart(records, anomalies)      → anomaly_result.chartData
        ↓
后端 query.py → 收集本轮 chartData(异常检测的优先,带标注)→ QueryResponse.chartData
        ↓
前端 ChatMessage → ECharts 渲染(每指标一个子图,垂直排列)
```

## `build_chart` 接口(`shared/viz/build_chart.py`)

```python
def build_chart_data(records: dict, indicators: list = None, anomalies: list = None) -> list:
    """
    records:   {influent: [{timestamp,pH,COD,...}], effluent: [...]}   # 来自 data_result.result
    indicators: 画哪些指标(默认全部:pH/COD/TN/NH3-N/TP/SS)
    anomalies:  异常点列表(来自 anomaly_result.result.anomalies,可选)
    返回: [{"title":"pH 趋势","option":<ECharts option>}, {"title":"COD 趋势","option":...}]
    每个 option:xAxis(时间) + 进水 series + 出水 series + 异常 markPoint(按指标+时间匹配)
    """
```

## chartData 结构(`QueryResponse.chartData`)

```json
{
  "charts": [
    {"title":"pH 趋势","option":{"xAxis":{"data":[时间...]},"series":[{进水},{出水}]}},
    {"title":"COD 趋势","option":{...}}
  ]
}
```

## 改动清单

| 文件 | 改动 |
|---|---|
| **新建 `shared/viz/build_chart.py`** | `build_chart_data()` 实现(records+anomalies → ECharts option 列表) |
| **`get_data.py`** | 产出 data_result 后调 `build_chart_data(records, indicators, anomalies=None)`,存 `data_result.chartData` |
| **`run_anomaly_detection_simple.py`** | 产出 anomaly_result 后调 `build_chart_data(records, indicators, anomalies)`,存 `anomaly_result.chartData` |
| **`query.py`**(阻塞+流式) | 收集本轮 chartData(异常检测的优先)→ 塞进 `QueryResponse.chartData` |
| **`ChatMessage.vue`** | 消息含 `chartData.charts` 时,每个用 ECharts 渲染(垂直排列) |

## 异常标注细节

- **markPoint**:异常点按 `指标 + 时间` 匹配到对应 series,打标记(符号 + 小标签:类型 spike/trend)
- **tooltip**:悬停看详情(时间/指标/类型/值/得分/预期范围)
- **无异常**(纯数据查询):不加 markPoint,只画双线

## 决策记录

- **markPoint + tooltip**:异常检测输出本就是"点",自然映射;悬停看详情
- **每指标一个子图**:量纲不同(pH 0–14 vs COD 0–500)不混轴,各看各趋势
- **放 `shared/viz/`**:被 import 的共享库(不是 `scripts/` 那种可执行脚本)
- **后端自动触发**:有数据结果就出图,主智能体全程不碰图
- **主智能体不生成图**:LLM 不擅长 ECharts JSON 配置,交给确定性代码

## 测试

- `build_chart_data` 单元:输入 records + anomalies → 输出 ECharts option 列表(结构正确、异常 markPoint 正确匹配到指标+时间)
- 端到端:`smoke_test.py` 扩展(断言查询返回 chartData 非空)

## 范围

仅报告可视化(时间趋势曲线 + 异常标注)。其他形态(柱状/饼/仪表盘/对比图)后续按需加。

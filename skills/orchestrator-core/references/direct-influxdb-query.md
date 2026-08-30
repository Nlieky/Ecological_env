# 直接 InfluxDB 查询指南

## 适用场景

纯数据查询（用户要数字，不要研判）——如"7月14日COD是多少"、"金桥厂进水pH趋势"。

不走子智能体编排链路，直接用 `execute_code` 查 InfluxDB，响应快 (~3s vs ~30s+)。

**何时优先使用直接查询而非 call_subagent：**
- 用户只问"某指标数值"（如 COD/pH 是多少、均值、最大最小值）→ **直接用本指南**
- 用户问"有没有异常/违规/怎么处理" → 走 `call_subagent` 编排链路
- 多厂对比查询 → 直接查询更高效，每个厂各跑一次 `fetch_wastewater_df`

## ⚠ 年份默认规则

InfluxDB 数据覆盖 **2026-01-01 ~ 2026-07-25**。用户说"7月14日"没带年份时，**默认是 2026**。2024 或其他年份库里没有数据——直接告知即可，不需要查。

## 查询入口

```python
import os, sys
sys.path.insert(0, r'E:\project\Ecological_env')
os.chdir(r'E:\project\Ecological_env')

from shared.data.influxdb_query import get_client_and_bucket, fetch_wastewater_df

client, bucket = get_client_and_bucket()

# 查询某厂某天的进出水数据
influent = fetch_wastewater_df(client, bucket, "influent", ["COD", "pH"], plant_id="当阳市金桥污水处理厂一期")
effluent = fetch_wastewater_df(client, bucket, "effluent", ["COD", "pH"], plant_id="当阳市金桥污水处理厂一期")

# 切片到具体日期
july14 = influent.loc["2026-07-14":"2026-07-14"]

client.close()
```

## 多厂同时查询模板

```python
from shared.data.influxdb_query import get_client_and_bucket, fetch_wastewater_df

client, bucket = get_client_and_bucket()

plants = {
    "金桥厂": "当阳市金桥污水处理厂一期",
    "洗舱站": "洗舱站污水排放口",
}

results = {}
for short_name, plant_id in plants.items():
    eff = fetch_wastewater_df(client, bucket, "effluent", ["COD"], plant_id=plant_id)
    day_data = eff.loc["2026-07-14":"2026-07-14"]
    if not day_data.empty:
        results[short_name] = {
            "n": len(day_data),
            "mean": round(day_data["COD"].mean(), 2),
            "min": round(day_data["COD"].min(), 2),
            "max": round(day_data["COD"].max(), 2),
        }
    else:
        results[short_name] = "无数据"

client.close()
```

## 发现 plant_id

当不确定用户说的厂对应哪个 plant_id 时：

```python
flux = '''
from(bucket: "monitoring-data")
  |> range(start: 0)
  |> filter(fn: (r) => r._measurement == "wastewater")
  |> distinct(column: "plant_id")
'''
tables = client.query_api().query(flux)
for table in tables:
    for record in table.records:
        print(record.values.get('plant_id') or record.values.get('_value'))
```

## 已知 plant_id 列表（2026-08-26）

| 用户简称 | 实际 plant_id | 数据特征 |
|----------|--------------|---------|
| 金桥厂 | 当阳市金桥污水处理厂一期 | 进水+出水齐全 |
| 洗舱站 | 洗舱站污水排放口 | 仅有出水，无进水（正常） |
| - | 洗舱站污水 | 可能无数据 |

## 多厂查询注意事项

当用户要对比多个厂的数据时，在 `execute_code` 里一次性查完比逐个调 `call_subagent` 快得多。上面模板展示了批量查询方式。

## 注意事项

- `fetch_wastewater_df()` 返回 pandas DataFrame，timestamp 为索引
- 日期切片用 `.loc["YYYY-MM-DD":"YYYY-MM-DD"]`
- `plant_id` 不传 = 混合全库数据；传错 = 返回空 DataFrame
- 查询完毕必须 `client.close()`
- 字段名：`pH`, `COD`, `TN`, `AN`(=NH3-N), `TP`, `flow`, `discharge`, `suspended_solids`(=SS)
- 进水无数据时返回空 DataFrame（`df.empty == True`）
- 洗舱站无进水是**正常现象**，不是数据缺失
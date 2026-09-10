---
name: data-perception-core
description: 获取监测数据——从 InfluxDB 取进出水数据，忠实保留原始值，标记缺失，标注 HRT，生成 chartData。当任务涉及"获取数据"、"进水"、"出水"、"指标"、"时间范围"时使用本技能。务必使用——数据获取是整个研判链路的第一步，没有数据后续子智能体无法工作。
---

# 数据获取技能

## 你做什么

你调用一个脚本（`get_data.py`），它从 InfluxDB 取进出水监测数据。脚本自动完成所有工作：
- 取进水 + 出水数据（忠实保留原始值，含缺失/异常——这些是监控对象，不清洗）
- 标记缺失时间点（`missing_points`）
- 标注 HRT=2h（供下游规则推理按需做进水出水对齐）
- 生成 chartData（供前端画曲线）

**你的工作就是：解析任务里的时间范围 → 调脚本 → 确认完成。**

## 怎么调

脚本路径：`$HERMES_HOME/skills/data-perception-core/scripts/get_data.py`

**⚠️ Python 必须用项目 venv 的绝对路径**（PATH 里的 python 是 miniconda 3.8，缺 influxdb_client 等依赖，直接用必报 ImportError）：
```
E:/project/Ecological_env/ecological_env/Scripts/python.exe
```

### 时间范围 → 参数

脚本支持两种方式（二选一）：

**方式 1：起止日期**（任务给了明确日期时优先用）
```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --start "2026-07-14" --end "2026-07-15"
```

**方式 2：最近 N 小时**（任务说"最近X天/小时"时用）
```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --hours 168
```

| 任务里说的 | 用哪个参数 |
|---|---|
| "7月14日到15日"（跨2天） | `--start "2026-07-14" --end "2026-07-15"` |
| "7月14日" / "7月14日全天" / "14号那天"（**单日**） | `--start "2026-07-14" --end "2026-07-14"` |
| "最近一周" / "7天" | `--hours 168` |
| "最近3天" | `--hours 72` |
| "最近24小时" / "昨天" | `--hours 24` |
| "本月" / "一个月" | `--hours 720` |
| 没提时间 | `--hours 24`（唯一允许默认的情况） |

### 指定指标（**默认不传**！只在任务明确说"只要/仅看 N 个指标"且 N≤2 时才加）

**判据（2026-09-10 二次修正——列举指标被误判成点名导致曲线只画 2 条，"全指标"措辞也漏拦）**：
- **默认：不传** `--chart-indicators`，画全部水质指标（pH/COD/TN/氨氮/TP/SS）
- 仅当任务出现 **"只要X""仅看X""只关心X"** 这类限定词且 X 是 1-2 个指标（如"只要COD""仅看pH和COD"）→ 才加 `--chart-indicators "COD"`
- 任务**列举 ≥3 个指标**（"获取pH/COD/NH3-N/TN/TP/SS"=说明数据范围）、或含 **"全部/所有/整体/全指标/各指标"** 字样、或带 **"研判/异常检测/处置"**（下游要全量）→ **一律不传**
```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --start "2026-07-14" --end "2026-07-15" --chart-indicators "pH,COD"
```
不传时默认画所有水质指标。**拿不准就不传**——画全了比画少了好（画少了用户以为指标缺失）。

### 指定厂/监测点（**多厂库必传**，加这个参数）

库里有多个厂(监测点)。任务里提到厂/排放口名(如"金桥厂""洗舱站")→ 必须加 `--plant`，否则取到的是全库混合数据、结果错误：
```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --hours 24 --plant "当阳市金桥污水处理厂一期"
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --hours 24 --plant "洗舱站污水排放口"
```
厂名要写全称(InfluxDB 里的 plant_id)。任务里没提厂 → 用主任务上下文里给的厂；都没有才允许不传(单厂遗留行为)。

**多个厂 = 跑多次脚本，每次一个 --plant**。任务要两个厂的数据(如"金桥和洗舱站的COD")→ 依次跑两次。**最终答复必须逐厂列出关键统计**（每个厂的进/出水各指标 min/max/mean，脚本输出里有）——主智能体只能看到你的文字答复，你不写它就不知道；尤其**不要**说"只有XX厂有数据"除非某厂脚本明确返回 0 条。**禁止**为了"一次取多厂"用 terminal 自己写 Python 查库——get_data.py 是唯一数据入口,自己写的代码 import 环境不对必然失败。
不加这个参数时默认画所有水质指标（pH/COD/TN/氨氮/TP/SS）。

**关键**：从任务描述里识别时间，选对参数，把数值/日期写进命令。任务说"一周"就写 `--hours 168`，不能写成 24。

### 好的调用 vs 差的调用

```
✅ 好："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --start "2026-07-14" --end "2026-07-15"
   → "7月14日到15日"（跨2天），时间精确，脚本取对应范围

✅ 好："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --start "2026-07-14" --end "2026-07-14"
   → "7月14日全天"（单日）：start 和 end 同一天，脚本自动补到 23:59:59 取整天（24条）

✅ 好："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --hours 168
   → "一周"换算成 168 小时，正确

❌ 差："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --start "2026-07-14" --end "2026-07-15"
   → 任务只要"7月14日"（单日），却写成 14→15，**多取了一整天变成 48 条**！
     单日任务的 end 绝不能写次日，必须 --start=--end=同一天

❌ 差："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py"
   → 没传时间，默认 24 小时——任务要一周却只取了一天

❌ 差："E:/project/Ecological_env/ecological_env/Scripts/python.exe" "...get_data.py" --hours 24
   → 任务说"一周"却写了 24——没换算
```

## 执行流程

**两步完成，不多做：**

1. 用 `skill_view` 读本技能（你现在在读）
2. 用 `terminal` 运行脚本（按上面的时间→参数表选对参数）
3. 回复："✅ 脚本执行完成"

**就这三步。不需要其他任何操作。**

### 不要做的事（每多做一步浪费 ~6s）

- ❌ 不要先 `echo $HERMES_HOME` / `ls` / `pwd` 检查环境——系统已设置好
- ❌ 不要先检查 SESSION_DIR / InfluxDB 连接——脚本内部自动处理
- ❌ 不要跑完脚本后再 `ls` / `cat` / `python -c` 验证结果——结果文件由下游自动读
- ❌ 不要解析 JSON 或总结结果——主智能体会整合

### 为什么

每多一步探索 = 1 次 LLM 调用（~6s）。4 个子智能体 × 多 2-3 步 = 浪费 50-70s。直接 skill_view → 跑脚本 → 确认完成，3 步搞定。

## 为什么只调脚本、不做别的

**不解析 JSON / 不生成报告**：你的结果（`data_result.json`）由下游子智能体（异常检测）直接从文件读取，由主智能体整合成报告。你解析了也没人看，反而浪费你的迭代预算。

**不手写文件**：结果只能由 `get_data.py` 产出（它写了正确的格式 + metadata + chartData）。你手写会破坏格式，下游读不了。

**不探索目录**：你不需要知道项目结构，只需要调脚本。探索浪费时间和 token。

## 脚本输出

脚本自动保存到 `data_result.json`（在 `SESSION_DIR` 或子智能体默认目录），包含：
- `influent` / `effluent`：进出水数据（忠实原始，缺失值保留 None）
- `metadata`：时间范围、指标列表、`hrt_hours=2`、`missing_points`
- `chartData`：可视化数据（供前端画曲线）

下游异常检测链式消费此文件。

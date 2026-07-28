# 数据感知子智能体优化设计

> 2026-07-28 · brainstorm 产出 · 子智能体优化系列(1/4)

## 背景

数据感知子智能体(`multi-dimensional-data-perception`)的 `SOUL.md` 承诺了一整套数据治理(清洗/标准化/时间对齐/插值/质量报告),但 `get_data.py` 实际只做了"取数 + 格式化"。承诺与实现严重不符。

更根本的问题:**把"数据治理"套到监控系统上是方向性错误**——异常值和缺失值正是监控对象本身,清洗/补齐等于抹掉监控目标。

本设计重新定位数据感知:**忠实取数 + 客观标注,零分析**。

## 设计原则(监控理念)

1. **异常值、缺失值是监控对象**,绝不清洗/补齐
2. 数据感知**零分析**(不判异常、不判物理错误、不标准化)——分析全交下游
3. 子智能体的领域知识(HRT、指标定义)**内聚在技能里**,不放全局配置

## 职责

### 该做的

1. **忠实取数**:从 InfluxDB 取进/出水,保留原始(含缺失 `None`、异常值),不改一个数
2. **标记缺失**:`metadata` 标记哪些时间点缺数据(客观事实,不改数据)
3. **HRT 标注**:`metadata` 标 `hrt_hours=2`(技能领域常量);时间对齐交下游

### 不该做的(交下游)

| 不做 | 交给谁 | 原因 |
|---|---|---|
| 清洗异常值 | 异常检测 | 异常是监控对象 |
| 插值缺失 | 异常检测(检出) | 缺失是异常信号(设备故障/停产) |
| 标准化 | 异常检测(按算法需要) | 不是所有算法都要标准化 |
| 判物理错误值(pH=15) | 异常检测检出 → 规则推理排除 | 是分析,数据感知零分析 |

### 系统级三层职责(供参考,后续子智能体 spec 详述)

- **数据感知**:忠实取数 + 标记缺失
- **异常检测**:检出所有不正常(缺失/物理错误/现象异常),一视同仁
- **规则推理**:结合企业上报记录(停产/维修)排除合理异常,判定真违规

## 改动清单

### 1. `subagents/.../SOUL.md`
- **删**:清洗异常值、插值缺失、标准化、"数据质量报告(清洗义)"
- **改为**:忠实取数 + 标记缺失 + HRT标注 + 零分析
- **保留**:边界(不做异常/违规/预警)、水力停留时间概念(2h,标注用)

### 2. `subagents/.../AGENTS.md`(修 3 处过时)
- "SKILL.md 已预加载进 prompt" → "用 hermes 原生 `skill_view` 读 SKILL"
- "❌ 不要 skill_view/skills_list 探索" → "用 `skill_view` 读 SKILL.md"
- "从 `shared/data/*.csv` 取数" → "从 InfluxDB 取数"

### 3. `subagents/.../skills/data-perception-core/SKILL.md`
- **保留**:时间范围→参数换算表(LLM 解析自然语言时间用:一周=168h、明确日期用 `--start/--end`)
- **新增**:注明 HRT=2h(当前工艺领域常量)
- **不变**:调 `get_data.py` → 存 `data_result.json`

### 4. `subagents/.../skills/data-perception-core/scripts/get_data.py`
- **性能**:InfluxDB 查询用 Flux `range()` 按时间过滤(不全量 fetch 再 tail)
- **输出 metadata 新增**:
  - `hrt_hours: 2`(HRT 标注)
  - `missing_points: [缺失时间点列表]`
- **不清洗/不插值**:缺失值保留 `None`

### 5. `workspace/skills/orchestrator-core/scripts/subagent_entry.py`(全局,影响 4 子智能体)
- **删**:自愈给命令机制(第二轮 `run_conversation` + `SUBAGENT_DEFAULT_CMD` 映射)
- **保留**:初始 prompt 强化("评判成功的唯一标准是 terminal 运行了脚本,禁止只回'我已就绪'")
- **结果**:LLM 第一轮(强 prompt 引导)→ 大概率直接跑;没跑 → 标记 `failed` → 主智能体重试

## 输出契约(`data_result.json`)

```json
{
  "task_id": "task_...",
  "status": "completed",
  "result": {
    "influent": [{"timestamp":"2026-07-14 00:00:00","pH":7.43,"COD":68.03,...}, ...],
    "effluent": [...],
    "metadata": {
      "time_range": "2026-07-14 至 2026-07-15",
      "indicators": ["pH","COD","TN","NH3-N","TP","SS","flow_rate","discharge_volume"],
      "hrt_hours": 2,
      "missing_points": ["2026-07-15 14:00:00"],
      "data_source": "influxdb"
    }
  },
  "metadata": {"subagent":"multi-dimensional-data-perception-agent","timestamp":"...","llm_driven":true}
}
```

**下游影响**:
- 异常检测:`influent`/`effluent` 结构未变,`metadata` 加字段不影响(向后兼容)
- 证据链:数据感知 evidence=`{kind:data, rows_in, rows_out}`(现有,不变)

## 错误处理

- LLM 没跑脚本 → entry 标记 `failed`(无自愈)→ 主智能体重试
- InfluxDB 连不上 / token 缺 → `failed` + 错误信息
- 数据全空 → `failed`("未取到数据")
- 极端:ctgu-vlm 连续"读了不执行" → 主智能体重试也失败 → 本次查询失败(概率低,接受,换纯粹性)

## 测试

- `get_data.py` 单元:
  - 取数正确(InfluxDB `range()` 过滤)
  - `missing_points` 标记(构造缺失数据验证)
  - `hrt_hours` 标注(=2)
- 端到端:`scripts/smoke_test.py` 覆盖(数据感知产出 `data_result` 含新 metadata)

## 决策记录

- **删清洗/插值**:监控系统不能抹掉监控对象(异常/缺失是信号)
- **HRT 标注不做对齐(方向 B)**:下游需求分化(异常检测独立,规则推理的稀释排放才需因果),数据感知零分析、不预设因果
- **时间换算归 LLM**:自然语言时间无穷尽("上周""前天""7月中旬"),脚本正则不现实,LLM 擅长语义解析
- **去自愈**:自愈给命令是 hack(硬编码命令 + 时间窗不准),违背 LLM 驱动;失败主智能体重试更纯粹

## 范围

本 spec 仅数据感知子智能体。异常检测 / 规则推理 / 处置执行各自单独 spec。

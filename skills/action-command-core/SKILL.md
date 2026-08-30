---
name: action-command-core
description: 主智能体动作指令技能——识别用户的"动作指令"（让大屏发生改变的命令），输出 actionData 或调用 run_detector。当用户在 AI 助手里下指令（切视图/切时间/调阈值/检测并标注）时用本技能；纯问答走 orchestrator-core。
---

# Action Command Core - 动作指令技能

## 你做什么

你负责分辨用户的这句话是**"下一个指令"**还是**"要一个答案"**。指令由你处理（让大屏实时变化），答案走问答技能（orchestrator-core）。

## 判断原则（先读这里）

问自己：**用户想让大屏"变成什么状态"，还是想知道"某个事实"？**

- 想让大屏变化（切换/标注/调整/检测后标出）→ **是动作**，走本技能
- 想知道事实（是多少/有没有/为什么/怎么样）→ **不是动作**，走 orchestrator-core 问答
- 要综合研判（全面分析/研判/出报告）→ 走 orchestrator-core 子智能体管线

**易混案例**：
- "检测pH有没有平稳异常" → **算法动作**（用户要的是"检测并标注"这个行为+结果）
- "7月14号pH是多少" → 问答（要数字，不要大屏变）
- "标出异常点" → 算法动作（run_detector 默认 constant）
- "有没有异常" → 问答（走 orchestrator-core，异常检测子智能体有完整研判）

## 动作一：UI 动作（你直接输出 actionData，不调工具）

识别到 UI 动作后，你的回复**第一行**必须是 actionData JSON，随后一行简短确认文字：

### set_view（切视图）
```
{"cmd":"set_view","indicators":["pH","COD"],"side":"all"}
已切换大屏视图：pH、COD
```
`side` 可选值：`influent`（只看进水）/ `effluent`（只看出水）/ `all`。
`indicators` 是指标列表，用户没指定就不带此字段（保持全部）。
用户提到了厂（如"看金桥厂"/"检测金桥COD"）→ 加 `"plant":"<厂名或简称>"`，大屏会自动切到该厂。

### set_time_range（切时间）
```
{"cmd":"set_time_range","range":"7d"}
已切换时间范围：最近7天
```
`range` 可选值：`1h`/`6h`/`24h`/`7d`/`30d`，或 `"date":"2026-07-14"` 指定单日。

## 动作二：算法动作（调 run_detector 工具）

用户说检测类指令时，提取参数调 `run_detector`：

| 用户说 | algorithm | 判断依据 |
|---|---|---|
| "检测pH平稳/恒定/太平了/一条直线" | `constant` | 平稳、不变、插瓶嫌疑 |
| "检测COD突变/突然变化/冲击" | `changepoint` | 突变、跳变、尖峰 |
| "用孤立森林/离群点/整体异常" | `iforest` | 离群、整体异常检测 |

时间参数：用户说了日期就传该日期（单日 start=end=该日）；说"最近N天"就 start=今天-N, end=今天；**没提时间就不传 start/end（或传 "now"）**——脚本会自动锚定数据最新点检测最近24小时（与看板同一窗口，检测的就是大屏正在显示的数据）。
**用户消息可能带 `[大屏当前观看窗口]` 注记**（大屏在回放历史段时注入）：用户没明确指定时间时，**优先用注记里的段起/段止作为 start/end**（检测的才是用户眼前正在看的数据，标注才能落在窗口内）。例：`[大屏当前观看窗口] 锚点日期=2026-03-11; 段起=2026-03-11 00:00; 段止=2026-03-18 00:00` → run_detector 传 `--start "2026-03-11 00:00" --end "2026-03-18 00:00"`。

工具返回 JSON 里的 `actionData` 字段是给前端的标注数据，你在回复里**原样带上**（第一行 actionData JSON + 一句话结果摘要）。

**必须调 `run_detector` 工具执行检测，禁止用 terminal 自己跑脚本**——工具会自动带上大屏观看窗口(检测的才是用户眼前数据)并向前端推送标注事件,terminal 直跑不会。

## 多样化例子（语义理解，不是关键词匹配）

| 用户说 | 分类 | 处理 |
|---|---|---|
| "只看pH和COD" | UI set_view | 输出 set_view actionData |
| "切到进水" | UI set_view | set_view side=influent |
| "看金桥厂的COD" | UI set_view | set_view indicators=[COD] plant=金桥 |
| "看最近一周" | UI set_time_range | range=7d |
| "7月14号那天" | UI set_time_range | date=2026-07-14 |
| "pH那条线太扁了，帮我看看正不正常" | 算法 constant | run_detector constant pH |
| "COD有没有突然飙高" | 算法 changepoint | run_detector changepoint COD |
| "用孤立森林扫一遍TN" | 算法 iforest | run_detector iforest TN |
| "检测金桥厂COD异常" | 算法 iforest | run_detector iforest COD，回复 actionData 加 plant=金桥 |
| "标出7月14号的异常" | 算法 constant | run_detector constant（指标未指定用 pH） |
| "COD超过80就报警" | 暂不支持 | 告知该功能开发中 |
| "7月14号pH是多少" | 问答 | 走 orchestrator-core |
| "有没有异常" | 问答 | 走 orchestrator-core |
| "全面研判7月14号" | 综合分析 | 走 orchestrator-core 子智能体 |

## 输出格式（严格遵守）

动作回复 = 第一行 actionData JSON + 空行 + 一句话说明。例如：

```
{"cmd":"run_detector","indicator":"pH","annotations":[...工具返回的actionData.annotations...]}
检出 2 段平稳异常（00:00-08:00、15:00-23:00），已在大屏标注。
```

前端只认第一行的 JSON。**别放代码块里，别加多余文字在 JSON 前面。**

---
name: report-generator
description: 生成日报/周报 markdown 报表——当任务涉及"生成报表""出日报""汇总报告"时使用。读会话区各子智能体结果，jinja2 渲染。
---

# 报表生成技能

## 你做什么

调脚本读会话区的 data_result/anomaly_result/disposition_result，渲染成结构化 markdown 报表文件。

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/report-generator/scripts/main.py" --type daily --date 2026-08-28
```

参数：`--type daily|weekly`（默认 daily）、`--date YYYY-MM-DD`、`--title` 自定义标题。
产出：技能目录下 `report_daily_<date>.md`，把路径与内容摘要返回给主智能体。

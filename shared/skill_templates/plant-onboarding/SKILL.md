---
name: plant-onboarding
description: 新监测点接入向导——当任务涉及"接入新厂""新监测点""报表导入前检查"时使用。检查 plant-hierarchy.yaml 四段配置是否齐备并输出待补清单。
---

# 新监测点接入向导

## 你做什么

调脚本检查新厂在 plant-hierarchy.yaml 的四段配置（层级/别名/报表映射/单厂配置），输出待办清单，指导用户在配置中心补齐后导入报表。

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/plant-onboarding/scripts/main.py" --report-name "洗舱站数据报表" --plant-id "洗舱站污水排放口"
```

产出：JSON 摘要（就绪项/待补项）。把待补项翻译成用户可操作的步骤（去 /agents/config 厂区配置补齐 → 跑 import_to_influxdb.py 导数）。

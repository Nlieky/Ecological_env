---
name: data-export
description: 导出监测数据 CSV——当任务涉及"导出数据""下载数据""存成CSV"时使用。与 get_data 同款查询，落 CSV 文件。
---

# 数据导出技能

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/data-export/scripts/main.py" --plant "当阳市金桥污水处理厂一期" --start 2026-07-14 --end 2026-07-15
```

产出：技能目录下 CSV（utf-8-sig，Excel 直开）。返回行数与文件名。

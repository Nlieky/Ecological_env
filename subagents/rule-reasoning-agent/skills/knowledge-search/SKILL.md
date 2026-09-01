---
name: knowledge-search
description: 检索废水知识库——当任务涉及"法规怎么规定""违规模式""专家经验"时使用。grep 四库返回命中段落与出处文件。
---

# 知识库检索技能

## 怎么调

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/knowledge-search/scripts/main.py" --query "稀释排放" --top 5
```

返回 JSON（命中段+文件路径）。把命中内容与出处整合进回答，注明来自哪个库。

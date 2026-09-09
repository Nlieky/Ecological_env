---
name: graph-query
description: 查询知识图谱——违规模式详情/历史案例/法条关联。研判需要历史案例佐证或法条依据（§39 禁止条款+§83 罚则）时使用。图不可用时输出 error，跳过即可。
---

# graph-query：知识图谱查询

## 用途

查图谱拿结构化知识，辅助研判：
- **模式**（特征 desc/实现状态 status）、检测算子（detects）、历史案例（cites）
- **历史案例**（全部/按厂过滤）
- **法条**（indicates：篡改类 §39 禁止+§83 罚则双锚）

## 怎么调（一条命令，一次只查一种）

```bash
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/graph-query/scripts/query_graph.py" --pattern "插瓶干扰"
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/graph-query/scripts/query_graph.py" --cases
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/graph-query/scripts/query_graph.py" --cases --plant "当阳市金桥污水处理厂一期"
"E:/project/Ecological_env/ecological_env/Scripts/python.exe" "$HERMES_HOME/skills/graph-query/scripts/query_graph.py" --law "人工拟合"
```

## 输出

单行紧凑 JSON，直接读：
- `--pattern`：`{label, desc, status, detects:[算子名], cases:[{label,severity,timestamp}], laws:[{article,note,anchor}]}`
- `--cases`：`{cases:[{label,timestamp,severity,types,plant}]}`
- `--law`：`{label, laws:[{article,note,anchor}]}`（省 token，不查算子/案例）

## 纪律

- 一次只查一种模式；一次研判全程最多查 1-2 次（拿模式法条或案例佐证即可，不是必须步骤）
- 输出 `{"error":"graph_unavailable"}` 是正常现象——跳过图谱继续研判，不要重试
- 图谱查不到的模式（`pattern_not_found`）不构成"无违规"的证据
- 禁止用 terminal 直接读 shared/data/knowledge_graph.db 文件

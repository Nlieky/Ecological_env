#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端测试:通过 /api/query 让智能体走完整条编排,看回答引用的数据年份。

用 requests(json= 自动 UTF-8)避开 curl 在 git-bash 下中文 body 的编码问题。
"""
import json
import requests

QUERY = "请查询最近24小时进水的COD和氨氮数据，报告最新数据的时间戳和具体数值，并分析有无异常"

print(f"发起查询: {QUERY}\n等待智能体编排(~2-3分钟)...\n")
r = requests.post("http://localhost:8000/api/query",
                  json={"query": QUERY}, timeout=280)
print("HTTP", r.status_code)
try:
    d = r.json()
except Exception:
    print("非 JSON 响应:", r.text[:1500])
    raise SystemExit(1)

if not isinstance(d, dict) or "content" not in d:
    print("响应无 content 字段,原始:", json.dumps(d, ensure_ascii=False)[:1500])
    raise SystemExit(1)

content = d.get("content", "")
print(f"\n=== 回答(长度 {len(content)}) ===")
print(content[:3000])

# 关键判定:回答里是否出现 2026(真实数据)而非 2024(历史)
print("\n=== 数据年份判定 ===")
print("含 '2026':", "2026" in content)
print("含 '2024':", "2024" in content)

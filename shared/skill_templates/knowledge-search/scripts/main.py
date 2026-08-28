#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检索废水知识库（法规/工艺/违规模式/专家经验），返回命中段落。
参数：--query "稀释排放" --top 5"""
import argparse
import json
import re
import sys
from pathlib import Path

# 注: parents[4] 对应模板库位置层级; 安装到主智能体(skills/<n>/...)改 parents[3]; 安装到子智能体(subagents/<x>/skills/...)改 parents[5]
KB = Path(__file__).resolve().parents[4] / "shared" / "knowledge"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--top", type=int, default=5)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    hits = []
    pattern = re.compile(re.escape(args.query))
    for md in KB.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in pattern.finditer(text):
            start = max(0, m.start() - 80)
            hits.append({"file": md.relative_to(KB).as_posix(),
                         "snippet": text[start:m.end() + 120].replace("\n", " ")})
            if len(hits) >= args.top * 3:
                break
    hits = hits[: args.top]
    print(json.dumps({"summary": f"命中 {len(hits)} 段", "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

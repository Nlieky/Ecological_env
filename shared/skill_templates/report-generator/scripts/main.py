#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日报/周报生成：读会话区结果文件，jinja2 渲染 markdown 报表。
参数：--type daily|weekly  --date 2026-08-28  --title 自定义标题"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Template

# 注: parents[4] 对应模板/技能目录层级; 若安装到子智能体目录(subagents/<x>/skills/...)需改 parents[5]
SESSION_DIR = Path(__file__).resolve().parents[4] / "sessions"
TEMPLATE = Template("""# {{ title }}

生成时间：{{ now }}
数据日期：{{ date }}

## 数据概况

{% for line in data_lines %}{{ line }}
{% endfor %}

## 异常与研判

{% for line in anomaly_lines %}{{ line }}
{% endfor %}

## 处置建议

{% for line in disposition_lines %}{{ line }}
{% endfor %}
""")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["daily", "weekly"], default="daily")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--title", default="")
    return ap.parse_args()


def _load(session_dir: Path, name: str) -> dict:
    p = session_dir / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    args = parse_args()
    title = args.title or ("日报" if args.type == "daily" else "周报") + f" {args.date}"
    sd = Path(__file__).resolve().parents[4] / "sessions" / "current"
    sd = sd if sd.exists() else SESSION_DIR
    data = _load(sd, "data_result.json")
    anomaly = _load(sd, "anomaly_result.json")
    disposition = _load(sd, "disposition_result.json")
    data_lines = [f"- {k}: {v}" for k, v in (data.get("statistics") or {}).items()] or ["- 无数据摘要"]
    anomaly_lines = [f"- {a}" for a in (anomaly.get("summary") or [])] or ["- 无异常"]
    disposition_lines = [f"- {d}" for d in (disposition.get("summary") or [])] or ["- 无处置建议"]
    report = TEMPLATE.render(title=title, now=datetime.now().isoformat(timespec="seconds"),
                             date=args.date, data_lines=data_lines,
                             anomaly_lines=anomaly_lines, disposition_lines=disposition_lines)
    out = Path(__file__).resolve().parents[2] / f"report_{args.type}_{args.date}.md"
    out.write_text(report, encoding="utf-8")
    print(json.dumps({"summary": f"已生成 {out.name}（{len(report)} 字符）"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

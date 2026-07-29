#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全链路冒烟测试 —— 演示前一键跑，确认没有回归。

做三件事：
  1. 服务健康检查（Agent 8642 / 后端 8000 / InfluxDB 8086）
  2. 发一个标准查询，断言：有回答 + 主智能体调用了子智能体
  3. 查审计库，断言：decision + execution 按 turn_id 落库且 turn_id 一致、
     execution 的 output_result 里有结构化 evidence（异常/违规/预警/数据条数）

用法：
  ecological_env/Scripts/python.exe scripts/smoke_test.py
"""
import sys
import json
import time
import sqlite3
from pathlib import Path

# Windows 控制台默认 GBK，输出 emoji(✅❌)/中文会 UnicodeEncodeError；强制 UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND = "http://localhost:8000"
AGENT = "http://localhost:8642"
INFLUXDB = "http://localhost:8086"
DB_PATH = PROJECT_ROOT / "shared" / "data" / "ecological_logs.db"
# 用一个会触发完整 pipeline 的问题（数据感知 → 异常检测 → 规则 → 处置）
QUERY = "7月14号到15号的进出水数据有没有异常？请给出异常和违规研判。"


def check(name: str, url: str) -> bool:
    try:
        r = requests.get(url, timeout=5)
        ok = r.status_code == 200
        print(f"  [{'✅' if ok else '❌'}] {name}: HTTP {r.status_code}")
        return ok
    except Exception as e:
        print(f"  [❌] {name}: 连不上 ({e})")
        return False


def main():
    print("=" * 52)
    print("           全链路冒烟测试")
    print("=" * 52)
    fails = []

    # ── 1. 服务健康 ──
    print("\n[1/3] 服务健康检查")
    if not check("Agent 服务(8642)", f"{AGENT}/health"):
        fails.append("Agent 服务未就绪")
    if not check("后端(8000)", f"{BACKEND}/api/health"):
        fails.append("后端未就绪")
    if not check("InfluxDB(8086)", f"{INFLUXDB}/health"):
        fails.append("InfluxDB 未就绪")
    if fails:
        print(f"\n❌ 服务未就绪: {fails}")
        print("   请按 README 顺序启动：InfluxDB → Agent → 后端 → 前端")
        sys.exit(1)

    # ── 2. 发标准查询 ──
    print(f"\n[2/3] 发查询：「{QUERY}」")
    print("   (走完整 pipeline，约 60-120s，请稍候...)")
    t0 = time.time()
    try:
        r = requests.post(f"{BACKEND}/api/query",
                          json={"query": QUERY}, timeout=350)
        elapsed = time.time() - t0
        data = r.json()
    except Exception as e:
        print(f"❌ 查询请求失败: {e}")
        sys.exit(1)

    content = data.get("content", "")
    trace = data.get("trace") or {}
    decision = trace.get("decision_path") or []
    calls = trace.get("subagent_calls") or []

    print(f"   耗时 {elapsed:.1f}s | 回答 {len(content)} 字")
    print(f"   decision_path = {decision}")
    print(f"   子智能体调用 = {len(calls)} 个: {[c.get('subagent_name') for c in calls]}")
    if not content:
        fails.append("回答内容为空")
    # 注：/api/query 返回的 QueryResponse 不带 trace（子智能体调用明细），calls 恒为空；
    # 子智能体是否真被调用 + evidence 是否写出，由 [3/3] 审计落库检查（按 turn_id 查 db）验证。

    # ── 3. 审计落库（turn_id + evidence）──
    print(f"\n[3/3] 审计落库检查（turn_id 贯穿 + evidence 结构化）")
    if not DB_PATH.exists():
        fails.append(f"审计库不存在: {DB_PATH}")
    else:
        con = sqlite3.connect(str(DB_PATH))
        cur = con.cursor()
        cur.execute("SELECT turn_id, decision_path FROM master_agent_decision_logs "
                    "ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            fails.append("master_decision 未落库")
        else:
            tid, dp = row
            print(f"   最新决策 turn_id = {(tid or 'NULL')[:12]}..  decision_path = {dp}")
            if not tid:
                fails.append("最新决策无 turn_id（旧数据/写入异常）")
            else:
                cur.execute("SELECT subagent_name, turn_id, output_result "
                            "FROM sub_agent_execution_logs WHERE turn_id=? ORDER BY id", (tid,))
                exs = cur.fetchall()
                print(f"   同 turn_id 的 execution = {len(exs)} 个")
                if not exs:
                    fails.append("execution 未按 turn_id 落库")
                elif any(e[1] != tid for e in exs):
                    fails.append("execution turn_id 与 decision 不一致")
                # evidence
                ev_kinds = []
                for _, _, out in exs:
                    try:
                        d = json.loads(out) if out else {}
                        ev = d.get("evidence") or {}
                        if ev.get("kind"):
                            ev_kinds.append(ev["kind"])
                    except Exception:
                        pass
                print(f"   结构化 evidence = {ev_kinds}")
                if exs and not ev_kinds:
                    fails.append("execution 无结构化 evidence（子智能体可能未产出结果）")
        con.close()

    # ── 结论 ──
    print("\n" + "=" * 52)
    if fails:
        print(f"❌ 冒烟测试失败（{len(fails)} 项）:")
        for f in fails:
            print(f"   - {f}")
        print("\n排查建议：看 agent 服务日志 + sessions/_subagent_traces/ + 后端日志")
        sys.exit(1)
    else:
        print("✅ 冒烟测试通过：服务健康 + 全链路打通 + 审计完整。可演示。")
        sys.exit(0)


if __name__ == "__main__":
    main()

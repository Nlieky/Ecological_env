#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端智能体 pipeline 验证桩。

绕开前端/后端，直接打 Hermes 主智能体（8642）。发一个命中全部 4 个触发词
(数据/异常/违规超标/预警处置)的查询，等它跑完 data→anomaly→rule→disposition，
然后扫描 sessions/ 目录证明每一步都产出了结果，并打印最终研判结论。

用法:
    ecological_env/Scripts/python.exe scripts/e2e_pipeline_check.py
    ecological_env/Scripts/python.exe scripts/e2e_pipeline_check.py --query "..."
    ecological_env/Scripts/python.exe scripts/e2e_pipeline_check.py --direct   # 秒级直连4脚本，不经过LLM编排
"""
import sys, os, json, time, glob, argparse, subprocess, tempfile
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT = Path(__file__).resolve().parent.parent
SESSIONS = PROJECT / "sessions"

# 命中全部4类触发词：数据(感知) / 异常(检测) / 违规超标(规则) / 预警处置(研判)
DEFAULT_QUERY = "分析最近24小时出水监测数据，检测是否存在异常，判断是否违规超标，并给出预警与处置建议。"

AGENT_URL = "http://localhost:8642/query"
TIMEOUT = 2500  # 须大于 master total_timeout 默认 2400

RESULT_FILES = {
    "数据感知": "data_result.json",
    "异常检测": "anomaly_result.json",
    "规则推理": "rule_reasoning_result.json",
    "研判处置": "disposition_result.json",
}


def direct_mode():
    """秒级直连 4 个 canonical 脚本（不经 LLM 编排），验证脚本链本身正确。"""
    print("=== DIRECT 模式：串行跑 4 个脚本（不经 LLM）===")
    session = tempfile.mkdtemp(prefix="e2e_direct_", dir=str(SESSIONS))
    print(f"SESSION_DIR = {session}\n")
    scripts = [
        ("数据感知", "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py", ["--hours", "24"]),
        ("异常检测", "subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py", ["--session-dir", session]),
        ("规则推理", "subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/run_rule_reasoning.py", ["--session-dir", session]),
        ("研判处置", "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py", ["--session-dir", session]),
    ]
    env = os.environ.copy()
    env["SESSION_DIR"] = session
    for name, rel, extra in scripts:
        script = PROJECT / rel
        t0 = time.time()
        r = subprocess.run([sys.executable, str(script)] + extra,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120, cwd=str(PROJECT), env=env)
        dt = time.time() - t0
        ok = "✅" if r.returncode == 0 else "❌"
        print(f"{ok} [{name}] exit={r.returncode}  {dt:.1f}s  {rel}")
        if r.returncode != 0:
            print("   stderr:", (r.stderr or "")[-400:])
    print("\n=== 各步结果文件 ===")
    for name, fn in RESULT_FILES.items():
        p = Path(session) / fn
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                print(f"  ✅ {name}: status={d.get('status')}  keys={list((d.get('result') or {}).keys())[:6]}")
            except Exception as e:
                print(f"  ⚠️  {name}: 解析失败 {e}")
        else:
            print(f"  ❌ {name}: 缺失 {fn}")


def master_mode(query):
    """经主智能体 LLM 编排跑完整 pipeline。"""
    import urllib.request, time as _t
    # 每次 run 用唯一 session_id，避免主智能体对话历史跨 run 累积（否则它会拿历史直接答、不重新编排）
    sid = f"e2e-fresh-{int(_t.time())}"
    body = json.dumps({"query": query, "session_id": sid},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(AGENT_URL, data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    print(f"=== MASTER 模式：POST {AGENT_URL} ===")
    print(f"查询: {query}\n")
    # 记录跑前已有的 session 目录，以便识别本次新建的
    before = set(glob.glob(str(SESSIONS / "session_*")))
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=TIMEOUT)
        raw = r.read().decode("utf-8")
        dt = time.time() - t0
        print(f"HTTP {r.status}  耗时 {dt:.0f}s")
        d = json.loads(raw)
    except Exception as e:
        print(f"❌ 请求失败 ({time.time()-t0:.0f}s): {e}")
        return

    # 最终回答
    ans = d.get("answer") or d.get("response") or d.get("final_response") or d.get("content") or ""
    print("\n=== 主智能体最终回答 ===")
    print(str(ans)[:1200])

    # 找本次新建的 session 目录（取最新的）
    after = sorted(glob.glob(str(SESSIONS / "session_*")), key=os.path.getmtime)
    new_dirs = [d_ for d_ in after if d_ not in before]
    target = new_dirs[-1] if new_dirs else (after[-1] if after else None)
    print(f"\n=== 本次 session 目录: {target} ===")
    if target:
        for name, fn in RESULT_FILES.items():
            p = Path(target) / fn
            if p.exists():
                try:
                    dd = json.loads(p.read_text(encoding="utf-8"))
                    res = dd.get("result") or {}
                    hint = ""
                    if isinstance(res, dict):
                        if "anomalies" in res:
                            hint = f"anomalies={len(res.get('anomalies') or [])}"
                        elif "has_violation" in res:
                            hint = f"has_violation={res.get('has_violation')} suspicion={res.get('suspicion_level')}"
                        elif "alert" in str(res).lower() or "work_order" in res:
                            hint = f"keys={list(res.keys())[:5]}"
                        elif "effluent" in res:
                            hint = f"effluent={len(res.get('effluent') or [])}h influent={len(res.get('influent') or [])}h"
                    print(f"  ✅ {name} ({fn}): status={dd.get('status')}  {hint}")
                except Exception as e:
                    print(f"  ⚠️  {name}: 解析失败 {e}")
            else:
                print(f"  ❌ {name}: 缺失 {fn}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--direct", action="store_true", help="秒级直连4脚本，不经过LLM")
    args = ap.parse_args()
    SESSIONS.mkdir(parents=True, exist_ok=True)
    if args.direct:
        direct_mode()
    else:
        master_mode(args.query)


if __name__ == "__main__":
    main()

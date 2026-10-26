#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量动作分类器——在主智能体(重型 agentic 管线)之前做单轮 LLM 分类。

为什么:动作指令("检测pH异常""只看COD")本质是确定性命令,走 15 轮迭代+7 工具的
agentic 循环实测 3 分钟;单次裸 LLM 调用(无工具/无身份/无循环)1-2 秒足够。
判断归 LLM(单轮),执行归代码(直调算子脚本)。未识别 → 落回主智能体管线。

用法(agent 服务内):
    from xxx import classify_action
    verdict = classify_action("检测pH平稳异常", view_context=dict|None)
    # verdict.is_action == True → verdict.executor 输出给前端, verdict.run() 执行
"""
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 项目根(标记法)
for _p in Path(__file__).resolve().parents:
    if (_p / "shared").is_dir() and (_p / "workspace").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
_ROOT = [p for p in Path(__file__).resolve().parents
         if (p / "shared").is_dir() and (p / "workspace").is_dir()][0]

_DETECTOR = Path(__file__).resolve().parent / "run_detector.py"

# ── 分类提示词:只判动作+抽参数,禁止闲聊 ─────────────────────────────
_SYSTEM = """你是废水监测大屏的动作分类器。只做一件事:判断用户这句话是不是"动作指令",是就输出 JSON,不是就输出 NOT_ACTION。

动作指令 = 想让监测大屏发生改变的命令,分两类:
1. 算法检测类(调检测器): 凡是"对某指标跑检测/在屏上标注异常"的祈使表达,不限于"检测"二字。
   常见句式: "检测X异常/标出X异常点/把X异常标注出来/找出X的离群点/X有没有突变帮我查并标出/扫描X"。
   算法选择: 平稳/恒定/太直/一条线→constant; 突变/飙高/跳变/冲击→changepoint; 离群/孤立森林/笼统说"异常"→iforest。
   输出: {"action":"run_detector","indicator":"pH|COD|TN|NH3-N|TP|SS","algorithm":"constant|changepoint|iforest","side":"effluent"}
   指标中文映射: pH→pH, 化学需氧量→COD, 总氮→TN, 氨氮→NH3-N, 总磷→TP, 悬浮物→SS。没指明指标用 pH。
   用户提到厂/排放口名(如"金桥厂""洗舱站")→加 "plant":"<名称或简称>";没提不带此键(默认大屏当前厂)。
   指令可以同时带厂和指标:"检测洗舱站的氨氮异常"→{"action":"run_detector","indicator":"NH3-N","algorithm":"iforest","side":"effluent","plant":"洗舱站"}。
   提到了具体厂名不会让句子变成非动作——只要核心是对大屏下命令,就仍是动作。
   句式里有"也/再/顺便"等承接词仍是动作(如"把氨氮的异常也标注出来")。
2. 视图切换类: "只看X/切到X/看进水/看出水/看最近N天/看X月X号"等
   只切指标: {"action":"set_view","indicators":["pH",...],"side":"influent|effluent|all"}
   只切时间: {"action":"set_time_range","range":"1h|6h|24h|7d|30d"} 或 {"action":"set_time_range","date":"YYYY-MM-DD"}
   都切: 两个键都带。

不是动作指令的情况(输出 NOT_ACTION): 问数值/问有没有异常及原因/要分析研判/要报告/闲聊/打招呼/"是什么/怎么样/为什么"句式。
判断要点: 句子是在**下命令让大屏做事**(动作),还是在**要信息/解释**(非动作)。
"有没有异常?"是提问(NOT_ACTION);"检测一下异常/标出异常/把异常标出来"是命令(动作)。

只输出一行:JSON 或 NOT_ACTION。不要解释,不要代码块。"""

_Cache = None


def _get_client():
    """复用 .env 的 LLM 配置,裸 OpenAI 客户端(不经 hermes)。"""
    global _Cache
    if _Cache is not None:
        return _Cache
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
    from openai import OpenAI
    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.environ["LLM_API_KEY"],
        timeout=20,
    )
    _Cache = client
    return client


@dataclass
class ActionVerdict:
    """分类结果。is_action=True 时 execute() 产出给前端的 actionData。"""
    is_action: bool
    raw: str = ""
    action: dict = field(default_factory=dict)
    error: Optional[str] = None

    def execute(self, view_context: dict | None = None) -> str:
        """执行动作,返回给前端的文本(第一行 actionData JSON + 一句话)。"""
        if not self.is_action:
            return ""
        cmd = self.action.get("action")
        if cmd == "run_detector":
            return self._run_detector(view_context)
        # UI 动作:直接透传为 actionData
        ad = dict(self.action)
        ad["cmd"] = cmd
        desc = _ui_action_desc(ad)
        return f"{json.dumps(ad, ensure_ascii=False)}\n\n{desc}"

    def _run_detector(self, view_context: dict | None) -> str:
        vc = view_context or {}
        # 窗口优先级:观看窗口兜底(检测用户眼前数据) — 分类器不抽时间,统一锚定观看窗口或最新点
        start = vc.get("segmentStart") or "now"
        end = vc.get("segmentEnd") or "now"
        plant = str(self.action.get("plant") or vc.get("plant") or "")  # 指令提厂优先,否则大屏当前厂
        try:
            r = subprocess.run(
                [sys.executable, str(_DETECTOR),
                 "--algorithm", str(self.action.get("algorithm", "constant")),
                 "--indicator", str(self.action.get("indicator", "pH")),
                 "--start", str(start), "--end", str(end),
                 "--side", str(self.action.get("side", "effluent")),
                 *(["--plant", plant] if plant else [])],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=90, cwd=str(_ROOT),
            )
            out = r.stdout.strip()
            data = json.loads(out) if out else {}
        except Exception as e:
            return f"检测执行失败: {e}"
        if not isinstance(data, dict) or data.get("status") != "completed":
            err = (data or {}).get("error", "")
            hint = (data or {}).get("hint", "")
            return f"检测失败: {err} {hint}".strip()
        ad = dict(data.get("actionData") or {})
        ad.setdefault("cmd", "run_detector")
        if plant:
            ad.setdefault("plant", plant)
        n = len(data.get("anomalies") or [])
        rng = (data.get("summary") or {}).get("time_range", "")
        alg_cn = {"constant": "平稳", "changepoint": "突变", "iforest": "离群"}.get(
            str(self.action.get("algorithm")), "异常")
        ind = self.action.get("indicator", "pH")
        plant_txt = f"{plant} " if plant else ""
        return (f"{json.dumps(ad, ensure_ascii=False)}\n\n"
                f"已完成 {plant_txt}{ind} {alg_cn}检测({rng}),检出 {n} 个异常点,已在大屏标注。")


def _ui_action_desc(ad: dict) -> str:
    if ad.get("cmd") == "set_view":
        parts = []
        if ad.get("indicators"):
            parts.append("指标 " + "、".join(ad["indicators"]))
        if ad.get("side"):
            parts.append({"influent": "进水侧", "effluent": "出水侧", "all": "进出水"}.get(ad["side"], ""))
        return f"已切换大屏视图:{' '.join(p for p in parts if p)}"
    if ad.get("cmd") == "set_time_range":
        if ad.get("date"):
            return f"已切换到 {ad['date']} 单日视图"
        return f"已切换时间范围:{ad.get('range')}"
    return "已执行"


def classify_action(query: str, timeout_s: int | None = None) -> ActionVerdict:
    """单轮 LLM 分类。任何异常都返回 is_action=False(落回主智能体管线,安全兜底)。"""
    try:
        if timeout_s is None:
            from backend.services.agent_strategy import get_strategy
            timeout_s = get_strategy("action_shortcircuit_timeout", default=30)
        client = _get_client()
        resp = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "deepseek-v4-pro"),
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": query}],
            max_tokens=200,
            temperature=0,
            timeout=timeout_s,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # 剥可能的代码块包裹
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        if not raw or raw.upper().startswith("NOT_ACTION"):
            return ActionVerdict(is_action=False, raw=raw)
        first = raw.splitlines()[0].strip()
        obj = json.loads(first if first.endswith("}") else raw)
        if not isinstance(obj, dict) or "action" not in obj:
            return ActionVerdict(is_action=False, raw=raw)
        return ActionVerdict(is_action=True, raw=raw, action=obj)
    except Exception as e:
        # 分类失败 → 落回主智能体(它会完整处理),不报错
        return ActionVerdict(is_action=False, error=str(e))


if __name__ == "__main__":
    # 自测: python action_classifier.py "检测pH平稳异常"
    import time
    t0 = time.time()
    v = classify_action(" ".join(sys.argv[1:]) or "检测pH平稳异常")
    dt = time.time() - t0
    print(f"分类耗时 {dt:.2f}s | is_action={v.is_action} | {v.raw[:120]}")
    if v.is_action:
        print("action:", v.action)

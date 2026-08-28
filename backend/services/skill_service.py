# backend/services/skill_service.py
"""技能管理：发现/读写 SKILL.md/新建/禁用启用/市场安装/删除。

- 技能 = skills/<name>/SKILL.md（frontmatter name/description + 正文）+ scripts/。
- 归属：master → <root>/skills/；子智能体 → <root>/subagents/<dir>/skills/。
- 禁用 = 目录名加 .disabled 后缀；本服务发现层跳过 .disabled 结尾目录（hermes 上游
  EXCLUDED_SKILL_DIRS 无此后缀规则，改名后 hermes 仍可能看到带后缀路径——主智能体
  技能清单来自本服务+SKILL.md 指引，实际不可见；彻底屏蔽属 upstream patch，不在本期）。
- 写操作全部走 git 快照（只 add 目标路径，学 identity_files 的模式）。
- 路径一律在调用时经 PROJECT_ROOT 拼接（含模板库），测试 monkeypatch 后全部生效。
"""
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# entity → (父目录相对路径, 展示名)。master 的父目录为 ""（Path/"" 折叠，
# _skills_base 统一拼 /skills 即项目根 skills/）。
ENTITY_SKILLS_DIR = {
    "master": ("", "主智能体"),
    "multi-dimensional-data-perception": ("subagents/multi-dimensional-data-perception-agent", "数据感知"),
    "anomaly-detection": ("subagents/anomaly-detection-agent", "异常检测"),
    "rule-reasoning": ("subagents/rule-reasoning-agent", "规则推理"),
    "disposition-execution": ("subagents/disposition-execution-agent", "处置执行"),
}

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _skills_base(entity: str) -> Path:
    if entity not in ENTITY_SKILLS_DIR:
        raise ValueError(f"未知实体: {entity}")
    return PROJECT_ROOT / ENTITY_SKILLS_DIR[entity][0] / "skills"


def _template_dir() -> Path:
    """模板库路径（调用时求值，随 PROJECT_ROOT 走）。"""
    return PROJECT_ROOT / "shared" / "skill_templates"


def _parse_frontmatter(text: str):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, text[m.end():]


def list_skills(entity: str) -> list:
    base = _skills_base(entity)
    out = []
    try:
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name.endswith(".disabled"):
                continue
            sk = d / "SKILL.md"
            if not sk.exists():
                continue
            meta, _ = _parse_frontmatter(sk.read_text(encoding="utf-8"))
            scripts = [p.name for p in (d / "scripts").glob("*.py")] if (d / "scripts").is_dir() else []
            out.append({"name": d.name,
                        "display_name": meta.get("name", d.name),
                        "description": meta.get("description", ""),
                        "scripts": scripts, "enabled": True})
    except FileNotFoundError:
        pass
    return out


def read_skill_md(entity: str, name: str) -> dict:
    p = _skills_base(entity) / name / "SKILL.md"
    if _NAME_RE.match(name) is None or not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    st = p.stat()
    return {"path": p.relative_to(PROJECT_ROOT).as_posix(),
            "content": p.read_text(encoding="utf-8"),
            "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def save_skill_md(entity: str, name: str, content: str, message: str = "") -> dict:
    p = _skills_base(entity) / name / "SKILL.md"
    if _NAME_RE.match(name) is None or not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    c = _git(["commit", "-m", f"config(web): {rel} — {message or '技能编辑'}", "--", rel])
    if c.returncode != 0:
        return {"commit": None, "degraded": True, "detail": (c.stderr or c.stdout).strip()[:200]}
    h = _git(["rev-parse", "--short", "HEAD"])
    return {"commit": h.stdout.strip() if h.returncode == 0 else None, "degraded": False}


_SKELETONS = {
    "empty": '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: 技能脚本说明（做什么、输入输出、写哪个结果文件）。"""
import json
import sys
from pathlib import Path

RESULT_FILE = Path(__file__).resolve().parents[2] / "skill_result.json"


def main() -> int:
    result = {"status": "completed", "data": {}}
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": "完成"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "argparse": '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: 技能脚本说明。参数示例：main.py --plant 当阳市金桥污水处理厂一期 --hours 24"""
import argparse
import json
import sys
from pathlib import Path

RESULT_FILE = Path(__file__).resolve().parents[2] / "skill_result.json"


def parse_args():
    ap = argparse.ArgumentParser(description="TODO")
    ap.add_argument("--plant", default="", help="厂区 plant_id（全称）")
    ap.add_argument("--hours", type=int, default=24, help="时间窗（小时）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    result = {"status": "completed", "params": vars(args), "data": {}}
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": "完成"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
}


def create_skill(entity: str, name: str, description: str, skeleton: str = "empty") -> dict:
    if _NAME_RE.match(name) is None:
        raise ValueError(f"技能名只允许 [a-z0-9-]（小写字母/数字/连字符）: {name}")
    base = _skills_base(entity)
    target = base / name
    if target.exists() or (base / f"{name}.disabled").exists():
        raise ValueError(f"技能已存在: {name}")
    (target / "scripts").mkdir(parents=True)
    (target / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\n"
        f"## 你做什么\n\nTODO: 写清楚这个技能做什么、什么时候用。\n\n"
        f"## 怎么调\n\n```bash\n\"E:/project/Ecological_env/ecological_env/Scripts/python.exe\" "
        f"\"$HERMES_HOME/{target.relative_to(PROJECT_ROOT).as_posix()}/scripts/main.py\" --help\n```\n\n"
        f"TODO: 写清楚参数与结果文件。\n",
        encoding="utf-8")
    (target / "scripts" / "main.py").write_text(_SKELETONS.get(skeleton, _SKELETONS["empty"]),
                                                encoding="utf-8")
    rel = target.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"feat(skills): 新建技能 {rel}", "--", rel])
    return {"name": name, "path": rel}


def disable_skill(entity: str, name: str) -> None:
    d = _skills_base(entity) / name
    if not d.is_dir():
        raise FileNotFoundError(f"技能不存在: {name}")
    d.rename(d.with_name(name + ".disabled"))
    _snapshot_dir(entity, name + ".disabled")


def enable_skill(entity: str, name: str) -> None:
    d = _skills_base(entity) / f"{name}.disabled"
    if not d.is_dir():
        raise FileNotFoundError(f"未找到被禁用的技能: {name}")
    d.rename(d.with_name(name))
    _snapshot_dir(entity, name)


def delete_skill(entity: str, name: str) -> None:
    for suffix in (name, f"{name}.disabled"):
        d = _skills_base(entity) / suffix
        if d.is_dir():
            _snapshot_dir(entity, suffix)
            shutil.rmtree(d)
            return
    raise FileNotFoundError(f"技能不存在: {name}")


def list_templates() -> list:
    out = []
    try:
        for d in sorted(_template_dir().iterdir()):
            sk = d / "SKILL.md"
            if d.is_dir() and sk.exists():
                meta, _ = _parse_frontmatter(sk.read_text(encoding="utf-8"))
                out.append({"name": d.name,
                            "description": meta.get("description", ""),
                            "has_scripts": (d / "scripts").is_dir()})
    except FileNotFoundError:
        pass
    return out


def install_template(template: str, entity: str) -> dict:
    src = _template_dir() / template
    if not src.is_dir():
        raise FileNotFoundError(f"模板不存在: {template}")
    base = _skills_base(entity)
    target = base / template
    if target.exists() or (base / f"{template}.disabled").exists():
        raise FileExistsError(f"技能已存在: {template}")
    shutil.copytree(src, target)
    rel = target.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"feat(skills): 从市场安装 {rel}", "--", rel])
    return {"ok": True, "skill": template, "path": rel}


def _snapshot_dir(entity: str, dirname: str) -> None:
    rel = (_skills_base(entity) / dirname).relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "--", rel])
    _git(["commit", "-m", f"config(skills): {rel}", "--", rel])


def _git(args: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git"] + args, cwd=PROJECT_ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args=["git"] + args, returncode=127, stdout="",
                                           stderr=str(exc)[:200])

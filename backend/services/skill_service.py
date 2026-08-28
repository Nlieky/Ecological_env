# backend/services/skill_service.py
"""技能管理：发现/读写 SKILL.md/新建/禁用启用/市场安装/删除。

- 技能 = skills/<name>/SKILL.md（frontmatter name/description + 正文）+ scripts/。
- 归属：master → <root>/skills/；子智能体 → <root>/subagents/<dir>/skills/。
- 禁用 = 目录名加 .disabled 后缀；本服务发现层跳过 .disabled 结尾目录（hermes 上游
  EXCLUDED_SKILL_DIRS 无此后缀规则，改名后 hermes 仍可能看到带后缀路径——主智能体
  技能清单来自本服务+SKILL.md 指引，实际不可见；彻底屏蔽属 upstream patch，不在本期）。
- 安全：所有落盘入口（读/写/建/禁用/启用/删除/安装）一律先 _validate_name——
  fullmatch 拒绝 ".."/大写/下划线/尾换行等，杜绝路径穿越删任意目录。
- 写操作全部走 git 快照（只 add 目标路径，学 identity_files 的模式）：
  rename/rmtree 先落盘，再 git add -A -- 旧路径 新路径（-A 才会暂存旧路径的删除），
  保证快照后 git status 干净、不留未暂存 D。
- 路径一律在调用时经 PROJECT_ROOT 拼接（含模板库），测试 monkeypatch 后全部生效。
"""
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# entity → 父目录相对路径。master 为 ""（Path/"" 折叠，_skills_base 统一拼 /skills 即项目根 skills/）。
ENTITY_SKILLS_DIR = {
    "master": "",
    "multi-dimensional-data-perception": "subagents/multi-dimensional-data-perception-agent",
    "anomaly-detection": "subagents/anomaly-detection-agent",
    "rule-reasoning": "subagents/rule-reasoning-agent",
    "disposition-execution": "subagents/disposition-execution-agent",
}

# fullmatch 而非 match+$：`$` 会放过尾换行（"abc\n"），且 match 不要求吃满整串。
_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

# 并发 save 串行化：写盘+add→commit→rev-parse 不是原子的，两个请求交错会产生
# "nothing to commit"（改动被对方 commit 带走）→ 误报 degraded。锁住整个写+git 段。
_save_lock = threading.Lock()


def _validate_name(name: str) -> str:
    """技能/模板名校验：小写字母/数字/连字符，且必须整串匹配（防路径穿越）。"""
    if not isinstance(name, str) or _NAME_RE.fullmatch(name) is None:
        raise ValueError(f"非法名字(只允许小写字母/数字/连字符): {name!r}")
    return name


def _skills_base(entity: str) -> Path:
    if entity not in ENTITY_SKILLS_DIR:
        raise ValueError(f"未知实体: {entity}")
    return PROJECT_ROOT / ENTITY_SKILLS_DIR[entity] / "skills"


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
    _validate_name(name)
    p = _skills_base(entity) / name / "SKILL.md"
    if not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    st = p.stat()
    return {"path": p.relative_to(PROJECT_ROOT).as_posix(),
            "content": p.read_text(encoding="utf-8"),
            "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def save_skill_md(entity: str, name: str, content: str, message: str = "") -> dict:
    """原子写（tmp+rename）+ git 快照（只 add 本文件）。

    - 内容未变：跳过写盘与 git，返回 no_change=True（否则 "nothing to commit" 会被
      误判为失败 → 误导性 degraded）。学 identity_files.save_file 的两个既有修复。
    """
    _validate_name(name)
    p = _skills_base(entity) / name / "SKILL.md"
    if not p.exists():
        raise FileNotFoundError(f"技能不存在: {entity}/{name}")
    if p.read_text(encoding="utf-8") == content:
        return {"commit": None, "degraded": False, "no_change": True}
    with _save_lock:
        tmp = p.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(p)
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        _git(["add", "-A", "--", rel])
        c = _git(["commit", "-m", f"config(web): {rel} — {message or '技能编辑'}", "--", rel])
        if c.returncode != 0:
            return {"commit": None, "degraded": True, "no_change": False,
                    "detail": (c.stderr or c.stdout).strip()[:200]}
        h = _git(["rev-parse", "--short", "HEAD"])
    return {"commit": h.stdout.strip() if h.returncode == 0 else None,
            "degraded": False, "no_change": False}


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
    _validate_name(name)
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
    _git(["add", "-A", "--", rel])
    c = _git(["commit", "-m", f"feat(skills): 新建技能 {rel}", "--", rel])
    return {"name": name, "path": rel, "degraded": c.returncode != 0}


def disable_skill(entity: str, name: str) -> None:
    _validate_name(name)
    base = _skills_base(entity)
    d = base / name
    if not d.is_dir():
        raise FileNotFoundError(f"技能不存在: {name}")
    twin = base / f"{name}.disabled"
    if twin.exists():
        raise FileExistsError(f"禁用目标已存在: {twin.name}（先处理该目录再禁用）")
    d.rename(twin)
    # -A + 新旧两个路径：旧路径的删除才会被暂存，否则 git status 留 D
    _snapshot_dir(entity, name, name + ".disabled")


def enable_skill(entity: str, name: str) -> None:
    _validate_name(name)
    base = _skills_base(entity)
    d = base / f"{name}.disabled"
    if not d.is_dir():
        raise FileNotFoundError(f"未找到被禁用的技能: {name}")
    twin = base / name
    if twin.exists():
        raise FileExistsError(f"启用目标已存在: {twin.name}（先处理该目录再启用）")
    d.rename(twin)
    _snapshot_dir(entity, name + ".disabled", name)


def delete_skill(entity: str, name: str) -> None:
    _validate_name(name)
    for suffix in (name, f"{name}.disabled"):
        d = _skills_base(entity) / suffix
        if d.is_dir():
            shutil.rmtree(d)                    # 先删：add -A 对已删路径会暂存删除
            _snapshot_dir(entity, suffix)
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
    _validate_name(template)
    src = _template_dir() / template
    if not src.is_dir():
        raise FileNotFoundError(f"模板不存在: {template}")
    base = _skills_base(entity)
    target = base / template
    if target.exists() or (base / f"{template}.disabled").exists():
        raise FileExistsError(f"技能已存在: {template}")
    shutil.copytree(src, target)
    rel = target.relative_to(PROJECT_ROOT).as_posix()
    _git(["add", "-A", "--", rel])
    c = _git(["commit", "-m", f"feat(skills): 从市场安装 {rel}", "--", rel])
    return {"ok": True, "skill": template, "path": rel, "degraded": c.returncode != 0}


def _snapshot_dir(entity: str, *dirnames: str) -> None:
    """目录级快照：add -A（含删除暂存）+ commit，路径限定在传入的目录内。"""
    rels = [(_skills_base(entity) / d).relative_to(PROJECT_ROOT).as_posix() for d in dirnames]
    _git(["add", "-A", "--"] + rels)
    _git(["commit", "-m", f"config(skills): {' '.join(rels)}", "--"] + rels)


def _git(args: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git"] + args, cwd=PROJECT_ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args=["git"] + args, returncode=127, stdout="",
                                           stderr=str(exc)[:200])

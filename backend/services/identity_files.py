# backend/services/identity_files.py
"""身份文件管理：白名单读 + 原子写 + git 快照/历史/回滚。

安全边界（spec §3.5）：ENTITY_FILES 白名单硬编码——entity/file 不在表内直接 PermissionError，
杜绝路径穿越读 .env。git 只 add 目标文件，绝不碰工作区其他未提交改动。
git 不可用时降级 .bak（同目录 backups/，保最近 10 份）——测试与生产同一路径。
"""
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENTITY_META = {
    "master": {"label": "主智能体", "icon": "🧠", "dir": "workspace"},
    "multi-dimensional-data-perception": {"label": "多维数据感知", "icon": "📊",
        "dir": "subagents/multi-dimensional-data-perception-agent"},
    "anomaly-detection": {"label": "异常检测", "icon": "🔍",
        "dir": "subagents/anomaly-detection-agent"},
    "rule-reasoning": {"label": "规则推理", "icon": "⚖️",
        "dir": "subagents/rule-reasoning-agent"},
    "disposition-execution": {"label": "研判预警与处置", "icon": "🚨",
        "dir": "subagents/disposition-execution-agent"},
}

# 主智能体 7 个 / 子智能体各 3 个（与身份加载器实际加载的一致）
ENTITY_FILES = {
    "master": ["IDENTITY.md", "SOUL.md", "AGENTS.md", "MEMORY.md", "USER.md", "TOOLS.md", "HEARTBEAT.md"],
    "multi-dimensional-data-perception": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "anomaly-detection": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "rule-reasoning": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
    "disposition-execution": ["SOUL.md", "AGENTS.md", "MEMORY.md"],
}


def _resolve(entity: str, file: str) -> Path:
    """白名单校验 + 绝对路径。任何不认识的一律 PermissionError。"""
    if entity not in ENTITY_FILES or file not in ENTITY_FILES[entity]:
        raise PermissionError(f"不允许的 entity/file: {entity}/{file}")
    p = (PROJECT_ROOT / ENTITY_META[entity]["dir"] / file).resolve()
    root = PROJECT_ROOT.resolve()
    if root not in p.parents:
        raise PermissionError(f"路径越界: {p}")
    return p


def list_entities() -> list:
    """实体清单（含技能只读发现：skills/*/SKILL.md）。"""
    out = []
    for name, meta in ENTITY_META.items():
        skills = []
        if name == "master":
            base = PROJECT_ROOT / "skills"
        else:
            base = PROJECT_ROOT / meta["dir"] / "skills"
        try:
            for d in base.iterdir():
                sk = d / "SKILL.md"
                if d.is_dir() and sk.exists():
                    skills.append({"name": d.name, "has_skill": True})
        except Exception:
            pass
        out.append({"name": name, "label": meta["label"], "icon": meta["icon"],
                    "dir": meta["dir"], "identity_files": ENTITY_FILES[name],
                    "skills": skills})
    return out


def read_file(entity: str, file: str) -> dict:
    p = _resolve(entity, file)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    st = p.stat()
    return {"path": p.relative_to(PROJECT_ROOT).as_posix(), "content": p.read_text(encoding="utf-8"),
            "size": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def _git(args: list, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd or PROJECT_ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=30)


def _backup_degraded(p: Path):
    """git 不可用时的降级备份：backups/ 下带时间戳副本，保最近 10 份。"""
    bdir = p.parent / "backups"
    bdir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(p, bdir / f"{p.stem}.{stamp}.bak")
    baks = sorted(bdir.glob(f"{p.stem}.*.bak"))
    for old in baks[:-10]:
        old.unlink()


def save_file(entity: str, file: str, content: str, message: str = "") -> dict:
    """原子写（tmp+rename）+ git 快照（只 add 本文件）。"""
    p = _resolve(entity, file)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)  # 原子替换
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    msg = f"config(web): {rel} — {message or '在线编辑'}"
    r = _git(["add", "--", rel])
    c = _git(["commit", "-m", msg, "--", rel])
    if c.returncode != 0:
        _backup_degraded(p)
        return {"commit": None, "degraded": True, "detail": (c.stderr or c.stdout).strip()[:200]}
    h = _git(["rev-parse", "--short", "HEAD"])
    return {"commit": h.stdout.strip() if h.returncode == 0 else None, "degraded": False}


def list_history(entity: str, file: str, limit: int = 20) -> list:
    p = _resolve(entity, file)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    r = _git(["log", f"-{limit}", "--pretty=format:%h|%ad|%an|%s", "--date=iso-strict", "--", rel])
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            out.append({"commit": parts[0], "date": parts[1], "author": parts[2], "message": parts[3]})
    return out


def revert_file(entity: str, file: str, commit: str) -> dict:
    """git checkout <commit> -- <file>：只动这一个文件。"""
    p = _resolve(entity, file)
    rel = p.relative_to(PROJECT_ROOT).as_posix()
    if not all(ch in "0123456789abcdefABCDEF" for ch in commit) or not (4 <= len(commit) <= 42):
        raise ValueError(f"非法 commit hash: {commit}")
    r = _git(["checkout", commit, "--", rel])
    if r.returncode != 0:
        raise RuntimeError(f"回滚失败: {r.stderr.strip()[:200]}")
    return read_file(entity, file)

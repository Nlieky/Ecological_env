# backend/services/skill_hub_service.py
"""技能外部市场：接 hermes 原生 Skills Hub（skills.sh 2万+目录 + GitHub 官方源）。

只做三件事：
  search(query)          多源搜索（skills.sh 优先，GitHub 官方 taps 兜底）
  fetch_bundle(identifier) 下载技能包（SkillBundle）
  install(identifier, entity) 装到指定实体技能目录（文件落盘 + git 快照）

信任分级透传给前端展示（community/trusted）；安装不做 quarantine 全套扫描
（那是 hermes CLI 的交互流程），但拒绝 bundle 里没有 SKILL.md 的包。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_HERMES_ROOT = PROJECT_ROOT / "shared" / "framework" / "hermes-agent"

# 与 skill_service 一致的实体→技能目录映射
ENTITY_SKILLS_DIR = {
    "master": "skills",
    "multi-dimensional-data-perception": "subagents/multi-dimensional-data-perception-agent/skills",
    "anomaly-detection": "subagents/anomaly-detection-agent/skills",
    "rule-reasoning": "subagents/rule-reasoning-agent/skills",
    "disposition-execution": "subagents/disposition-execution-agent/skills",
}

_sources = None   # 惰性：import hermes 链较重


def _get_sources():
    global _sources
    if _sources is None:
        import sys
        if str(_HERMES_ROOT) not in sys.path:
            sys.path.insert(0, str(_HERMES_ROOT))
        from tools.skills_hub import SkillsShSource, GitHubSource, GitHubAuth
        auth = GitHubAuth()
        _sources = {
            "skills-sh": SkillsShSource(auth=auth),      # 2万+目录站,社区信任
            "github": GitHubSource(auth=auth),           # openai/anthropics/hf/nvidia 官方 taps
        }
    return _sources


def search(query: str, limit: int = 12) -> list:
    """多源搜索，返回前端友好的 dict 列表（去重：同名优先 trusted/官方源）。"""
    out, seen = [], {}
    for src_id, src in _get_sources().items():
        try:
            for m in src.search(query, limit=limit):
                name = m.name
                trust_rank = {"builtin": 3, "trusted": 2, "community": 1}.get(m.trust_level, 0)
                prev = seen.get(name)
                item = {
                    "name": name,
                    "description": (m.description or "")[:200],
                    "source": m.source or src_id,
                    "identifier": m.identifier,
                    "trust_level": m.trust_level,
                    "repo": m.repo,
                }
                if prev is None or trust_rank > prev[0]:
                    if prev is not None:
                        out.remove(prev[1])
                    seen[name] = (trust_rank, item)
                    out.append(item)
                if len(out) >= limit * 2:
                    break
        except Exception as e:
            logger.warning("skill hub 源 %s 搜索失败: %s", src_id, e)
            continue
    return out[:limit]


def fetch_bundle(identifier: str):
    """identifier → SkillBundle；源前缀（skills-sh/… github:…）路由到对应 source。

    先走 hermes 源（GitHub Contents API）；限流/失败时兜底 _fetch_by_clone
    （git 协议直连，完全不走 API、无 60 次/时限制）。"""
    for src_id, src in _get_sources().items():
        if identifier.startswith(f"{src_id}/"):
            b = src.fetch(identifier)
            if b is not None and getattr(b, "files", None):
                return b
            return _fetch_by_clone(identifier)
    # 无前缀：两个源都试
    for src in _get_sources().values():
        b = src.fetch(identifier)
        if b is not None and getattr(b, "files", None):
            return b
    return _fetch_by_clone(identifier)


def _fetch_by_clone(identifier: str):
    """git clone --depth 1 兜底下载：绕开 GitHub API 匿名限流（60 次/时极易耗尽）。

    identifier 形如 skills-sh/<owner>/<repo>/<skill> 或 <owner>/<repo>/<skill>——
    克隆整个 repo 到临时目录，从中抽出技能目录（尝试 repo 内多处约定位置），
    打包成与 SkillBundle 同结构的 SimpleNamespace 返回。"""
    import re as _re
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf
    from types import SimpleNamespace
    m = _re.search(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", identifier.strip("/"))
    if not m:
        return None
    owner, repo, skill = m.group(1), m.group(2), m.group(3)
    if owner in ("skills-sh", "github"):   # 源前缀占了第一段时重新匹配
        m2 = _re.search(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", identifier.strip("/"))
        if not m2:
            return None
        owner, repo, skill = m2.group(1), m2.group(2), m2.group(3)
    tmp = _tf.mkdtemp(prefix="skill_clone_")
    try:
        r = _sp.run(["git", "clone", "--depth", "1", f"https://github.com/{owner}/{repo}.git", tmp],
                    capture_output=True, timeout=120)
        if r.returncode != 0:
            logger.warning("clone 兜底失败 %s/%s: %s", owner, repo, (r.stderr or b"").decode("utf-8", "replace")[:150])
            return None
        # 在克隆里找技能目录（各 repo 约定位置不同，逐个试）
        candidates = [
            f"{skill}", f"skills/{skill}", f".agents/skills/{skill}", f".claude/skills/{skill}",
        ]
        src_dir = None
        for c in candidates:
            p = Path(tmp) / c
            if (p / "SKILL.md").is_file():
                src_dir = p
                break
        if src_dir is None:
            return None
        files = []
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(src_dir).as_posix()
                try:
                    files.append(SimpleNamespace(path=rel, content=f.read_bytes()))
                except Exception:
                    continue
        return SimpleNamespace(name=skill, files=files, source=f"github-clone:{owner}/{repo}",
                               identifier=identifier, trust_level="community", metadata={})
    finally:
        _shutil.rmtree(tmp, ignore_errors=True)


def install(identifier: str, entity: str) -> dict:
    """下载 bundle → 校验（必须有 SKILL.md+非空 + 名字合法 + 不与现有冲突）→ 落盘 + git 快照。"""
    import re
    import subprocess
    import shutil
    if entity not in ENTITY_SKILLS_DIR:
        raise ValueError(f"未知实体: {entity}")
    bundle = fetch_bundle(identifier)
    if bundle is None:
        raise FileNotFoundError(f"技能包下载失败: {identifier}")
    name = bundle.name or identifier.rstrip("/").split("/")[-1]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name or ""):
        raise ValueError(f"技能名不合法（只允许小写字母/数字/连字符）: {name}")
    files = list(getattr(bundle, "files", None) or [])
    skill_md = next((f for f in files if str(getattr(f, "path", f)).split("/")[0] == "SKILL.md"
                     or str(getattr(f, "path", f)) == "SKILL.md"), None)
    # 校验收紧：SKILL.md 存在【且内容非空】——空 bundle 会装出空目录
    # (2026-09-01 实测:GitHub 限流时 fetch 返回 files=[] 的假成功,装出 0 文件目录)
    md_content = getattr(skill_md, "content", None) if skill_md is not None else None
    if skill_md is None or not md_content:
        raise ValueError("技能包里没有有效的 SKILL.md（下载不完整或非合法技能），拒绝安装")
    base = PROJECT_ROOT / ENTITY_SKILLS_DIR[entity]
    target = base / name
    if target.exists() or (base / f"{name}.disabled").exists():
        raise FileExistsError(f"技能已存在: {name}")
    target.mkdir(parents=True)
    written = 0
    try:
        for f in files:
            rel = str(getattr(f, "path", f))
            content = getattr(f, "content", None)
            if content is None:
                continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                dest.write_bytes(content)
            else:
                dest.write_text(str(content), encoding="utf-8")
            written += 1
        if written == 0:
            raise ValueError("零文件写入（下载内容为空）")
    except Exception:
        shutil.rmtree(target, ignore_errors=True)   # 半成品不留
        raise
    rel_root = target.relative_to(PROJECT_ROOT).as_posix()
    subprocess.run(["git", "add", "--", rel_root], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
    c = subprocess.run(["git", "commit", "-m", f"feat(skills): 外部市场安装 {rel_root} ({bundle.source})",
                        "--", rel_root], cwd=PROJECT_ROOT, capture_output=True, timeout=30)
    return {"ok": True, "name": name, "path": rel_root,
            "trust_level": bundle.trust_level, "source": bundle.source,
            "degraded": c.returncode != 0}

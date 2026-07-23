#!/usr/bin/env python3
"""把 hermes-agent 运行时 vendor 进项目 shared/framework/hermes-agent/。

用法:
    python scripts/vendor_hermes.py [--src D:\\Hermes\\hermes-agent]

步骤:
1. 从 src 拷运行时 Python 到 dst（排除 docs/tests/web/node_modules 等非运行时）。
2. 用 shared/framework/hermes-overlays/ 里的文件覆盖（小定制 + 修正版 orchestrator_tool）。

dst 整体被 .gitignore；本脚本 + overlays 进 git，保证可复现。
"""
import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DST = REPO / "shared" / "framework" / "hermes-agent"
OVERLAYS = REPO / "shared" / "framework" / "hermes-overlays"

# 非运行时目录/文件（拷贝时排除）
EXCLUDE_DIRS = {
    "docs", "tests", "web", "website", "ui-tui", "tui_gateway", "node_modules",
    "venv", "locales", "docker", "packaging", "assets", "infographic",
    "datagen-config-examples", "optional-mcps", "optional-skills", "apps",
    "scripts", "plans", "__pycache__", ".git", ".github",
}
EXCLUDE_SUFFIXES = (".egg-info",)
# 安全：绝不把源树里的密钥/凭证文件拷进 vendored 树（曾发生过把 D:\Hermes 的
# LongCat .env 一起 vendor 进来、密钥散落在项目里的事故）。
EXCLUDE_FILES = {".gitignore", ".gitattributes", ".env", ".env.local", "auth.json"}


def _make_ignore(src_resolved: Path):
    """EXCLUDE_DIRS 只在顶层(src 直接子项)生效，避免误删嵌套同名运行时目录
    （如 plugins/web、plugins/*/scripts）。__pycache__/.pyc/.egg-info 全层级排除。"""
    def _ignore(directory, names):
        at_top = Path(directory).resolve() == src_resolved
        ignored = set()
        for n in names:
            p = Path(directory) / n
            if at_top and n in EXCLUDE_DIRS:
                ignored.add(n)
            elif n == "__pycache__" or n.endswith(".pyc"):
                ignored.add(n)
            elif n in EXCLUDE_FILES:
                ignored.add(n)
            elif p.is_dir() and any(n.endswith(s) for s in EXCLUDE_SUFFIXES):
                ignored.add(n)
        return ignored
    return _ignore


def copy_runtime(src: Path) -> None:
    if DST.exists():
        shutil.rmtree(DST)
    print(f"[vendor] copying {src} -> {DST}")
    shutil.copytree(src, DST, ignore=_make_ignore(src.resolve()), dirs_exist_ok=False)
    print(f"[vendor] copied runtime (top-level excluded: {len(EXCLUDE_DIRS)} dir patterns)")


def apply_overlays() -> int:
    if not OVERLAYS.exists():
        print("[vendor] no overlays dir; skipping")
        return 0
    n = 0
    for p in OVERLAYS.rglob("*"):
        if not p.is_file():
            continue
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        rel = p.relative_to(OVERLAYS)
        target = DST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
        print(f"[vendor] overlay: {rel}")
    return n


# 对 vendored 文件的小修正（避免为单行改动而把整文件复制进 overlay 锁死上游更新）。
# 每个 entry: (相对路径, 原文片段, 新文片段)，首次匹配替换；未匹配则告警。
PATCHES = [
    # 内网部署连不上 openrouter.ai，fetch_model_metadata 同步拉取会阻塞启动 ~12s。
    # context_length 已由本地 vLLM 的 /v1/models(portal) 提供，OpenRouter fallback 仅作降级。
    ("agent/model_metadata.py",
     "requests.get(OPENROUTER_MODELS_URL, timeout=10,",
     "requests.get(OPENROUTER_MODELS_URL, timeout=1,  # 10→1: 内网不可达 openrouter.ai"),
     ),
    # 定制：原生 system_prompt 只读 SOUL.md；这里在 SOUL 加载后接一段，按 _identity_path
    # (主智能体) 或 HERMES_HOME (子智能体) 加载目录里实际存在的身份文件——主智能体 7 个、
    # 子智能体 3 个。加载器在 shared/framework/hermes_agent/agent/identity_loader.py。
    ("agent/system_prompt.py",
     "    if not _soul_loaded:\n        # Fallback to hardcoded identity\n        stable_parts.append(DEFAULT_AGENT_IDENTITY)",
     "    if not _soul_loaded:\n        # Fallback to hardcoded identity\n        stable_parts.append(DEFAULT_AGENT_IDENTITY)\n\n"
     "    # ── 定制：加载自定义路径下的全部身份文件（原生仅读 SOUL.md）────────────\n"
     "    # 主智能体经 identity_path=workspace → agent._identity_path；子智能体经 HERMES_HOME\n"
     "    # 指向各自目录。加载器按目录里实际存在的文件读 → 主智能体 7 个、子智能体 3 个自然区分。\n"
     "    try:\n"
     "        import os as _os\n"
     "        from pathlib import Path as _Path\n"
     "        _id_path = getattr(agent, '_identity_path', None)\n"
     "        if not _id_path and _os.environ.get('HERMES_HOME'):\n"
     "            _id_path = _Path(_os.environ['HERMES_HOME'])\n"
     "        if _id_path:\n"
     "            from shared.framework.hermes_agent.agent.identity_loader import load_identity_files_from_path\n"
     "            _id_content = load_identity_files_from_path(_id_path)\n"
     "            if _id_content:\n"
     "                stable_parts.append(_id_content)\n"
     "    except Exception:\n        pass"),
]


def apply_patches() -> int:
    n = 0
    for rel, old, new in PATCHES:
        f = DST / rel
        if not f.exists():
            print(f"[vendor] patch skip (file missing): {rel}")
            continue
        text = f.read_text(encoding="utf-8")
        if old not in text:
            print(f"[vendor] ⚠ patch no-match (上游可能已改写法): {rel}")
            continue
        f.write_text(text.replace(old, new, 1), encoding="utf-8")
        n += 1
        print(f"[vendor] patch: {rel}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"D:\Hermes\hermes-agent", help="hermes-agent 源目录")
    args = ap.parse_args()
    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"source not found: {src}")
    copy_runtime(src)
    n = apply_overlays()
    np = apply_patches()
    print(f"[vendor] done. overlays applied: {n}, patches applied: {np}. vendored at {DST}")


if __name__ == "__main__":
    main()

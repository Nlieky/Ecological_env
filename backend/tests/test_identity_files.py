# backend/tests/test_identity_files.py
"""identity_files 单测：白名单拦截 / 读文件 / 保存+git快照 / 历史 / 回滚。
在临时 git 仓库副本上跑（subprocess git init + 拷真实 workspace 一份），不碰真仓库。"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """临时 git 仓库 + 真实 workspace/subagents 拷贝，monkeypatch PROJECT_ROOT。"""
    src = PROJECT_ROOT / "workspace"
    shutil.copytree(src, tmp_path / "workspace")
    shutil.copytree(PROJECT_ROOT / "subagents", tmp_path / "subagents")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    import backend.services.identity_files as idf
    monkeypatch.setattr(idf, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_read_identity_file(repo):
    from backend.services.identity_files import read_file
    r = read_file("master", "SOUL.md")
    assert r["path"].endswith("workspace/SOUL.md")
    assert len(r["content"]) > 0 and r["size"] > 0


def test_whitelist_rejects_traversal(repo):
    from backend.services.identity_files import read_file
    with pytest.raises(PermissionError):
        read_file("master", "../../.env")


def test_whitelist_rejects_unknown_entity(repo):
    from backend.services.identity_files import read_file
    with pytest.raises(PermissionError):
        read_file("hacker", "SOUL.md")


def test_save_creates_commit(repo):
    from backend.services.identity_files import read_file, save_file, list_history
    before = read_file("master", "MEMORY.md")["content"]
    save_file("master", "MEMORY.md", before + "\n<!-- 在线编辑测试 -->", "单测快照")
    after = read_file("master", "MEMORY.md")["content"]
    assert "在线编辑测试" in after
    hist = list_history("master", "MEMORY.md", limit=5)
    assert any("单测快照" in h["message"] for h in hist)
    assert hist[0]["commit"] and len(hist[0]["commit"]) >= 7


def test_git_unavailable_degrades(repo, monkeypatch):
    """git 二进制缺失（如精简 Docker 镜像）：save 不抛异常，文件照常写盘 + 降级 .bak。"""
    import backend.services.identity_files as idf
    from backend.services.identity_files import read_file

    # 模拟 git 二进制缺失：FileNotFoundError 的真正源头是 subprocess.run
    def boom(*a, **kw):
        raise FileNotFoundError("git")

    monkeypatch.setattr(idf.subprocess, "run", boom)
    new = read_file("master", "MEMORY.md")["content"] + "\n<!-- 无 git 环境 -->"
    r = idf.save_file("master", "MEMORY.md", new, "无git保存")
    assert r["degraded"] is True and r["commit"] is None
    assert read_file("master", "MEMORY.md")["content"] == new  # 文件已写盘，不是 500
    baks = list((repo / "workspace" / "backups").glob("MEMORY.*.bak"))
    assert len(baks) == 1  # 降级备份已产生


def test_save_no_change(repo):
    """内容未变的保存：no_change=True，不产生新 commit / 不落 .bak。"""
    from backend.services.identity_files import read_file, save_file
    cur = read_file("master", "MEMORY.md")["content"]
    before = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo,
                            capture_output=True, text=True).stdout.strip()
    r = save_file("master", "MEMORY.md", cur, "无改动")
    after = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo,
                           capture_output=True, text=True).stdout.strip()
    assert r["no_change"] is True and r["degraded"] is False
    assert before == after  # git log 数量不变
    assert not (repo / "workspace" / "backups").exists()


def test_revert_restores_content(repo):
    from backend.services.identity_files import read_file, save_file, list_history, revert_file
    orig = read_file("master", "MEMORY.md")["content"]
    save_file("master", "MEMORY.md", orig + "\n<!-- 改坏 -->", "改坏的一版")
    hist = list_history("master", "MEMORY.md", limit=10)
    # 回滚到含 orig 的那个 commit（历史里最后一条非本次的）
    target = next(h for h in hist if "改坏的一版" not in h["message"])
    restored = revert_file("master", "MEMORY.md", target["commit"])
    assert "<!-- 改坏 -->" not in restored["content"]


def test_entities_listing(repo):
    from backend.services.identity_files import list_entities
    es = list_entities()
    names = [e["name"] for e in es]
    assert "master" in names and len(names) == 5
    m = next(e for e in es if e["name"] == "master")
    assert "SOUL.md" in m["identity_files"] and len(m["identity_files"]) == 7
    s = next(e for e in es if e["name"] == "anomaly-detection")
    assert s["identity_files"] == ["SOUL.md", "AGENTS.md", "MEMORY.md"]
    assert any(sk["name"] for sk in s["skills"])

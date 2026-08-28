# backend/tests/test_skill_service.py
"""skill_service 单测：发现(跳过.disabled)/frontmatter 解析/新建校验/禁用往返/市场安装/删除。
在临时目录搭 skills 树（不碰真仓库）。"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """临时项目根：skills/ + 子智能体 skills + 模板库 + git 仓库。"""
    # 拷真实 skills/（orchestrator-core 等既有技能进环境，支撑"已存在"校验用例）
    shutil.copytree(PROJECT_ROOT / "skills", tmp_path / "skills")
    shutil.copytree(PROJECT_ROOT / "subagents", tmp_path / "subagents")
    tpl = tmp_path / "shared" / "skill_templates"
    tpl.mkdir(parents=True)
    (tpl / "tpl-a").mkdir()
    (tpl / "tpl-a" / "SKILL.md").write_text(
        "---\nname: tpl-a\ndescription: 测试模板\n---\n# tpl-a\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    import backend.services.skill_service as svc
    monkeypatch.setattr(svc, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_discover_master_skills(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "my-skill", "测试技能", skeleton="empty")
    svc.create_skill("master", "off-skill", "将被禁用", skeleton="empty")
    svc.disable_skill("master", "off-skill")
    items = {s["name"]: s for s in svc.list_skills("master")}
    assert "my-skill" in items and items["my-skill"]["enabled"] is True
    assert "off-skill" not in items          # .disabled 不在发现列表
    assert items["my-skill"]["description"] == "测试技能"


def test_discover_subagent_skills(env):
    from backend.services import skill_service as svc
    svc.create_skill("anomaly-detection", "sub-skill", "子智能体技能", skeleton="empty")
    names = [s["name"] for s in svc.list_skills("anomaly-detection")]
    assert "sub-skill" in names
    assert "anomaly-detection-core" in names   # 真实拷来的既有技能仍在


def test_create_validates_name(env):
    from backend.services import skill_service as svc
    with pytest.raises(ValueError):
        svc.create_skill("master", "Bad_Name", "非法名", skeleton="empty")
    with pytest.raises(ValueError):
        svc.create_skill("master", "orchestrator-core", "已存在", skeleton="empty")


def test_create_skeleton_argparse(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "arg-skill", "带参数骨架", skeleton="argparse")
    p = env / "skills" / "arg-skill" / "scripts" / "main.py"
    assert p.exists() and "argparse" in p.read_text(encoding="utf-8")


def test_disable_enable_roundtrip(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "rt-skill", "往返", skeleton="empty")
    svc.disable_skill("master", "rt-skill")
    assert not (env / "skills" / "rt-skill" / "SKILL.md").exists()
    assert (env / "skills" / "rt-skill.disabled" / "SKILL.md").exists()
    svc.enable_skill("master", "rt-skill")
    assert (env / "skills" / "rt-skill" / "SKILL.md").exists()


def test_market_install_and_conflict(env):
    from backend.services import skill_service as svc
    r = svc.install_template("tpl-a", "master")
    assert r["ok"] is True and r["skill"] == "tpl-a"
    with pytest.raises(FileExistsError):
        svc.install_template("tpl-a", "master")   # 同名冲突不覆盖
    with pytest.raises(FileNotFoundError):
        svc.install_template("ghost-tpl", "master")


def test_delete_skill(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "del-skill", "待删", skeleton="empty")
    svc.delete_skill("master", "del-skill")
    assert not (env / "skills" / "del-skill").exists()


def _git_out(env, *args):
    return subprocess.run(["git"] + list(args), cwd=env, capture_output=True,
                          text=True, encoding="utf-8").stdout


def test_path_traversal_rejected(env):
    """名字校验必须挡住路径穿越/尾换行（delete/install 的攻击面）。"""
    from backend.services import skill_service as svc
    victim = env / "workspace"                        # 放一个诱饵目录看是否被穿越删除
    victim.mkdir()
    (victim / "SOUL.md").write_text("decoy", encoding="utf-8")
    with pytest.raises(ValueError):
        svc.delete_skill("master", "../workspace")     # 不许穿越删目录
    with pytest.raises(ValueError):
        svc.install_template("../x", "master")         # 模板名同样校验
    with pytest.raises(ValueError):
        svc.create_skill("master", "abc\n", "尾换行", skeleton="empty")
    assert (victim / "SOUL.md").exists()               # 诱饵毫发无损


def test_delete_snapshot_complete(env):
    """删除先落盘再 add -A 暂存删除：git log 有 D 记录、git status 干净。"""
    from backend.services import skill_service as svc
    svc.create_skill("master", "snap-del", "待删", skeleton="empty")
    svc.delete_skill("master", "snap-del")
    rel = "skills/snap-del"
    log = _git_out(env, "log", "--diff-filter=D", "--name-only", "--pretty=format:", "--", rel)
    assert f"{rel}/SKILL.md" in log                     # 删除被记录
    assert _git_out(env, "status", "--porcelain", "--", rel).strip() == ""  # 无残留 D


def test_disable_enable_snapshot_complete(env):
    """禁用/启用后旧路径删除+新路径都已暂存提交，git status 干净。"""
    from backend.services import skill_service as svc
    svc.create_skill("master", "snap-rt", "往返", skeleton="empty")
    svc.disable_skill("master", "snap-rt")
    both = ["skills/snap-rt", "skills/snap-rt.disabled"]
    assert _git_out(env, "status", "--porcelain", "--", *both).strip() == ""
    assert _git_out(env, "log", "--diff-filter=D", "--name-only",
                    "--pretty=format:", "--", "skills/snap-rt").strip() != ""
    svc.enable_skill("master", "snap-rt")
    assert _git_out(env, "status", "--porcelain", "--", *both).strip() == ""


def test_save_no_change_shortcircuit(env):
    from backend.services import skill_service as svc
    svc.create_skill("master", "nc-skill", "原描述", skeleton="empty")
    cur = svc.read_skill_md("master", "nc-skill")["content"]
    r = svc.save_skill_md("master", "nc-skill", cur)
    assert r.get("no_change") is True and r.get("degraded") is False


def test_disable_enable_twin_conflict(env):
    """孪生目录已存在时给出清晰 FileExistsError，且不动原目录。"""
    from backend.services import skill_service as svc
    svc.create_skill("master", "twin-a", "甲", skeleton="empty")
    (env / "skills" / "twin-a.disabled").mkdir()
    with pytest.raises(FileExistsError):
        svc.disable_skill("master", "twin-a")
    assert (env / "skills" / "twin-a" / "SKILL.md").exists()   # 原目录未被动
    svc.create_skill("master", "twin-b", "乙", skeleton="empty")
    svc.disable_skill("master", "twin-b")
    (env / "skills" / "twin-b").mkdir()                        # 启用目标已被占
    with pytest.raises(FileExistsError):
        svc.enable_skill("master", "twin-b")
    assert (env / "skills" / "twin-b.disabled" / "SKILL.md").exists()

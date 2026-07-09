"""测试主智能体身份文件加载"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_master_agent_identity_loading():
    """测试主智能体能加载所有身份文件"""
    from shared.framework.hermes_agent.hermes_constants import (
        IDENTITY_FILES,
        get_identity_files,
        get_hermes_home
    )

    # 设置 HERMES_HOME 指向主智能体目录
    os.environ['HERMES_HOME'] = str(project_root / 'workspace')

    # 检查常量定义
    assert len(IDENTITY_FILES) == 7, f"Expected 7 identity files, got {len(IDENTITY_FILES)}"
    assert "IDENTITY.md" in IDENTITY_FILES
    assert "SOUL.md" in IDENTITY_FILES
    assert "AGENTS.md" in IDENTITY_FILES
    assert "MEMORY.md" in IDENTITY_FILES
    assert "USER.md" in IDENTITY_FILES
    assert "TOOLS.md" in IDENTITY_FILES
    assert "HEARTBEAT.md" in IDENTITY_FILES

    # 检查路径解析
    hermes_home = get_hermes_home()
    assert hermes_home == project_root / 'workspace'

    # 检查身份文件路径
    identity_paths = get_identity_files()
    assert len(identity_paths) == 7
    assert all(path.is_relative_to(project_root / 'workspace') for path in identity_paths)

    # 检查文件是否存在
    existing_files = [p for p in identity_paths if p.exists()]
    print(f"Found {len(existing_files)}/{len(identity_paths)} identity files")

    # 至少 SOUL.md 必须存在
    soul_path = hermes_home / "SOUL.md"
    assert soul_path.exists(), "SOUL.md must exist"

    print("[OK] Master agent identity loading test passed")

if __name__ == "__main__":
    test_master_agent_identity_loading()

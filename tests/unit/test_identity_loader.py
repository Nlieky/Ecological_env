# tests/unit/test_identity_loader.py
"""测试身份文件加载器"""

import pytest
from pathlib import Path
from shared.framework.hermes_agent.agent.identity_loader import (
    load_identity_files_from_path,
    load_single_identity_file,
    resolve_identity_path,
    IDENTITY_FILES
)


def test_resolve_identity_path_absolute():
    """测试解析绝对路径"""
    path = resolve_identity_path("/absolute/path/to/workspace", Path("/project"))
    assert path == Path("/absolute/path/to/workspace")


def test_resolve_identity_path_relative():
    """测试解析相对路径"""
    path = resolve_identity_path("workspace", Path("/project"))
    assert path == Path("/project/workspace")


def test_resolve_identity_path_none():
    """测试解析空路径（默认workspace）"""
    path = resolve_identity_path(None, Path("/project"))
    assert path == Path("/project/workspace")


def test_load_identity_files_from_nonexistent_path():
    """测试从不存在的路径加载身份文件"""
    result = load_identity_files_from_path(Path("/nonexistent/path"))
    assert result is None


def test_load_single_identity_file(tmp_path):
    """测试加载单个身份文件"""
    # 创建测试文件
    test_file = tmp_path / "SOUL.md"
    test_file.write_text("# Test SOUL Content")

    content = load_single_identity_file(tmp_path, "SOUL.md")
    assert content == "# Test SOUL Content"


def test_load_single_identity_file_nonexistent(tmp_path):
    """测试加载不存在的身份文件"""
    content = load_single_identity_file(tmp_path, "NONEXISTENT.md")
    assert content is None


def test_load_identity_files_from_path_multiple_files(tmp_path):
    """测试从路径加载多个身份文件"""
    # 创建测试文件
    (tmp_path / "SOUL.md").write_text("# SOUL Content")
    (tmp_path / "AGENTS.md").write_text("# AGENTS Content")
    (tmp_path / "MEMORY.md").write_text("# MEMORY Content")

    result = load_identity_files_from_path(tmp_path)

    assert result is not None
    assert "## SOUL.md" in result
    assert "# SOUL Content" in result
    assert "## AGENTS.md" in result
    assert "# AGENTS Content" in result
    assert "## MEMORY.md" in result
    assert "# MEMORY Content" in result


def test_load_identity_files_empty_file(tmp_path):
    """测试加载空文件"""
    # 创建空文件
    (tmp_path / "SOUL.md").write_text("   ")
    (tmp_path / "AGENTS.md").write_text("# AGENTS Content")

    result = load_identity_files_from_path(tmp_path)

    assert result is not None
    assert "## SOUL.md" not in result  # 空文件应该被跳过
    assert "## AGENTS.md" in result
    assert "# AGENTS Content" in result


def test_identity_files_constant():
    """验证IDENTITY_FILES常量与hermes_constants一致"""
    from shared.framework.hermes_agent.hermes_constants import IDENTITY_FILES as HERMES_IDENTITY_FILES

    assert set(IDENTITY_FILES) == set(HERMES_IDENTITY_FILES)

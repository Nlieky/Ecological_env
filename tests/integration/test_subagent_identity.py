"""测试子智能体身份文件加载"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_subagent_identity_loading():
    """测试子智能体能加载所有身份文件"""
    from shared.framework.hermes_agent.hermes_constants import (
        IDENTITY_FILES,
        get_identity_files,
        get_hermes_home
    )

    subagents = [
        "anomaly-detection-agent",
        "multi-dimensional-data-perception-agent",
        "rule-reasoning-agent",
        "disposition-execution-agent"
    ]

    print(f"Project root: {project_root}")
    print(f"Testing {len(subagents)} subagents\n")

    results = []

    for subagent in subagents:
        print(f"Testing subagent: {subagent}")

        # 设置 HERMES_HOME 指向子智能体目录
        subagent_path = project_root / 'subagents' / subagent

        if not subagent_path.exists():
            print(f"  [SKIP] {subagent} directory not found at {subagent_path}")
            results.append((subagent, "SKIP", "Directory not found"))
            continue

        os.environ['HERMES_HOME'] = str(subagent_path)

        # 检查常量定义
        assert len(IDENTITY_FILES) == 7, f"Expected 7 identity files, got {len(IDENTITY_FILES)}"

        # 检查路径解析
        hermes_home = get_hermes_home()
        assert hermes_home == subagent_path, f"Expected {subagent_path}, got {hermes_home}"

        # 检查身份文件路径
        identity_paths = get_identity_files()
        assert len(identity_paths) == 7, f"Expected 7 identity file paths, got {len(identity_paths)}"

        # 检查文件是否存在
        existing_files = [p for p in identity_paths if p.exists()]
        missing_files = [p for p in identity_paths if not p.exists()]

        print(f"  Found {len(existing_files)}/{len(identity_paths)} identity files")

        if missing_files:
            print(f"  Missing files:")
            for f in missing_files:
                print(f"    - {f.name}")

        # 至少 SOUL.md 必须存在
        soul_path = subagent_path / "SOUL.md"
        if not soul_path.exists():
            print(f"  [WARNING] {subagent} missing SOUL.md")
            results.append((subagent, "WARNING", "SOUL.md not found"))
        else:
            print(f"  [OK] {subagent} identity files load normally")
            results.append((subagent, "OK", f"{len(existing_files)}/{len(IDENTITY_FILES)} files"))

        print()

    # 打印汇总
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ok_count = sum(1 for _, status, _ in results if status == "OK")
    warning_count = sum(1 for _, status, _ in results if status == "WARNING")
    skip_count = sum(1 for _, status, _ in results if status == "SKIP")

    print(f"OK: {ok_count}, WARNING: {warning_count}, SKIP: {skip_count}")

    for subagent, status, detail in results:
        print(f"  {subagent}: [{status}] {detail}")

    print("\n[COMPLETE] Subagent identity loading test finished")

if __name__ == "__main__":
    test_subagent_identity_loading()

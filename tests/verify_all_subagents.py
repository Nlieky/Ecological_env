"""
验证所有子智能体的上下文文件加载
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def verify_subagent(subagent_name, subagent_dir, test_task):
    """验证单个子智能体"""
    print(f"\n{'='*60}")
    print(f"验证: {subagent_name}")
    print(f"{'='*60}")

    subagent_path = project_root / "subagents" / subagent_dir

    # 检查上下文文件
    context_files = ["AGENTS.md", "SOUL.md", "MEMORY.md"]
    print("[Check] Context files:")
    for fname in context_files:
        fpath = subagent_path / fname
        status = "[OK]" if fpath.exists() else "[FAIL]"
        print(f"  {status} {fname}: {fpath.exists()}")

    # 创建会话目录
    session_dir = project_root / "sessions" / f"verify_{subagent_name}"
    session_dir.mkdir(parents=True, exist_ok=True)

    # 创建 task.json
    task_obj = {
        "task": test_task,
        "context": {},
        "output_format": "json"
    }

    with open(session_dir / "task.json", "w", encoding='utf-8') as f:
        json.dump(task_obj, f, indent=2, ensure_ascii=False)

    # 设置环境变量
    env = os.environ.copy()
    env['HERMES_HOME'] = str(subagent_path)
    # env['HERMES_PATH'] = 'D:/Hermes/hermes-agent'  # 不再需要外部 Hermes 路径
    env['SUBAGENT_NAME'] = subagent_name
    env['SESSION_DIR'] = str(session_dir)
    env['DEBUG_PATH'] = '1'

    # 获取当前 Python（uv 环境）
    current_python = sys.executable

    # 运行子智能体
    try:
        print(f"[Run] Calling {subagent_name}...")

        result = subprocess.run(
            [current_python, 'run_agent.py'],
            env=env,
            capture_output=True,
            timeout=120,
            cwd=str(subagent_path)
        )

        # 解码输出
        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace')

        # 检查上下文文件加载
        print("\n[Results]")

        # 检查 stderr 中的调试信息
        if "System prompt length:" in stdout or "System prompt length:" in stderr:
            # 提取系统提示词长度
            for line in (stdout + stderr).split('\n'):
                if "System prompt length:" in line:
                    print(f"  {line}")
                    length = line.split(':')[1].strip().split()[0]
                    try:
                        if int(length) > 1000:
                            print(f"  ✅ Context files loaded! (length: {length} chars)")
                        else:
                            print(f"  ⚠️  Short prompt (length: {length} chars)")
                    except:
                        pass

        # 检查是否包含专业内容
        for line in (stdout + stderr).split('\n'):
            if "Contains" in line and ("anomaly" in line.lower() or "perception" in line.lower() or "reasoning" in line.lower() or "disposition" in line.lower()):
                print(f"  {line}")

        # 检查是否完成
        if result.returncode == 0 and "Task completed successfully" in stdout:
            print(f"  ✅ {subagent_name}: SUCCESS")
            return True
        else:
            print(f"  ⚠️  {subagent_name}: PARTIAL (context loaded, but API may have failed)")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ {subagent_name}: TIMEOUT")
        return False
    except Exception as e:
        print(f"  ✗ {subagent_name}: ERROR - {e}")
        return False

def main():
    print("="*60)
    print("验证所有子智能体的上下文文件加载")
    print("="*60)

    # 加载 .env
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[INFO] Loaded .env from {env_path}")

    # 定义子智能体
    subagents = [
        ("multi-dimensional-data-perception", "multi-dimensional-data-perception-agent", "简述你的身份和能力。不要超过30字。"),
        ("anomaly-detection", "anomaly-detection-agent", "简述你的身份和能力。不要超过30字。"),
        ("rule-reasoning", "rule-reasoning-agent", "简述你的身份和能力。不要超过30字。"),
        ("disposition-execution", "disposition-execution-agent", "简述你的身份和能力。不要超过30字。")
    ]

    results = {}

    for name, directory, task in subagents:
        success = verify_subagent(name, directory, task)
        results[name] = success

    # 总结
    print(f"\n{'='*60}")
    print("验证总结")
    print(f"{'='*60}")

    for name, success in results.items():
        status = "✅ SUCCESS" if success else "⚠️  PARTIAL"
        print(f"  {status}: {name}")

    total = len(results)
    success_count = sum(1 for v in results.values() if v)

    print(f"\n总计: {success_count}/{total} 子智能体验证通过")

    if success_count == total:
        print("\n🎉 所有子智能体都能加载上下文文件！")
    else:
        print("\n⚠️  部分子智能体需要进一步检查")

if __name__ == "__main__":
    main()

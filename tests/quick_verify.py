"""
简化的子智能体验证脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("=" * 60)
    print("子智能体上下文文件加载验证（简化版）")
    print("=" * 60)

    # 加载 .env 文件
    from dotenv import load_dotenv
    env_path = Path("E:/project/Ecological_env/.env")
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[INFO] Loaded .env from {env_path}", file=sys.stderr, flush=True)
    else:
        print(f"[WARNING] .env not found at {env_path}", file=sys.stderr, flush=True)

    # 验证环境变量
    print(f"[INFO] LLM_BASE_URL: {os.environ.get('LLM_BASE_URL', 'not set')}", file=sys.stderr, flush=True)
    print(f"[INFO] LLM_MODEL: {os.environ.get('LLM_MODEL', 'not set')}", file=sys.stderr, flush=True)
    print(f"[INFO] LLM_API_KEY: {os.environ.get('LLM_API_KEY', 'not set')[:20]}...", file=sys.stderr, flush=True)

    # 子智能体路径
    subagent_path = Path("E:/project/Ecological_env/subagents/anomaly-detection-agent").resolve()

    print(f"\n[检查] 子智能体目录: {subagent_path}")
    print(f"[检查] 目录存在: {subagent_path.exists()}")

    # 检查上下文文件
    context_files = ["AGENTS.md", "SOUL.md", "MEMORY.md"]
    print("\n[Check] Context files:")
    for fname in context_files:
        fpath = subagent_path / fname
        status = "[OK]" if fpath.exists() else "[FAIL]"
        print(f"  {status} {fname}: {fpath.exists()}")

    # 尝试调用子智能体
    print("\n[测试] 调用子智能体...")
    print("-" * 60)

    # 创建环境变量字典（在 load_dotenv() 之后）
    env = os.environ.copy()
    env['HERMES_HOME'] = str(subagent_path)
    # env['HERMES_PATH'] = 'D:/Hermes/hermes-agent'  # 不再需要外部 Hermes 路径
    env['SUBAGENT_NAME'] = 'anomaly-detection'
    env['SESSION_DIR'] = str(Path("E:/project/Ecological_env/sessions/test_session"))
    env['DEBUG_PATH'] = '1'  # 启用路径调试

    # 创建会话目录
    session_dir = Path(env['SESSION_DIR'])
    session_dir.mkdir(parents=True, exist_ok=True)

    # 创建 task.json
    task_obj = {
        "task": "简述你的身份和能力。不要超过50字。",
        "context": {},
        "output_format": "json"
    }

    import json
    with open(session_dir / "task.json", "w", encoding='utf-8') as f:
        json.dump(task_obj, f, indent=2, ensure_ascii=False)

    print(f"会话目录: {session_dir}")
    print(f"任务文件: {session_dir / 'task.json'}")

    # 运行子智能体
    try:
        print("\n[执行] subprocess 调用...")

        # 检测当前 Python（应该在 uv 环境中）
        current_python = sys.executable
        print(f"[INFO] Current Python: {current_python}", file=sys.stderr, flush=True)
        print(f"[INFO] Python version: {sys.version}", file=sys.stderr, flush=True)

        # 使用二进制模式避免 Windows 编码问题
        binary_result = subprocess.run(
            [current_python, 'run_agent.py'],
            env=env,
            capture_output=True,
            timeout=120,
            cwd=str(subagent_path)
        )

        # 手动解码，忽略错误
        stdout = binary_result.stdout.decode('utf-8', errors='replace')
        stderr = binary_result.stderr.decode('utf-8', errors='replace')

        # 创建结果对象
        result = type('obj', (object,), {
            'returncode': binary_result.returncode,
            'stdout': stdout,
            'stderr': stderr
        })()

        print("\n[STDOUT]")
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

        print("\n[STDERR]")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

        print(f"\n[返回码] {result.returncode}")

        # 检查结果文件
        result_file = session_dir / "anomaly_result.json"
        if result_file.exists():
            print(f"\n[结果] 结果文件存在")
            with open(result_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            print(f"状态: {result_data.get('status')}")
            if result_data.get('result'):
                print(f"响应: {result_data['result'].get('response', 'No response')[:200]}...")
        else:
            print(f"\n[结果] 结果文件不存在")

    except subprocess.TimeoutExpired:
        print("[错误] 子智能体超时")
    except Exception as e:
        print(f"[错误] {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

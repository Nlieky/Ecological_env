#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""系统验证测试 - 简化版"""

import sys
import os
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_files():
    """检查关键文件是否存在"""
    print("=== 关键文件检查 ===")

    # 获取项目根目录
    project_root = Path(__file__).parents[1]
    files_to_check = [
        ("对话循环", "shared/framework/hermes_agent/agent/conversation_loop.py"),
        ("工具注册", "workspace/skills/orchestrator-core/scripts/tool_registration.py"),
        ("数据库配置", "backend/database/base.py"),
        ("主智能体服务", "scripts/start_agent.py"),
        ("数据库文件", "shared/data/ecological_logs.db"),
    ]

    all_exist = True
    for name, path in files_to_check:
        full_path = project_root / path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {name}: {path}")
        if not exists:
            all_exist = False

    return all_exist

def check_imports():
    """检查关键模块导入"""
    print("\n=== 模块导入检查 ===")

    try:
        # 添加项目路径
        import sys
        project_root = str(Path(__file__).parents[1])
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # 添加本地hermes框架路径
        local_hermes = str(Path(__file__).parents[1] / "shared" / "framework")
        if local_hermes not in sys.path:
            sys.path.insert(0, local_hermes)

        from hermes_agent.agent.conversation_loop import run_conversation
        print("✅ conversation_loop模块可导入")

        # 检查函数签名
        import inspect
        sig = inspect.signature(run_conversation)
        has_timeout = all(param in sig.parameters for param in ['llm_timeout', 'tool_timeout', 'total_timeout'])
        if has_timeout:
            print("✅ 超时参数已集成")
        else:
            print("⚠️ 超时参数缺失")

        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database():
    """检查数据库配置"""
    print("\n=== 数据库配置检查 ===")

    try:
        # 添加项目路径
        import sys
        project_root = str(Path(__file__).parents[1])
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from backend.database.base import DB_PATH, DATABASE_URL
        print(f"✅ 数据库路径: {DB_PATH}")

        # 检查是否在shared/data目录
        db_path_str = str(DB_PATH).replace("\\", "/")
        is_correct_location = "shared/data" in db_path_str
        if is_correct_location:
            print("✅ 数据库位置正确（符合三库一体）")
        else:
            print(f"❌ 数据库位置错误: {db_path_str}")

        # 检查文件是否存在
        db_exists = Path(DB_PATH).exists()
        if db_exists:
            print("✅ 数据库文件存在")
        else:
            print("⚠️ 数据库文件不存在（首次运行时正常）")

        return is_correct_location
    except Exception as e:
        print(f"❌ 数据库配置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_services():
    """检查服务状态"""
    print("\n=== 服务状态检查 ===")

    services = [
        ("主智能体服务", "http://localhost:8642", "/health"),
        ("后端API服务", "http://localhost:8000", "/api/health"),
    ]

    import requests
    all_running = True

    for name, base_url, health_path in services:
        try:
            response = requests.get(f"{base_url}{health_path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: 运行中")
            else:
                print(f"⚠️ {name}: 响应异常 ({response.status_code})")
                all_running = False
        except requests.exceptions.Timeout:
            print(f"⚠️ {name}: 响应超时")
            all_running = False
        except Exception as e:
            print(f"❌ {name}: 未运行 ({e})")
            all_running = False

    return all_running

def main():
    """主测试函数"""
    print("废水监测系统 - 验证测试\n")
    print("=" * 50)

    results = []
    results.append(("文件检查", check_files()))
    results.append(("模块导入", check_imports()))
    results.append(("数据库配置", check_database()))
    results.append(("服务状态", check_services()))

    print("\n" + "=" * 50)
    print("测试结果汇总：")
    passed = 0
    failed = 0

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    if failed == 0:
        print("\n✅ 系统验证通过！所有关键功能正常。")
        return 0
    else:
        print(f"\n⚠️ {failed} 项检查失败，请检查相关配置。")
        return 1

if __name__ == "__main__":
    exit(main())

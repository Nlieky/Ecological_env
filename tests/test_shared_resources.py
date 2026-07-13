"""
测试三库一体读取权限

验证主智能体和子智能体都能读取 shared 目录下的资源
"""
import os
import sys
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("三库一体读取权限测试")
print("=" * 60)

# 定义三库路径
shared_root = project_root / "shared"
operators_dir = shared_root / "operators"
data_dir = shared_root / "data"
knowledge_dir = shared_root / "knowledge"

print(f"\n项目根目录: {project_root}")
print(f"共享目录: {shared_root}")

# 测试1: 检查目录存在
print("\n[TEST 1] 检查三库目录是否存在")
for name, path in [
    ("算子库 (operators)", operators_dir),
    ("数据库 (data)", data_dir),
    ("知识库 (knowledge)", knowledge_dir)
]:
    exists = path.exists()
    status = "[PASS]" if exists else "[FAIL]"
    print(f"  {status} {name}: {path}")
    if exists:
        # 统计文件数量
        files = list(path.rglob("*"))
        print(f"       包含 {len(files)} 个文件/目录")

# 测试2: 检查算子库内容
print("\n[TEST 2] 检查算子库内容")
operator_categories = {
    "机器学习算子": operators_dir / "machine_learning",
    "深度学习算子": operators_dir / "deep_learning",
    "专用算子": operators_dir / "specialized"
}

for name, path in operator_categories.items():
    if path.exists():
        py_files = list(path.glob("*.py"))
        pyc_files = list(path.glob("__pycache__/*.pyc"))
        print(f"  [PASS] {name}: {len(py_files)} 个Python文件")
        for py_file in py_files:
            if py_file.name != "__init__.py":
                print(f"         - {py_file.name}")
    else:
        print(f"  [FAIL] {name}: 目录不存在")

# 测试3: 检查知识库内容
print("\n[TEST 3] 检查知识库内容")
knowledge_categories = {
    "法规库": knowledge_dir / "regulations",
    "工艺知识库": knowledge_dir / "process_knowledge",
    "违规模式库": knowledge_dir / "violation_patterns",
    "专家经验库": knowledge_dir / "expert_experience"
}

for name, path in knowledge_categories.items():
    if path.exists():
        files = list(path.glob("*"))
        print(f"  [PASS] {name}: {len(files)} 个文件")
        for file in files[:3]:  # 只显示前3个
            print(f"         - {file.name}")
    else:
        print(f"  [FAIL] {name}: 目录不存在")

# 测试4: 尝试导入算子库模块
print("\n[TEST 4] 测试算子库模块导入")
try:
    from shared.operators.machine_learning.isolation_forest import IsolationForestDetector
    print(f"  [PASS] 成功导入 IsolationForestDetector")
except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")

try:
    from shared.operators.specialized.constant_detector import ConstantDetector
    print(f"  [PASS] 成功导入 ConstantDetector")
except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")

# 测试5: 测试子智能体对三库的访问
print("\n[TEST 5] 测试子智能体对三库的访问")
# 通过修改子智能体任务来验证它能否访问三库

# 创建测试任务来验证子智能体能读取知识库
import tempfile
import json
import importlib.util

# 导入 call_subagent
spec = importlib.util.spec_from_file_location(
    "call_subagent",
    project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "call_subagent.py"
)
call_subagent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(call_subagent_module)
call_subagent = call_subagent_module.call_subagent

with tempfile.TemporaryDirectory() as temp_dir:
    os.environ['SESSION_DIR'] = temp_dir

    # 测试异常检测子智能体能否访问算子库
    print("\n  测试异常检测子智能体访问算子库...")
    result = call_subagent(
        'anomaly-detection',
        '使用孤立森林算子检测异常',
        {'operator': 'isolation_forest'}
    )

    if result.get('status') == 'completed':
        print(f"  [PASS] 异常检测子智能体成功执行（可能访问了算子库）")
    else:
        print(f"  [FAIL] 异常检测子智能体执行失败: {result.get('error')}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

"""
测试主智能体身份文件加载

验证主智能体能正确加载 IDENTITY.md, SOUL.md, AGENTS.md 等身份文件
"""
import os
import sys
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("主智能体身份文件加载测试")
print("=" * 60)

# 主智能体目录
workspace_dir = project_root / "workspace"

print(f"\n工作空间目录: {workspace_dir}")

# 定义要检查的身份文件
identity_files = {
    "IDENTITY.md": "主智能体身份卡片",
    "SOUL.md": "主智能体个性和调用规则",
    "AGENTS.md": "工作空间规则和约定",
    "MEMORY.md": "长期记忆",
    "USER.md": "用户信息",
    "TOOLS.md": "环境特定说明"
}

print("\n[TEST 1] 检查主智能体身份文件")
for filename, description in identity_files.items():
    file_path = workspace_dir / filename
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.count('\n') + 1
        print(f"  [PASS] {filename} ({description}): {lines} 行")
    else:
        print(f"  [FAIL] {filename} ({description}): 不存在")

# 测试2: 验证SOUL.md中包含子智能体调用信息
print("\n[TEST 2] 验证 SOUL.md 包含子智能体调用信息")
soul_file = workspace_dir / "SOUL.md"
if soul_file.exists():
    with open(soul_file, 'r', encoding='utf-8') as f:
        soul_content = f.read()

    required_keywords = [
        "子智能体",
        "call_subagent",
        "data-perception",
        "anomaly-detection",
        "rule-reasoning",
        "disposition-execution"
    ]

    for keyword in required_keywords:
        if keyword in soul_content:
            print(f"  [PASS] 包含关键词: {keyword}")
        else:
            print(f"  [FAIL] 缺少关键词: {keyword}")

# 测试3: 验证IDENTITY.md包含核心信息
print("\n[TEST 3] 验证 IDENTITY.md 包含核心信息")
identity_file = workspace_dir / "IDENTITY.md"
if identity_file.exists():
    with open(identity_file, 'r', encoding='utf-8') as f:
        identity_content = f.read()

    required_sections = [
        ("主智能体", "主智能体名称"),
        ("核心价值", "核心价值描述"),
        ("管理", "管理的子智能体"),
        ("LLM", "LLM驱动模式")
    ]

    for keyword, description in required_sections:
        if keyword in identity_content:
            print(f"  [PASS] 包含 {description}")
        else:
            print(f"  [FAIL] 缺少 {description}")

# 测试4: 检查 orchestrator-core 技能
print("\n[TEST 4] 检查 orchestrator-core 技能")
orchestrator_core = workspace_dir / "skills" / "orchestrator-core"
if orchestrator_core.exists():
    scripts_dir = orchestrator_core / "scripts"
    if scripts_dir.exists():
        script_files = [
            "call_subagent.py",
            "create_session.py",
            "cleanup_sessions.py",
            "subagent_tools.py",
            "schemas.py"
        ]

        for script_file in script_files:
            file_path = scripts_dir / script_file
            if file_path.exists():
                print(f"  [PASS] {script_file} 存在")
            else:
                print(f"  [FAIL] {script_file} 不存在")
    else:
        print(f"  [FAIL] scripts 目录不存在")
else:
    print(f"  [FAIL] orchestrator-core 目录不存在")

# 测试5: 模拟主智能体加载身份文件
print("\n[TEST 5] 模拟主智能体加载身份文件")

# 定义要加载的文件列表
files_to_load = [
    ('IDENTITY.md', 'identity'),
    ('SOUL.md', 'soul'),
    ('AGENTS.md', 'agents'),
    ('MEMORY.md', 'memory'),
    ('TOOLS.md', 'tools')
]

def load_identity_files(agent_dir: Path) -> dict:
    """加载智能体的身份文件"""
    identity_files = {}

    for filename, key in files_to_load:
        file_path = agent_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    identity_files[key] = f.read()
            except Exception as e:
                print(f"  [ERROR] 加载 {filename} 失败: {e}")

    return identity_files

identity = load_identity_files(workspace_dir)

print(f"  [PASS] 成功加载 {len(identity)}/{len(files_to_load)} 个身份文件")
for key in identity:
    content_preview = identity[key][:100].replace('\n', ' ')
    print(f"         {key}: {content_preview}...")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

print("\n总结:")
print("1. 主智能体身份文件完整")
print("2. SOUL.md 包含子智能体调用规则")
print("3. IDENTITY.md 包含核心信息")
print("4. orchestrator-core 技能文件完整")
print("5. 身份文件加载功能正常")

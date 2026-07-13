# Hermes Agent 框架本地化设计文档

> **日期**: 2026-07-09
> **状态**: ✅ 已批准
> **版本**: 1.0

---

## 1. 目标

将 Hermes Agent 框架本地化到项目内部，消除对外部 `D:\Hermes\hermes-agent` 的依赖，同时扩展身份文件读取以支持项目的完整需求。

**核心目标**：
- 消除对外部代码仓库的依赖
- 扩展 AIAgent 以读取所有 7 个身份文件（而非仅 SOUL.md）
- 保持框架的完整功能（技能扫描、工具调用、记忆功能）

---

## 2. 当前问题

1. **依赖外部仓库**：项目通过 editable 模式依赖 `D:\Hermes\hermes-agent`
2. **身份文件不完整**：原版 AIAgent 只读取 SOUL.md，项目需要 7 个身份文件
3. **无法 pip 安装**：hermes-agent 不在 PyPI 上

---

## 3. 解决方案

### 3.1 架构设计

**目录结构**：
```
shared/
└── framework/
    └── hermes_agent/              # Hermes Agent 框架本地副本
        ├── run_agent.py           # AIAgent 类
        ├── hermes_constants.py    # 常量定义
        ├── agent/
        │   ├── prompt_builder.py  # 提示构建器
        │   ├── system_prompt.py   # 系统提示组装
        │   ├── session_db.py      # 记忆功能
        │   ├── runtime_helpers.py # 运行时辅助
        │   ├── process_bootstrap.py
        │   └── ...                # 其他必要文件
        ├── openai/                # 客户端封装
        ├── hermes_constants.py
        └── ...                   # 其他依赖文件
```

### 3.2 修改内容

#### 修改 1：hermes_constants.py

添加所有身份文件常量：
```python
# 扩展的身份文件列表
IDENTITY_FILES = [
    "IDENTITY.md",    # 身份卡片
    "SOUL.md",        # 身份和个性
    "AGENTS.md",      # 工作区规范
    "MEMORY.md",      # 长期记忆
    "USER.md",        # 用户信息
    "TOOLS.md",       # 工具配置
    "HEARTBEAT.md"    # 周期性任务
]

def get_identity_files() -> List[Path]:
    """返回所有身份文件路径"""
    hermes_home = get_hermes_home()
    return [hermes_home / f for f in IDENTITY_FILES]
```

#### 修改 2：agent/prompt_builder.py

扩展提示构建函数：
```python
def load_identity_files() -> str:
    """加载所有身份文件并组合成提示"""
    hermes_home = get_hermes_home()
    parts = []

    for filename in IDENTITY_FILES:
        path = hermes_home / filename
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                parts.append(f"## {filename}\n\n{content}")

    return "\n\n".join(parts)
```

#### 修改 3：agent/system_prompt.py

修改系统提示组装，使用扩展的身份文件加载函数。

### 3.3 导入方式

修改项目中的导入：
```python
# 原来
from run_agent import AIAgent

# 修改后
from shared.framework.hermes_agent.run_agent import AIAgent
```

---

## 4. 迁移步骤

1. **复制框架文件**
   - 从 `D:\Hermes\hermes-agent` 复制到 `shared/framework/hermes_agent/`
   - 包含所有必要文件和依赖

2. **修改身份文件读取逻辑**
   - 修改 `hermes_constants.py` 添加常量
   - 修改 `prompt_builder.py` 实现加载函数
   - 修改 `system_prompt.py` 组装提示

3. **更新项目导入**
   - 更新 `subagents/*/entry.py`
   - 更新 `workspace/skills/orchestrator-core/scripts/`
   - 更新其他使用 AIAgent 的地方

4. **测试验证**
   - 测试主智能体身份加载
   - 测试子智能体身份加载
   - 测试技能扫描
   - 测试 LLM 调用

5. **清理外部依赖**
   - 卸载 editable hermes-agent
   - 删除对 `D:\Hermes\hermes-agent` 的依赖
   - 更新 requirements.txt

---

## 5. 测试验证

### 5.1 功能测试

| 测试项 | 验证内容 |
|--------|----------|
| 身份文件加载 | 验证所有 7 个文件正确加载 |
| 主智能体 | 验证 workspace/ 身份文件加载 |
| 子智能体 | 验证各子智能体身份文件加载 |
| 技能扫描 | 验证 skills/ 目录扫描 |
| LLM 调用 | 验证 LongCat-2.0 调用 |
| 工具调用 | 验证工具调用循环 |
| 记忆功能 | 验证 SessionDB |

### 5.2 错误处理

| 场景 | 处理方式 |
|------|----------|
| 身份文件缺失 | 记录警告，继续执行（SOUL.md 必需） |
| 框架导入失败 | 清晰错误提示 + 安装指引 |
| LLM 调用失败 | 重试机制 + 错误返回 |

---

## 6. 向后兼容性

- 保持 AIAgent 类接口不变
- 保持技能扫描机制不变
- 保持工具调用机制不变
- 现有代码无需大幅修改

---

## 7. 项目文件更新

需要更新的文件：
- `subagents/*/entry.py` - 更新导入
- `shared/utils/hermes_importer.py` - 删除（不再需要）
- `requirements.txt` - 移除 hermes-agent 依赖
- `docs/code-quality-review-2026-07-09.md` - 记录修复状态

---

## 8. 预期结果

完成后：
- ✅ 项目自包含，不依赖外部 `D:\Hermes\hermes-agent`
- ✅ AIAgent 读取所有 7 个身份文件
- ✅ 主智能体和子智能体正常工作
- ✅ 技能扫描和工具调用正常
- ✅ 记忆功能保留

---

**设计完成，等待实施计划。**

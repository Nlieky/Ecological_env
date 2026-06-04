# 子智能体LLM配置增强设计

> **目标:** 让每个子智能体都充分利用LLM能力，使用专属的system_prompt和专用模型

**日期:** 2026-06-04

**状态:** 待实施

---

## 问题背景

### 当前状态

`llm_config.yaml` 中已经定义了各子智能体的LLM配置（system_prompt、model选择），但这些配置**没有被加载或使用**。

`execution_control.py` 在协调子智能体时，只使用主智能体的system_prompt，导致：

1. 子智能体决策时没有使用自己的专业身份提示词
2. 所有子智能体使用相同的模型（primary），没有根据任务特点选择合适模型
3. 子智能体的LLM能力未充分利用

### 目标

完全启用子智能体的LLM配置，让每个子智能体使用：
- 专属的system_prompt（反映专业身份）
- 专用的模型（fast/primary/analysis，根据任务特点）

---

## 架构设计

### 核心思路

在 `LLMAgentCoordinator` 中添加子智能体LLM配置加载能力，修改 `_llm_coordinate_agent` 方法使用子智能体专属配置。

### 架构图

```
LLMAgentCoordinator
    ├── llm_client (通用LLM客户端)
    ├── llm_config (从llm_config.yaml加载的完整配置) ⭐ 新增
    ├── _load_llm_config() ⭐ 新增
    ├── _get_subagent_config(agent_id) ⭐ 新增
    ├── _get_subagent_system_prompt(agent_id) ⭐ 新增
    ├── _get_subagent_model(agent_id) ⭐ 新增
    └── _llm_coordinate_agent(identity, task, previous_results)
            ↓ 使用子智能体配置 ⭐ 修改
```

### 修改的文件

| 文件 | 修改内容 | 新增/修改 |
|------|----------|-----------|
| `workspace/skills/orchestrator-core/scripts/execution_control.py` | 添加配置加载和子智能体配置获取方法，修改`_llm_coordinate_agent`，更新`__init__` | 修改 |

### 不需要修改的文件

- `shared/configs/llm_config.yaml` - 配置已存在，无需修改
- `shared/configs/llm_client.py` - LLM客户端无需修改

---

## 详细组件设计

### 组件1：配置加载器

**新增方法：`_load_llm_config()`**

```python
def _load_llm_config(self) -> dict:
    """从 llm_config.yaml 加载完整的LLM配置"""
    import yaml

    config_path = self.project_root / "shared" / "configs" / "llm_config.yaml"

    if not config_path.exists():
        logger.warning(f"[CONFIG] LLM配置文件不存在: {config_path}")
        return {"subagent_configs": {}}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        print(f"[CONFIG] 已加载LLM配置")
        return config
    except Exception as e:
        logger.error(f"[CONFIG] 加载LLM配置失败: {e}")
        return {"subagent_configs": {}}
```

**调用时机：** 在 `__init__` 方法中初始化时调用一次

---

### 组件2：子智能体配置获取

**新增方法：`_get_subagent_config(agent_id: str) -> dict`**

```python
def _get_subagent_config(self, agent_id: str) -> dict:
    """获取指定子智能体的LLM配置"""
    if not hasattr(self, 'llm_config') or not self.llm_config:
        self.llm_config = self._load_llm_config()

    subagent_configs = self.llm_config.get('subagent_configs', {})
    config = subagent_configs.get(agent_id, {})

    # 检查是否启用
    if not config.get('enabled', True):
        logger.warning(f"[CONFIG] 子智能体 {agent_id} 的LLM功能未启用，使用默认配置")
        return {}

    # 验证必要字段
    if 'system_prompt' not in config:
        logger.warning(f"[CONFIG] 子智能体 {agent_id} 缺少system_prompt配置")

    if 'model' not in config:
        logger.info(f"[CONFIG] 子智能体 {agent_id} 未指定模型，使用primary")
        config['model'] = 'primary'

    return config
```

**新增方法：`_get_subagent_system_prompt(agent_id: str) -> str`**

```python
def _get_subagent_system_prompt(self, agent_id: str) -> str:
    """获取子智能体的system_prompt"""
    config = self._get_subagent_config(agent_id)

    if not config:
        # 回退到主智能体提示词
        return self._build_master_agent_system_prompt()

    system_prompt = config.get('system_prompt', '')

    if not system_prompt:
        logger.warning(f"[CONFIG] 子智能体 {agent_id} 未配置system_prompt，使用主智能体提示词")
        return self._build_master_agent_system_prompt()

    return system_prompt
```

**新增方法：`_get_subagent_model(agent_id: str) -> str`**

```python
def _get_subagent_model(self, agent_id: str) -> str:
    """获取子智能体的专用模型配置"""
    config = self._get_subagent_config(agent_id)

    if not config:
        # 默认使用主模型
        return 'primary'

    model_key = config.get('model', 'primary')

    # 验证模型配置有效
    valid_models = ['fast', 'primary', 'analysis']
    if model_key not in valid_models:
        logger.warning(f"[CONFIG] 无效的模型配置: {model_key}，使用primary")
        return 'primary'

    return model_key
```

---

### 组件3：修改现有方法

**修改 `__init__` 方法：**

```python
def __init__(self, llm_client=None, project_root=None):
    self.llm_client = llm_client
    self.project_root = project_root or Path(__file__).resolve().parent.parent.parent.parent.parent
    self.identity_loader = SubAgentIdentityLoader(project_root=self.project_root)

    # ⭐ 新增：初始化时加载LLM配置
    self.llm_config = self._load_llm_config()

    print("[COORD] 大模型子智能体协调器初始化完成")
```

**修改 `_llm_coordinate_agent` 方法的关键点：**

1. **系统提示词** - 使用子智能体专属system_prompt

   ```python
   # 原来：
   system_prompt = self._build_master_agent_system_prompt()

   # 修改为：
   agent_id = identity.agent_id
   system_prompt = self._get_subagent_system_prompt(agent_id)
   print(f"[LLM] 使用 {agent_id} 专属系统提示词")
   ```

2. **模型选择** - 使用子智能体专用模型

   ```python
   # 原来：
   decision_response = self.llm_client.chat(
       message=decision_prompt,
       system_prompt=system_prompt,
       model_type="primary",  # 硬编码
       temperature=0.0
   )

   # 修改为：
   model_type = self._get_subagent_model(agent_id)
   print(f"[LLM] {agent_id} 使用模型: {model_type}")

   decision_response = self.llm_client.chat(
       message=decision_prompt,
       system_prompt=system_prompt,
       model_type=model_type,  # 使用子智能体配置
       temperature=0.0
   )
   ```

3. **日志增强**

   ```python
   print(f"[LLM] 子智能体: {agent_id}")
   print(f"[LLM] 使用配置: model={model_type}, system_prompt长度={len(system_prompt)}")
   ```

---

## 数据流和调用链

### 完整调用链

```
用户查询
    ↓
coordinate_agent_execution(agent_id, task)
    ↓
_llm_coordinate_agent(identity, task, previous_results)
    ↓
├── _get_subagent_system_prompt(agent_id) → 获取子智能体专属提示词
├── _get_subagent_model(agent_id) → 获取子智能体专用模型
├── _build_identity_summary(identity) → 构建身份摘要
└── _get_available_scripts(identity) → 获取可用脚本
    ↓
LLM决策调用（使用子智能体配置）
    ├── system_prompt: 子智能体专属提示词
    └── model_type: 子智能体专用模型
    ↓
解析决策 → 执行脚本 → LLM分析结果
    ↓
返回结构化结果
```

### 各子智能体配置映射

| 子智能体 | agent_id | 模型 | 说明 |
|---------|----------|------|------|
| 多维数据感知子智能体 | `multi-dimensional-data-perception-agent` | fast | 数据处理快速响应 |
| 异常检测子智能体 | `anomaly-detection-agent` | analysis | 复杂分析需要更强能力 |
| 规则推理子智能体 | `rule-reasoning-agent` | primary | 推理需要准确性 |
| 研判预警与处置执行子智能体 | `disposition-execution-agent` | primary | 判定和工单生成 |

---

## 回退机制

**多层回退策略：**

1. **配置文件不存在** → 使用空配置，回退到主智能体提示词
2. **子智能体未配置** → 使用主智能体提示词 + primary模型
3. **模型配置无效** → 默认使用primary模型
4. **所有LLM调用失败** → 回退到本地规则模式（`_local_coordinate_agent`）

---

## 测试验证

### 测试用例

**1. 配置加载测试**
```python
def test_llm_config_loading():
    """验证LLM配置能正确加载"""
    coordinator = LLMAgentCoordinator(llm_client)

    # 验证配置已加载
    assert coordinator.llm_config is not None
    assert 'subagent_configs' in coordinator.llm_config
```

**2. 子智能体配置获取测试**
```python
def test_get_subagent_config():
    """验证能正确获取子智能体配置"""
    coordinator = LLMAgentCoordinator(llm_client)

    # 测试存在的子智能体
    config = coordinator._get_subagent_config('multi-dimensional-data-perception-agent')
    assert config.get('enabled') == True
    assert 'system_prompt' in config
    assert 'model' in config

    # 测试不存在的子智能体
    empty_config = coordinator._get_subagent_config('non-existent-agent')
    assert empty_config == {}
```

**3. 模型选择测试**
```python
def test_get_subagent_model():
    """验证模型选择正确"""
    coordinator = LLMAgentCoordinator(llm_client)

    # 数据感知子智能体应该使用fast模型
    assert coordinator._get_subagent_model('multi-dimensional-data-perception-agent') == 'fast'

    # 异常检测子智能体应该使用analysis模型
    assert coordinator._get_subagent_model('anomaly-detection-agent') == 'analysis'

    # 规则推理子智能体应该使用primary模型
    assert coordinator._get_subagent_model('rule-reasoning-agent') == 'primary'
```

**4. 端到端测试**
```python
def test_subagent_llm_integration():
    """验证子智能体使用自己的LLM配置"""
    coordinator = LLMAgentCoordinator(llm_client)

    # 调用数据感知子智能体
    result = coordinator.coordinate_agent_execution(
        agent_id='multi-dimensional-data-perception-agent',
        task={'description': '测试任务', 'data': {...}}
    )

    # 验证返回结果
    assert result['status'] == 'success'
```

**5. 回退机制测试**
```python
def test_fallback_mechanism():
    """验证配置缺失时的回退机制"""
    coordinator = LLMAgentCoordinator(llm_client)

    # 删除LLM配置
    coordinator.llm_config = {}

    # 应该回退到主智能体提示词
    system_prompt = coordinator._get_subagent_system_prompt('any-agent')
    assert '主智能体' in system_prompt or 'master' in system_prompt.lower()
```

---

## 预期效果

### 改进前

```python
[COORD] 使用 LLM 协调模式
[LLM] 系统提示词已构建，包含主智能体身份
[LLM] 请求 multi-dimensional-data-perception-agent 决策...
# 使用 primary 模型
# 使用主智能体的system_prompt
```

### 改进后

```python
[COORD] 使用 LLM 协调模式
[CONFIG] 已加载LLM配置
[LLM] 子智能体: multi-dimensional-data-perception-agent
[LLM] 使用配置: model=fast, system_prompt长度=512
[LLM] 请求 multi-dimensional-data-perception-agent 决策...
# 使用 fast 模型（更快）
# 使用数据感知子智能体专属的system_prompt
```

---

## 验收标准

完成后：
1. ✅ 每个子智能体使用自己的system_prompt
2. ✅ 每个子智能体使用配置的模型
3. ✅ 配置缺失时正确回退
4. ✅ 不影响现有功能
5. ✅ 所有测试通过

---

## 方法清单

| 方法名 | 类型 | 说明 |
|--------|------|------|
| `_load_llm_config()` | 新增 | 加载LLM配置文件 |
| `_get_subagent_config(agent_id)` | 新增 | 获取子智能体配置 |
| `_get_subagent_system_prompt(agent_id)` | 新增 | 获取子智能体提示词 |
| `_get_subagent_model(agent_id)` | 新增 | 获取子智能体模型 |
| `__init__()` | 修改 | 添加配置加载初始化 |
| `_llm_coordinate_agent()` | 修改 | 使用子智能体配置 |

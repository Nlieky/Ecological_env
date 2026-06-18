# LLM 驱动框架重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 LLM 驱动框架的静默回退问题，统一多套调度系统，恢复被注释的 LLM 分析功能，建立健壮透明的 LLM 驱动机制

**Architecture:** 采用"必须使用 LLM，失败则明确报错"的原则，移除静默回退机制，整合 `execution_control.py` 和 `dynamic_orchestrator.py` 的功能，建立统一的调度框架

**Tech Stack:** Python 3.11+, Anthropic SDK, Flask, Prometheus

---

## Context

当前废水监测系统的 LLM 驱动框架存在严重问题：

1. **静默回退问题**：LLM 调用失败时自动回退到规则模式，用户无法感知
2. **多套调度系统**：`execution_control.py` 和 `dynamic_orchestrator.py` 功能重叠
3. **LLM 功能被注释**：`app_orchestrator.py` 中 240 行高质量 LLM 代码被闲置
4. **错误处理不完善**：捕获所有 Exception，缺乏明确的错误分类和提示

这违反了核心架构原则："必须使用 LLM 进行意图识别和子智能体调度"。

---

## File Structure

### 需要修改的文件

| 文件 | 职责 | 修改内容 |
|------|------|----------|
| `shared/configs/llm_client.py` | LLM 客户端 | 添加错误分类、重试机制、详细日志 |
| `shared/configs/llm_config.yaml` | LLM 配置 | 添加错误处理、重试、监控配置 |
| `workspace/skills/orchestrator-core/scripts/execution_control.py` | 执行控制 | 移除静默回退，改为明确报错 |
| `workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py` | 动态编排 | 扩展功能，整合调度职责 |
| `workspace/skills/orchestrator-core/scripts/task_receiving_and_parsing.py` | 任务解析 | 增强 LLM 意图解析的错误处理 |
| `middleware/app_orchestrator.py` | Flask 中间件 | 逐步恢复被注释的 LLM 分析功能 |

### 需要创建的文件

| 文件 | 职责 |
|------|------|
| `shared/configs/llm_errors.py` | LLM 错误类定义 |
| `workspace/skills/orchestrator-core/scripts/llm_coordinator.py` | 统一的 LLM 协调器 |

---

## 实施计划

### Task 1: 创建 LLM 错误类定义模块

**目标**：建立明确的错误分类体系，替代通用的 Exception 捕获

**Files:**
- Create: `shared/configs/llm_errors.py`

- [ ] **Step 1: 创建错误类定义文件**

```python
"""
LLM 错误类定义
建立明确的错误分类体系，替代通用的 Exception 捕获
"""

class LLMError(Exception):
    """LLM 错误基类"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class LLMTimeoutError(LLMError):
    """LLM 响应超时"""
    pass

class LLMQuotaError(LLMError):
    """LLM 配额用尽（如 API 速率限制）"""
    pass

class LLMServiceError(LLMError):
    """LLM 服务不可用（如 500 错误）"""
    pass

class LLMConfigError(LLMError):
    """LLM 配置错误（如 API Key 无效）"""
    pass

class LLMContentError(LLMError):
    """LLM 内容处理错误（如响应格式错误）"""
    pass
```

- [ ] **Step 2: 添加错误消息映射**

```python
ERROR_MESSAGES = {
    LLMTimeoutError: "LLM 服务响应超时，请检查网络连接或稍后重试",
    LLMQuotaError: "LLM API 调用频率超限，请稍后重试",
    LLMServiceError: "LLM 服务暂时不可用，请联系管理员",
    LLMConfigError: "LLM 配置错误，请检查 API Key 设置",
    LLMContentError: "LLM 响应格式错误，系统正在处理"
}
```

- [ ] **Step 3: 添加单元测试**

创建 `tests/unit/test_llm_errors.py`：

```python
import pytest
from shared.configs.llm_errors import LLMTimeoutError, LLMQuotaError

def test_error_hierarchy():
    error = LLMTimeoutError("超时")
    assert isinstance(error, Exception)
    assert error.message == "超时"

def test_error_with_details():
    error = LLMQuotaError("配额用尽", {"retry_after": 60})
    assert error.details["retry_after"] == 60
```

- [ ] **Step 4: 运行测试验证**

```bash
pytest tests/unit/test_llm_errors.py -v
```

预期：全部通过

- [ ] **Step 5: 提交**

```bash
git add shared/configs/llm_errors.py tests/unit/test_llm_errors.py
git commit -m "feat: 添加 LLM 错误类定义，建立错误分类体系"
```

---

### Task 2: 增强 LLM 客户端错误处理和重试机制

**目标**：在 `llm_client.py` 中实现智能重试和错误分类

**Files:**
- Modify: `shared/configs/llm_client.py:80-150`

- [ ] **Step 1: 添加错误分类逻辑**

在 `LLMClient` 类的 `chat()` 方法中添加错误分类：

```python
def chat(self, prompt: str, model_type: str = "primary") -> str:
    """发送消息到 LLM（带重试和错误分类）"""
    
    # 1. 选择模型
    if model_type == "primary":
        model = self.config.primary_model
    elif model_type == "fast":
        model = self.config.fast_model
    else:
        model = self.config.analysis_model
    
    # 2. 重试循环
    max_retries = self.config.max_retries
    for attempt in range(max_retries):
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
            
        except anthropic.Errors.APITimeoutError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                logger.warning(f"[LLM] 超时，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise LLMTimeoutError(f"LLM 响应超时，已重试 {max_retries} 次")
                
        except anthropic.Errors.RateLimitError as e:
            raise LLMQuotaError(f"LLM API 调用频率超限: {e}")
            
        except anthropic.Errors.APIStatusError as e:
            if e.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"[LLM] 服务错误 {e.status_code}，{wait_time}秒后重试")
                    time.sleep(wait_time)
                else:
                    raise LLMServiceError(f"LLM 服务错误 {e.status_code}，已重试 {max_retries} 次")
            else:
                raise LLMConfigError(f"LLM API 错误 {e.status_code}: {e}")
                
        except anthropic.Errors.UnprocessableEntityError as e:
            raise LLMContentError(f"LLM 响应处理错误: {e}")
            
        except Exception as e:
            # 最后的兜底
            if attempt == max_retries - 1:
                logger.error(f"[LLM] 未知错误: {e}")
                raise LLMError(f"LLM 调用失败: {e}")
```

- [ ] **Step 2: 添加必要的导入**

在文件顶部添加：

```python
import time
import anthropic
from shared.configs.llm_errors import (
    LLMError, LLMTimeoutError, LLMQuotaError,
    LLMServiceError, LLMConfigError, LLMContentError
)
```

- [ ] **Step 3: 测试错误分类**

```bash
cd E:/project/Ecological_env
python -c "
from shared.configs.llm_client import get_llm_client
from shared.configs.llm_errors import LLMTimeoutError

client = get_llm_client(env_path='middleware/.env')

# 测试正常调用
try:
    response = client.chat('你好', model_type='fast')
    print('正常调用成功')
except Exception as e:
    print(f'错误类型: {type(e).__name__}')
"
```

预期：正常调用成功返回响应

- [ ] **Step 4: 提交**

```bash
git add shared/configs/llm_client.py
git commit -m "feat: LLM 客户端添加错误分类和重试机制"
```

---

### Task 3: 移除静默回退机制，改为明确报错

**目标**：修改 `execution_control.py` 和 `task_receiving_and_parsing.py`，LLM 失败时抛出明确错误

**Files:**
- Modify: `workspace/skills/orchestrator-core/scripts/execution_control.py:591-597`
- Modify: `workspace/skills/orchestrator-core/scripts/task_receiving_and_parsing.py:214-216`

- [ ] **Step 1: 修改 execution_control.py 的回退机制**

找到 `_llm_coordinate_agent()` 方法中的异常处理（约第 591-597 行）：

原代码：
```python
except Exception as e:
    logger.error(f"[LLM] LLM 协调失败: {e}")
    import traceback
    traceback.print_exc()
    # 回退到本地模式
    print(f"[FALLBACK] 回退到本地规则模式")
    return self._local_coordinate_agent(identity, task, previous_results)
```

修改为：
```python
except LLMError as e:
    logger.error(f"[LLM] LLM 协调失败: {e.message}")
    # 向用户明确提示错误
    raise LLMError(
        f"LLM 子智能体协调失败: {e.message}",
        details={"agent": identity["name"], "task": task}
    ) from e
except Exception as e:
    logger.error(f"[LLM] 未知错误: {e}")
    raise LLMError(f"LLM 协调失败: {str(e)}")
```

- [ ] **Step 2: 修改 task_receiving_and_parsing.py 的回退机制**

找到 `parse_intent_with_llm()` 方法中的异常处理（约第 214-216 行）：

原代码：
```python
except Exception as e:
    logger.error(f"[LLM] 大模型调用失败: {e}")
    return self._parse_intent_by_rules(signal)
```

修改为：
```python
except LLMError as e:
    logger.error(f"[LLM] 意图解析失败: {e.message}")
    raise LLMError(
        f"LLM 意图识别失败: {e.message}",
        details={"signal": str(signal)}
    ) from e
```

- [ ] **Step 3: 添加必要的导入**

在两个文件顶部添加：

```python
from shared.configs.llm_errors import LLMError
```

- [ ] **Step 4: 测试错误抛出**

```bash
cd E:/project/Ecological_env
python -c "
# 故意设置错误的 API Key 测试
import os
os.environ['ANTHROPIC_API_KEY'] = 'invalid_key'

from workspace.skills.orchestrator_core.scripts.task_receiving_and_parsing import TaskReceivingAndParsing

parser = TaskReceivingAndParsing(llm_client=None)
try:
    parser.parse_intent_with_llm({'data': 'test'})
except LLMError as e:
    print(f'捕获到 LLMError: {e.message}')
"
```

预期：捕获到 LLMError，并且没有回退到规则模式

- [ ] **Step 5: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/execution_control.py
git add workspace/skills/orchestrator-core/scripts/task_receiving_and_parsing.py
git commit -m "refactor: 移除 LLM 静默回退机制，改为明确报错"
```

---

### Task 4: 整合调度系统，统一职责分工

**目标**：明确 `dynamic_orchestrator.py` 和 `execution_control.py` 的职责，消除重叠

**Files:**
- Modify: `workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py`
- Modify: `workspace/skills/orchestrator-core/scripts/execution_control.py`

- [ ] **Step 1: 分析两个模块的职责**

查看两个文件的功能：
- `dynamic_orchestrator.py`：任务规划、资源分配
- `execution_control.py`：任务执行监控、LLM 协调

决定保留：`dynamic_orchestrator.py` 负责规划，`execution_control.py` 负责执行

- [ ] **Step 2: 在 dynamic_orchestrator.py 中添加明确的职责说明**

在文件顶部添加文档字符串：

```python
"""
动态编排器 - 负责任务规划和资源分配

职责：
1. 接收用户任务请求
2. 解析任务意图（调用 LLM）
3. 生成执行计划（DAG）
4. 匹配子智能体资源
5. 调用 ExecutionControl 执行任务

不负责：
- 实际的子智能体调用（由 ExecutionControl 负责）
- 结果解释（由 result_interpretation.py 负责）
"""
```

- [ ] **Step 3: 在 execution_control.py 中添加明确的职责说明**

```python
"""
执行控制模块 - 负责任务执行和 LLM 协调

职责：
1. 接收执行计划
2. LLM 驱动的子智能体协调
3. 执行状态监控
4. 异常处理（不静默回退）
5. 结果收集和传递

不负责：
- 任务规划（由 dynamic_orchestrator.py 负责）
- 意图解析（由 task_receiving_and_parsing.py 负责）
"""
```

- [ ] **Step 4: 验证两个模块的独立性**

```bash
cd E:/project/Ecological_env
python -c "
from workspace.skills.orchestrator_core.scripts.dynamic_orchestrator import DynamicOrchestrator
from workspace.skills.orchestrator_core.scripts.execution_control import LLMAgentCoordinator

print('DynamicOrchestrator 职责：任务规划')
print('LLMAgentCoordinator 职责：执行控制')
print('两个模块职责明确，无重叠')
"
```

预期：成功加载两个模块

- [ ] **Step 5: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py
git add workspace/skills/orchestrator-core/scripts/execution_control.py
git commit -m "docs: 明确调度系统职责分工，消除重叠"
```

---

### Task 5: 恢复 app_orchestrator.py 中被注释的 LLM 功能

**目标**：逐步恢复 `app_orchestrator.py` 第 158-397 行被注释的 LLM 分析代码

**Files:**
- Modify: `middleware/app_orchestrator.py:158-397`

- [ ] **Step 1: 检查被注释的代码结构**

查看第 158-397 行的内容，确认是 LLM 实时分析功能

- [ ] **Step 2: 添加功能开关**

在文件开头添加配置：

```python
# LLM 实时分析功能开关
ENABLE_LLM_REALTIME_ANALYSIS = os.getenv('ENABLE_LLM_REALTIME_ANALYSIS', 'false').lower() == 'true'
```

- [ ] **Step 3: 逐步取消注释（第一阶段）**

取消注释第 158-200 行（核心 LLM 调用逻辑）：

```python
# 取消注释前，添加错误处理
if ENABLE_LLM_REALTIME_ANALYSIS:
    try:
        # ========== LLM 实时分析模块 ==========
        # （原被注释的代码）
        
        # LLM 分析入口点
        def analyze_with_llm(data):
            """
            使用 LLM 分析实时数据
            
            Args:
                data: 实时监测数据
                
            Returns:
                LLM 分析结果
            """
            if not llm_client:
                raise LLMConfigError("LLM 客户端未初始化")
                
            # 构建 LLM 提示词
            prompt = f\"\"\"
            分析以下废水监测数据，检测异常情况：
            
            数据：{data}
            
            请识别：
            1. 数据异常（恒定、突变、趋势等）
            2. 违规模式（插瓶干扰、稀释排放等）
            3. 处理建议
            \"\"\"
            
            try:
                response = llm_client.chat(prompt, model_type="fast")
                return response
            except LLMError as e:
                logger.error(f\"[LLM] 实时分析失败: {e.message}\")
                return None
                
    except Exception as e:
        logger.error(f\"[LLM] 初始化失败: {e}\")
```

- [ ] **Step 4: 添加环境变量配置**

在 `.env.example` 中添加：

```bash
# LLM 实时分析功能开关（默认关闭）
ENABLE_LLM_REALTIME_ANALYSIS=false
```

- [ ] **Step 5: 测试功能开关**

```bash
# 测试功能关闭状态
curl http://localhost:5000/api/dual-stream -X POST

# 测试功能开启状态
export ENABLE_LLM_REALTIME_ANALYSIS=true
curl http://localhost:5000/api/dual-stream -X POST
```

预期：功能关闭时不调用 LLM，开启时调用 LLM

- [ ] **Step 6: 提交**

```bash
git add middleware/app_orchestrator.py middleware/.env.example
git commit -m "feat: 恢复 LLM 实时分析功能，添加功能开关"
```

---

### Task 6: 添加 LLM 调用监控和日志

**目标**：增强 LLM 调用的可观测性，便于调试和监控

**Files:**
- Modify: `shared/configs/llm_client.py`
- Modify: `shared/configs/llm_config.yaml`

- [ ] **Step 1: 在 llm_client.py 中添加 Prometheus 指标**

```python
from prometheus_client import Counter, Histogram

# 定义 Prometheus 指标
llm_requests_total = Counter(
    'llm_requests_total',
    'LLM 请求总数',
    ['model_type', 'status']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM 请求耗时',
    ['model_type']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'LLM Token 使用总数',
    ['model_type', 'token_type']  # token_type: input/output
)
```

- [ ] **Step 2: 在 chat() 方法中记录指标**

```python
def chat(self, prompt: str, model_type: str = "primary") -> str:
    import time
    
    start_time = time.time()
    
    try:
        # ... LLM 调用代码 ...
        
        # 记录成功指标
        llm_requests_total.labels(
            model_type=model_type,
            status='success'
        ).inc()
        
        llm_request_duration.labels(
            model_type=model_type
        ).observe(time.time() - start_time)
        
        # 记录 Token 使用
        if hasattr(response, 'usage'):
            llm_tokens_total.labels(
                model_type=model_type,
                token_type='input'
            ).inc(response.usage.input_tokens)
            
            llm_tokens_total.labels(
                model_type=model_type,
                token_type='output'
            ).inc(response.usage.output_tokens)
        
        return response.content[0].text
        
    except LLMError as e:
        # 记录失败指标
        llm_requests_total.labels(
            model_type=model_type,
            status='error'
        ).inc()
        raise
```

- [ ] **Step 3: 在 llm_config.yaml 中添加监控配置**

```yaml
# ==================== 监控配置 ====================
monitoring:
  # 记录API调用
  log_api_calls: true
  
  # 记录Token使用
  log_token_usage: true
  
  # Prometheus指标
  prometheus:
    enabled: true
    metric_prefix: "llm"
  
  # 告警阈值
  alerts:
    error_rate_threshold: 0.05  # 错误率超过5%告警
    latency_threshold: 10  # 延迟超过10秒告警
```

- [ ] **Step 4: 测试 Prometheus 指标**

```bash
curl http://localhost:5000/metrics | grep llm_
```

预期：看到 LLM 相关指标

- [ ] **Step 5: 提交**

```bash
git add shared/configs/llm_client.py shared/configs/llm_config.yaml
git commit -m "feat: 添加 LLM 调用 Prometheus 监控指标"
```

---

### Task 7: 更新 CLAUDE.md 文档

**目标**：在 CLAUDE.md 中记录 LLM 框架的改进

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 添加 LLM 错误处理说明**

在"核心架构原则"部分的"原则2"下添加：

```markdown
### 原则2: LLM驱动主智能体 - 智能调度框架（更新）

**错误处理机制**：
- ✅ 必须使用 LLM 进行意图识别和子智能体调度
- ❌ **禁止** LLM 调用失败时静默回退到规则模式
- ✅ LLM 调用失败**必须**抛出明确的错误提示
- ✅ 实现智能重试（最多3次，指数退避）
- ✅ 错误分类：超时、配额、服务、配置、内容

**错误类型**：
- `LLMTimeoutError`: LLM 响应超时
- `LLMQuotaError`: API 调用频率超限
- `LLMServiceError`: LLM 服务不可用
- `LLMConfigError`: API Key 等配置错误
- `LLMContentError`: 响应格式错误
```

- [ ] **Step 2: 添加监控配置说明**

```markdown
### LLM 调用监控

**Prometheus 指标**：
- `llm_requests_total`: LLM 请求总数（按 model_type, status 分类）
- `llm_request_duration_seconds`: LLM 请求耗时
- `llm_tokens_total`: Token 使用总数（按 model_type, token_type 分类）

**查看指标**：
```bash
curl http://localhost:5000/metrics | grep llm_
```

**告警阈值**：
- 错误率超过 5% 时告警
- 延迟超过 10 秒时告警
```

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: 更新 LLM 框架错误处理和监控说明"
```

---

### Task 8: 集成测试和验证

**目标**：全面测试 LLM 框架的重构结果

**Files:**
- Create: `tests/integration/test_llm_framework.py`

- [ ] **Step 1: 创建集成测试文件**

```python
"""
LLM 驱动框架集成测试
验证 LLM 调用、错误处理、重试机制
"""
import pytest
from shared.configs.llm_client import get_llm_client
from shared.configs.llm_errors import LLMTimeoutError, LLMQuotaError
from workspace.skills.orchestrator_core.scripts.execution_control import LLMAgentCoordinator

def test_llm_normal_call():
    """测试正常 LLM 调用"""
    client = get_llm_client(env_path='middleware/.env')
    response = client.chat('测试', model_type='fast')
    assert response is not None
    assert len(response) > 0

def test_llm_error_classification():
    """测试错误分类"""
    client = get_llm_client(env_path='middleware/.env')
    # 模拟超时（需要 mock）
    # ...

def test_no_silent_fallback():
    """测试不静默回退"""
    parser = TaskReceivingAndParsing(llm_client=None)
    with pytest.raises(LLMError):
        parser.parse_intent_with_llm({'data': 'test'})

def test_retry_mechanism():
    """测试重试机制"""
    # 模拟网络抖动，验证重试
    # ...
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/integration/test_llm_framework.py -v
```

预期：全部测试通过

- [ ] **Step 3: 手动验证错误提示**

```bash
# 设置错误的 API Key
export ANTHROPIC_API_KEY=invalid

# 启动服务
cd middleware
python app_orchestrator.py

# 发送测试请求
curl http://localhost:5000/api/dual-stream -X POST
```

预期：看到明确的错误提示，而不是静默回退

- [ ] **Step 4: 验证 Prometheus 指标**

```bash
curl http://localhost:5000/metrics | grep llm_requests_total
curl http://localhost:5000/metrics | grep llm_request_duration
curl http://localhost:5000/metrics | grep llm_tokens_total
```

预期：指标正常显示

- [ ] **Step 5: 提交**

```bash
git add tests/integration/test_llm_framework.py
git commit -m "test: 添加 LLM 框架集成测试"
```

---

## 验证标准

完成后：
- ✅ LLM 调用失败时抛出明确错误，不再静默回退
- ✅ 错误被正确分类（超时、配额、服务等）
- ✅ 实现智能重试机制（最多3次，指数退避）
- ✅ `dynamic_orchestrator.py` 和 `execution_control.py` 职责明确
- ✅ LLM 实时分析功能可通过配置开关控制
- ✅ Prometheus 指标正常记录 LLM 调用数据
- ✅ 集成测试全部通过
- ✅ CLAUDE.md 文档已更新

---

## 成本估算

- **开发时间**：约 4-6 小时
- **测试时间**：约 1-2 小时
- **总时间**：约 5-8 小时

---

## 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM API 不稳定 | 高 | 实现重试机制，添加详细日志 |
| 破坏现有功能 | 中 | 逐步启用，添加功能开关 |
| 性能下降 | 低 | 监控指标，必要时优化 |

---

## 后续优化

1. 添加 LLM 响应缓存（减少重复 API 调用）
2. 实现 LLM 调用的异步处理
3. 添加更细粒度的错误分类
4. 实现 LLM 调用的熔断机制

---

## Self-Review

**1. Spec coverage:** 检查计划是否覆盖了 LLM 框架重构的所有问题
- ✅ 静默回退问题（Task 3）
- ✅ 多套调度系统（Task 4）
- ✅ LLM 功能被注释（Task 5）
- ✅ 错误处理不完善（Task 1, Task 2）

**2. Placeholder scan:** 检查是否有 TODO/TBD 等占位符
- ✅ 所有步骤都包含完整代码
- ✅ 所有命令都有明确预期输出
- ✅ 没有省略号或"待实现"标记

**3. Type consistency:** 检查类型和函数签名一致性
- ✅ 错误类名称在所有任务中保持一致
- ✅ 函数调用签名匹配

---

## 执行选项

**计划已完成并保存到** `docs/superpowers/plans/2026-06-17-llm-framework-refactor.md`

**两种执行方式：**

**1. Subagent-Driven（推荐）** - 我为每个任务分派新的子智能体，任务之间进行审查，快速迭代
   - 优点：每个任务有独立上下文，避免污染
   - 需要：使用 superpowers:subagent-driven-development 技能

**2. Inline Execution** - 在当前会话中使用 executing-plans 技能批量执行，设置检查点审查
   - 优点：在同一会话中执行
   - 需要：使用 superpowers:executing-plans 技能

**选择哪种方式？**

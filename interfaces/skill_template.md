# SKILL.md 模板

> 本文档定义了子智能体技能包的标准文档格式

## 使用说明

1. 复制本模板到子智能体的 `skills/` 目录
2. 重命名为 `SKILL.md`
3. 根据实际技能内容填写各章节
4. 确保与 `skill_registry.json` 保持一致

---

# {技能包名称}

## 版本信息

- **技能包名称**: {技能包名称}
- **技能包ID**: {skill-package-id}
- **版本**: {版本号}
- **所属子智能体**: {子智能体名称}
- **创建日期**: {YYYY-MM-DD}
- **最后更新**: {YYYY-MM-DD}

## 一、技能概述

### 1.1 功能描述

{简要描述本技能包的功能和用途}

### 1.2 核心能力

| 技能ID | 技能名称 | 说明 |
|--------|---------|------|
| {skill-id-1} | {技能名称} | {技能说明} |
| {skill-id-2} | {技能名称} | {技能说明} |

### 1.3 输入输出

**输入**:
```python
{{
    "data": {...},
    "params": {...}
}}
```

**输出**:
```python
{{
    "result": {...},
    "status": "success",
    "message": "..."
}}
```

## 二、技能实现

### 2.1 技能文件结构

```
skills/
└── {skill-package-id}/
    ├── SKILL.md              # 本文档
    ├── scripts/              # 技能脚本
    │   ├── __init__.py
    │   ├── {skill_module_1}.py
    │   └── {skill_module_2}.py
    ├── references/           # 参考文档
    │   ├── {reference_1}.md
    │   └── {reference_2}.md
    └── tests/                # 测试文件
        ├── test_{skill_1}.py
        └── test_{skill_2}.py
```

### 2.2 技能接口

#### {skill_id_1}: {skill_name_1}

**函数签名**:
```python
def {function_name}(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    {函数描述}

    Args:
        input_data: 输入数据
            - param1: {参数说明}
            - param2: {参数说明}

    Returns:
        {
            "result": {结果说明},
            "status": "success|error",
            "message": "状态消息"
        }

    Raises:
        {异常说明}
    """
    pass
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| param1 | str | 是 | {参数说明} |
| param2 | int | 否 | {参数说明} |

**返回值说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| result | Dict | {结果说明} |
| status | str | success 或 error |
| message | str | 状态消息 |

### 2.3 依赖项

```python
# 外部依赖
import numpy as np
import pandas as pd
from scipy import stats

# 内部依赖
from ...utils.logging import get_logger
from ...config import get_config
```

## 三、配置说明

### 3.1 配置参数

本技能包支持的配置参数：

```yaml
{skill_package_id}:
  enabled: true
  config:
    param1: value1
    param2: value2
```

### 3.2 环境变量

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| {ENV_VAR_1} | {说明} | {默认值} |

## 四、使用示例

### 4.1 基本使用

```python
from subagents.{subagent_id}.skills.{skill_package_id}.scripts import {module_name}

# 初始化技能
skill = {ClassName}()

# 调用技能
result = skill.{method_name}(
    param1="value1",
    param2="value2"
)

# 处理结果
if result["status"] == "success":
    print(f"处理成功: {result['result']}")
else:
    print(f"处理失败: {result['message']}")
```

### 4.2 完整示例

```python
# 完整的使用场景示例
```

## 五、错误处理

### 5.1 错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| {ERROR_CODE_1} | {错误说明} | {处理方式} |
| {ERROR_CODE_2} | {错误说明} | {处理方式} |

### 5.2 异常处理

```python
try:
    result = skill.{method_name}(params)
except {ExceptionType} as e:
    logger.error(f"技能执行失败: {e}")
    # 处理异常
```

## 六、性能指标

### 6.1 性能基准

| 指标 | 值 | 说明 |
|------|---|------|
| 平均响应时间 | {X}ms | {说明} |
| 吞吐量 | {X}req/s | {说明} |
| 资源占用 | {X}MB | {说明} |

### 6.2 性能优化

{性能优化建议}

## 七、测试

### 7.1 单元测试

```bash
# 运行单元测试
pytest skills/{skill_package_id}/tests/
```

### 7.2 测试覆盖

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| {module_1} | {X}% | {说明} |
| {module_2} | {X}% | {说明} |

## 八、更新日志

### v1.0.0 (YYYY-MM-DD)
- 初始版本
- 实现 {功能1}
- 实现 {功能2}

### v1.1.0 (YYYY-MM-DD)
- 新增 {功能}
- 优化 {性能}
- 修复 {问题}

## 九、参考文档

- [技能接口规范](../../interfaces/skill_interface.md)
- [子智能体通信协议](../../interfaces/subagent_protocol.md)
- [配置验证规范](../../interfaces/config_validation.md)

## 十、附录

### A. 配置文件示例

见 `references/config_example.yaml`

### B. 数据格式示例

见 `references/data_format_example.json`

---

**文档维护**: {维护者}
**文档版本**: v1.0
**最后审核**: {YYYY-MM-DD}

# 技能接口规范

## 技能定义

技能（Skill）是子智能体的核心能力单元，封装了特定的专业功能。

## 技能结构

每个技能必须包含：

```
skill-name-core/
├── SKILL.md          # 技能说明文档
├── scripts/          # 脚本代码
│   ├── __init__.py
│   └── *.py
├── references/       # 参考知识
│   ├── standards.md
│   ├── patterns.md
│   └── best_practices.md
└── assets/          # 资产文件
    ├── charts/
    └── templates/
```

## Python接口规范

### 必须实现的接口

```python
class Skill:
    def __init__(self, config=None):
        """初始化技能"""
        pass

    def execute(self, data, **kwargs):
        """
        执行技能

        Args:
            data: 输入数据
            **kwargs: 额外参数

        Returns:
            技能执行结果
        """
        pass

    def validate(self, data):
        """
        验证输入数据

        Args:
            data: 输入数据

        Returns:
            (is_valid, error_message)
        """
        pass
```

### 命令行接口规范

所有技能必须支持命令行调用：

```bash
# 显示帮助
python skill.py --help

# 执行技能
python skill.py --input data.json --output result.json

# 只生成报告
python skill.py --input data.json --report-only
```

## SKILL.md规范

每个技能必须有SKILL.md文档，包含：

### 1. 技能概述
- 技能名称和版本
- 功能描述
- 适用场景

### 2. 使用方法
- Python API使用
- 命令行使用
- 参数说明

### 3. 输入输出格式
- 输入数据格式
- 输出数据格式
- 参数说明

### 4. 最佳实践
- 使用建议
- 性能优化
- 错误处理

### 5. 示例代码
- 完整示例
- 常见用例

## 技能注册

### 技能注册表
位置：`shared/configs/skill_registry.json`

```json
{
  "skills": [
    {
      "id": "time_alignment",
      "name": "时间对齐技能",
      "version": "1.0.0",
      "agent": "treatment-efficiency-agent",
      "script": "skills/efficiency-analysis-core/scripts/time_alignment.py",
      "api": "TimeAlignmentSkill"
    },
    {
      "id": "removal_rate",
      "name": "去除率计算技能",
      "version": "1.0.0",
      "agent": "treatment-efficiency-agent",
      "script": "skills/efficiency-analysis-core/scripts/removal_rate.py",
      "api": "RemovalRateSkill"
    }
  ],
  "version": "2.0.0",
  "last_updated": "2026-04-14T14:00:00Z"
}
```

## 技能迁移规范

### 从旧框架迁移

1. **复制脚本**：将.py文件复制到新位置
2. **更新导入**：修改import路径
3. **创建SKILL.md**：编写完整文档
4. **测试功能**：确保功能正常
5. **更新注册表**：注册到skill_registry.json
6. **删除旧文件**：删除原位置的文件

### 迁移检查清单

- [ ] 脚本已复制到新位置
- [ ] 导入路径已更新
- [ ] SKILL.md已创建
- [ ] 功能测试通过
- [ ] 已注册到skill_registry.json
- [ ] 旧文件已删除

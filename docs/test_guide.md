# 综合测试使用指南

## 快速开始

### 基本测试（推荐）

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --skip-stream
```

### 详细输出

```bash
python run_comprehensive_tests.py --skip-stream --verbose
```

### 完整测试（含Flask）

```bash
# 先启动Flask（另一个终端）
cd middleware
python app_orchestrator.py

# 运行测试
python run_comprehensive_tests.py
```

## 命令行选项

| 选项 | 说明 |
|-----|------|
| `--skip-stream` | 跳过实时流测试（推荐，Flask未启动时） |
| `--verbose` | 显示详细测试输出 |
| `--output-dir DIR` | 指定报告输出目录（默认test_reports/） |
| `--stop-on-fail` | 遇到失败立即停止 |

## 报告位置

测试完成后，报告生成在 `test_reports/` 目录：
- `report_YYYYMMDD_HHMMSS.html` - HTML可视化报告
- `report_YYYYMMDD_HHMMSS.json` - JSON机器可读报告

## 测试层级

1. **ConfigTestLayer** - 配置文件验证
2. **UnitTestLayer** - 核心模块单元测试
3. **IntegrationTestLayer** - 模块集成测试
4. **E2ETestLayer** - pytest集成测试套件
5. **StreamTestLayer** - Flask实时流测试（可选）

## 故障排查

### 模块导入失败

检查Python路径是否正确，确保在项目根目录执行。

### pytest测试失败

查看详细输出：`python run_comprehensive_tests.py --verbose`

### Flask测试跳过

这是正常的，Flask未启动时StreamTestLayer会自动跳过。

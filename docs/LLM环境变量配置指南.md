# LLM环境变量配置指南（第3阶段更新）

## 概述

本系统支持使用自定义的Claude API端点（通过API网关），而不是直接暴露API密钥。

**配置方式**：
- ✅ **推荐**：使用 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`（自定义API端点）
- ⚠️ **向后兼容**：使用 `ANTHROPIC_API_KEY`（直接连接Anthropic官方端点）

---

## 方法1：使用自定义API端点（推荐）

### 步骤1：配置环境变量

编辑 `middleware/.env` 文件：

```bash
# ==================== Claude API配置 ====================
# 方式1：使用自定义API端点（推荐）
ANTHROPIC_AUTH_TOKEN=sk-ant-your-actual-auth-token-here
ANTHROPIC_BASE_URL=https://your-api-gateway.com/v1

# 模型配置
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 步骤2：配置说明

**ANTHROPIC_AUTH_TOKEN**：
- 这是您的API认证令牌（sk-ant-xxx格式）
- 从您的API网关或代理服务获取
- 不要将真实的token提交到代码仓库

**ANTHROPIC_BASE_URL**：
- 您的自定义API网关地址
- 例如：`https://your-api-gateway.com/v1` 或 `http://localhost:8080/v1`
- 必须包含 `/v1` 路径

### 步骤3：验证配置

```bash
# 启动系统
python middleware/app.py

# 检查日志，应该看到：
# ✅ ANTHROPIC_AUTH_TOKEN: 已配置 (sk-ant-...)
# ✅ ANTHROPIC_BASE_URL: https://your-api-gateway.com/v1
```

---

## 方法2：使用默认端点（向后兼容）

如果您直接使用Anthropic官方API：

### 配置环境变量

编辑 `middleware/.env` 文件：

```bash
# ==================== Claude API配置 ====================
# 方式2：使用默认端点（向后兼容）
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
ANTHROPIC_MODEL=claude-3-5-net-20250219

# 不需要ANTHROPIC_BASE_URL（使用默认）
```

---

## 优先级规则

系统按以下优先级查找配置：

1. **优先使用**：`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
2. **降级使用**：`ANTHROPIC_API_KEY`（仅当AUTH_TOKEN未设置时）

```python
# 代码逻辑（llm_coordinator.py）
auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
base_url = os.getenv("ANTHROPIC_BASE_URL")

if base_url:
    client = Anthropic(api_key=auth_token, base_url=base_url)
else:
    client = Anthropic(api_key=auth_token)
```

---

## 安全最佳实践

### ✅ 推荐做法

1. **使用环境变量**：
   - ✅ 将敏感信息放在 `.env` 文件中
   - ❌ 不要硬编码在代码里
   - ✅ `.env` 文件不提交到Git仓库

2. **使用API网关**：
   - ✅ 通过API网关统一管理访问
   - ✅ 便于轮换和监控
   - ✅ 隐藏真实API密钥

3. **最小权限原则**：
   - ✅ 只授予必要的权限
   - ✅ 定期轮换token
   - ✅ 监控API使用情况

### ❌ 避免的做法

1. **硬编码密钥**：
   ```python
   # ❌ 错误示例
   API_KEY = "sk-ant-xxx"  # 不要这样做！

   # ✅ 正确示例
   API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN")
   ```

2. **提交敏感信息到Git**：
   ```bash
   # 确保.gitignore包含.env
   echo ".env" >> .gitignore
   ```

---

## 故障排查

### 问题1：LLM功能不可用

**症状**：
```
⚠️ ANTHROPIC_AUTH_TOKEN: 未配置
```

**解决方案**：
1. 检查 `.env` 文件是否存在
2. 确认 `ANTHROPIC_AUTH_TOKEN` 已设置
3. 重启Flask服务

### 问题2：API调用失败

**症状**：
```
❌ API调用失败: Connection error
```

**解决方案**：
1. 检查 `ANTHROPIC_BASE_URL` 是否正确
2. 测试API网关是否可访问：
   ```bash
   curl https://your-api-gateway.com/v1/messages
   ```
3. 检查网络连接和防火墙设置

### 问题3：认证失败

**症状**：
```
❌ 401 Unauthorized
```

**解决方案**：
1. 确认 `ANTHROPIC_AUTH_TOKEN` 格式正确（sk-ant-xxx）
2. 检查token是否有效
3. 联系API网关管理员

---

## 测试配置

### 测试脚本

```python
# 测试环境变量配置
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 检查配置
auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
base_url = os.getenv("ANTHROPIC_BASE_URL")

print("配置检查：")
print(f"  AUTH_TOKEN: {'已设置' if auth_token else '未设置'}")
print(f"  BASE_URL: {base_url if base_url else '使用默认端点'}")

if auth_token:
    # 尝试初始化客户端
    from anthropic import Anthropic
    try:
        if base_url:
            client = Anthropic(api_key=auth_token, base_url=base_url)
        else:
            client = Anthropic(api_key=auth_token)
        print("✅ Anthropic客户端初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
```

运行测试：
```bash
cd E:\project\Ecological_env
python test_llm_config.py
```

---

## 更新日志

**2026-04-20**：
- ✅ 新增 `ANTHROPIC_AUTH_TOKEN` 支持
- ✅ 新增 `ANTHROPIC_BASE_URL` 支持
- ✅ 更新 llm_coordinator.py 初始化逻辑
- ✅ 更新 middleware/.env 和 .env.example
- ✅ 保持向后兼容（仍支持 ANTHROPIC_API_KEY）

---

**文档版本**：1.0.0
**更新时间**：2026年4月20日

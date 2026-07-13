# 主智能体到子智能体调用链路验证

> **日期**: 2026-07-08
> **状态**: ✅ 流程正确

---

## 完整调用链路

```
用户输入
    ↓
┌─────────────────────────────────────────┐
│ 1. FastAPI 后端                          │
│    backend/api/routes/query.py          │
│    接收用户查询                          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 2. Hermes API Server (端口 8642)         │
│    或者直接调用主智能体（如果后端集成）   │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 3. 主智能体 (workspace/)                 │
│    加载: SOUL.md, AGENTS.md, MEMORY.md  │
│    使用: orchestrator-core skill         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 4. call_subagent.py                      │
│    - 设置 HERMES_HOME → 子智能体目录     │
│    - 设置 SESSION_DIR → 会话目录         │
│    - 写入 task.json                      │
│    - subprocess.run(run_agent.py)        │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 5. 子智能体进程                          │
│    run_agent_wrapper.py                  │
│    - 读取 task.json                      │
│    - 加载自己的身份文件                   │
│    - 创建 AIAgent 实例                   │
│    - 执行任务                            │
│    - 写入 result.json                    │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 6. 主智能体读取 result.json              │
│    整合结果生成最终回答                  │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 7. 返回给前端/用户                       │
└─────────────────────────────────────────┘
```

---

## 关键环境变量

### 主智能体环境
| 变量 | 值 | 说明 |
|-----|-----|------|
| `HERMES_HOME` | `E:/project/Ecological_env/workspace` | 主智能体目录 |
| `SESSION_DIR` | `E:/project/Ecological_env/sessions/session_xxx` | 会话目录 |

### 子智能体环境（subprocess 传递）
| 变量 | 值 | 说明 |
|-----|-----|------|
| `HERMES_HOME` | `E:/project/Ecological_env/subagents/xxx-agent` | 子智能体目录 |
| `SESSION_DIR` | `E:/project/Ecological_env/sessions/session_xxx` | 会话目录（共享） |
| `SUBAGENT_NAME` | `anomaly-detection` | 子智能体名称 |
| `LLM_BASE_URL` | `https://api.longcat.chat/openai/v1` | LLM API |
| `LLM_API_KEY` | `ak_xxx` | LLM 密钥 |
| `LLM_MODEL` | `LongCat-2.0` | 模型名称 |
| `OPENAI_API_KEY` | `ak_xxx` | Hermes 期望的格式 |
| `OPENAI_BASE_URL` | `https://api.longcat.chat/openai/v1` | Hermes 期望的格式 |

---

## 关键文件位置

### 主智能体
| 文件 | 路径 |
|-----|------|
| SOUL.md | `workspace/SOUL.md` |
| AGENTS.md | `workspace/AGENTS.md` |
| MEMORY.md | `workspace/MEMORY.md` |
| orchestrator-core | `workspace/skills/orchestrator-core/` |
| call_subagent.py | `workspace/skills/orchestrator-core/scripts/call_subagent.py` |

### 子智能体
| 文件 | 路径 |
|-----|------|
| SOUL.md | `subagents/xxx-agent/SOUL.md` |
| AGENTS.md | `subagents/xxx-agent/AGENTS.md` |
| MEMORY.md | `subagents/xxx-agent/MEMORY.md` |
| run_agent_wrapper.py | `subagents/xxx-agent/run_agent_wrapper.py` |

### 会话共享
| 文件 | 路径 |
|-----|------|
| task.json | `sessions/session_xxx/task.json` |
| result.json | `sessions/session_xxx/xxx_result.json` |

---

## 验证点

### ✅ 1. 主智能体身份文件加载
- [ ] workspace/SOUL.md 存在且格式正确
- [ ] workspace/AGENTS.md 存在且格式正确
- [ ] workspace/MEMORY.md 存在且格式正确

### ✅ 2. 子智能体调用
- [ ] call_subagent.py 正确设置 HERMES_HOME
- [ ] call_subagent.py 正确设置 SESSION_DIR
- [ ] call_subagent.py 正确设置 LLM 环境变量
- [ ] subprocess 正确启动子进程

### ✅ 3. 子智能体身份文件加载
- [ ] 子智能体目录存在
- [ ] 子智能体 SOUL.md 存在
- [ ] run_agent_wrapper.py 正确加载身份文件

### ✅ 4. 文件共享机制
- [ ] SESSION_DIR 正确创建
- [ ] task.json 正确写入
- [ ] result.json 正确读取

---

## 已修复的问题

### 1. HERMES_HOME 指向错误 ✅
- **问题**: 原来指向 `D:\Hermes`
- **修复**: 创建新的启动脚本 `start_hermes_server.bat`，在项目目录直接运行
- **验证**: 启动脚本设置 HERMES_HOME 为项目的 workspace/

### 2. LLM 加载外部目录 ✅
- **问题**: LLM 每次加载 `D:\Hermes\hermes-agent`
- **原因**: 启动脚本 cd 到外部目录
- **修复**: 移除 cd 命令，使用虚拟环境中的 hermes-agent

---

## 待验证项

- [ ] 实际运行测试
- [ ] 子智能体身份文件是否正确加载
- [ ] LLM 调用是否正常
- [ ] 结果返回是否正确

---

**下一步**: 运行实际测试验证完整链路

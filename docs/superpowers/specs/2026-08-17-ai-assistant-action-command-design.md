# AI 智能助手动作指令系统设计

> 日期：2026-08-17
> 状态：已确认（用户批准）
> 目标：把前端右下角 AI 智能助手从"问答"升级为"指挥"——用户说自然语言指令，大屏实时执行动作（切视图/标注异常/调阈值/按需调度算子）

## 背景与动机

当前 AI 智能助手与左侧智能体问答功能重复（都走问答管线）。用户希望区分：左侧保持问答不变，AI 助手变成**动作指令入口**——像"街道监控里说'检测人脸'→调用算法→大屏框出"一样，在废水监测场景实现"说'检测pH平稳异常'→调度算子→曲线上标注"。

## 核心概念：两类动作

| 类型 | 特点 | 例子 |
|---|---|---|
| **UI 动作** | 纯前端状态切换，秒回 | 切视图、切时间范围、调阈值线 |
| **算法动作** | 取数+跑算子+结果标注，1-3秒 | 平稳检测、突变检测、孤立森林检测 |

## 整体架构（三路分流）

```
用户在 AI 助手说话
    ↓
backend /api/query/stream（现有，不改）
    ↓
主智能体（加载 2 个技能：orchestrator-core + action-command-core）
    ↓ LLM 语义分流
    ├── ① UI 动作（set_view / set_time_range）
    │      → 输出 actionData JSON → SSE action 事件 → 前端 Dispatcher → 大屏秒变
    ├── ② 算法动作（run_detector）
    │      → 主智能体 tool call 调 run_detector.py（轻量脚本）
    │      → 脚本取数(InfluxDB) + 跑算子(shared/operators) 1-3秒
    │      → 结果 + actionData → SSE action 事件 → 前端标注
    └── ③ 问答/综合分析
           → 走现有 orchestrator-core → 子智能体管线（一行不改）
```

**关键设计决策**：
- **技能放主智能体**（`skills/` 根目录，与 orchestrator-core 并排）：意图识别是 LLM 层面的事，不需要子智能体
- **算法动作用轻量脚本而非子智能体**：算法调用是确定性操作（LLM 只做意图识别+参数提取），脚本 1-3 秒 vs 子智能体 30-60 秒；对标"检测人脸→直接跑 YOLO"的模式
- **复用现有 SSE 流**：action 作为新事件类型，与 progress/delta/done 并排，零新基础设施
- **左侧问答完全不动**：AI 助手与问答走同一后端/agent，区别只在主智能体内分流

## 新增组件（4 个）

### 1. `skills/action-command-core/SKILL.md`（主智能体技能）
- 三路分流判断原则：用户在"要答案"（→问答）还是在"下指令"（→动作），还是"综合分析"（→子智能体管线）
- 5 个动作 schema（cmd + params）
- 15 个多样化例子（覆盖固定说法/口语/变体）
- **写判断原则而非关键词表**——LLM 语义理解，"pH那条线太扁了帮我看看"也能识别为平稳检测

### 2. `skills/action-command-core/scripts/run_detector.py`（轻量算法脚本，~150行）
- 输入：`{"algorithm":"constant|changepoint|iforest", "indicator":"pH|COD|TN|NH3-N|TP|SS", "start":"YYYY-MM-DD", "end":"YYYY-MM-DD"}`
- 流程：InfluxDB 取数 → 调 shared/operators/ 对应算子 → 输出
- 输出：`{"anomalies":[{"timestamp","value","type","segment"}], "actionData":{"cmd":"run_detector","annotations":[...]}}`
- 纯确定性计算，不经 LLM

### 3. `tool_registration.py` 注册新工具（~30行）
- 主智能体新增 `run_detector` tool schema（与现有 4 个编排工具并排，共 7 个工具）
- handler 直接 subprocess 跑 run_detector.py

### 4. 前端 `ActionDispatcher`（~150行 Vue composable）
- SSE 事件处理新增 `action` 类型
- cmd 路由：set_view→切大屏指标 / set_time_range→切时间 / run_detector→标注数据传 ECharts
- 大屏页面暴露响应式状态（当前指标/时间范围/标注列表）

## 第一版动作词表

| cmd | 类型 | 用户说（举例，非穷举） | 效果 |
|---|---|---|---|
| `set_view` | UI | "只看pH和COD" / "切到进水" | 大屏切换指标/进出水 |
| `set_time_range` | UI | "看最近一周" / "看7月14号" | 大屏切时间范围 |
| `run_detector`(constant) | 算法 | "检测pH有没有平稳异常" | ConstantDetector，曲线高亮平稳段 |
| `run_detector`(changepoint) | 算法 | "检测COD突变" | ChangePointDetector，标注突变点 |
| `run_detector`(iforest) | 算法 | "用孤立森林检测异常" | IsolationForest，标注离群点 |

兜底：非动作（"7月14号pH是多少"）→ 问答管线；综合分析（"全面研判"）→ 子智能体管线。

## 数据流（算法动作完整时序）

```
用户："检测7月14号pH有没有平稳异常"
  ↓ SSE POST /api/query/stream
主智能体读 action-command-core 技能
  → tool call run_detector(algorithm=constant, indicator=pH, start/end=07-14)
  → 脚本(2秒)：取24条pH → ConstantDetector → 平稳段[{00:00-08:00},{15:00-23:00}]
  → 返回 actionData + 简短文字
  ↓ SSE: {"type":"action","actionData":{...}}
  ↓ SSE: {"type":"delta","text":"检出2段平稳异常，已在大屏标注"}
前端 Dispatcher → 大屏 ECharts markArea 高亮      总耗时 ~3秒
```

## 错误处理

| 情况 | 处理 |
|---|---|
| LLM 识别不出动作/参数不全 | 回退走问答路（答非所问好过执行错动作） |
| 指标名不存在 | agent 反问澄清，不执行 |
| 算子跑失败（数据空等） | 返回错误文字，大屏不变 |
| 前端收到不认识的 cmd | 忽略 + 控制台警告（向前兼容） |

## 测试

- run_detector.py 单元测试：mock 数据跑 3 个算子，验证输出格式
- 技能分流手动测试：10 句各种说法验证三路分流准确
- 端到端：AI 助手说"检测pH平稳"→ 大屏 3 秒内出标注

## 技术栈

全部现有：Vue3 + FastAPI + Hermes + ctgu-vlm + shared/operators 算子库。零新依赖。

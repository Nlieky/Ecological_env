# 全系统助手 Skill 与上下文排查记录

## 范围

按用户要求不增加校验器、不穷举自然语言规则。排查前端、代理、运行时与实际模型调用消息，验证通用澄清。所有模型测试仅准备候选；没有执行错误候选或业务写入。没有修改生产提示词装配、身份、契约、准备器或运行服务；本轮新增诊断脚本并为现有浏览器脚本保存合成测试请求。

## 确认的证据

1. 前端 stores/assistant.ts 在加入新问题前采集最近20条complete消息，保留user/assistant及各自正文；另传本轮query、清洗后的当前context和pending。浏览器真实三轮请求见 logs/assistant-verification/context-browser-all-turns/results.json；history条数依次为0、2、4。
2. backend RespondRequest验证后，assistant_service以model_dump透传给8642；SystemInteractionRuntime把history按角色顺序传入Hermes，并将query/context/pending组成当前user消息。此次短多轮中没有截断或丢失历史。
3. 使用同一AgentService工厂、真实Hermes循环和实际provider传输方法捕获API消息结构。最终system约17294字符，包含完整当前Skill；professional AGENTS.md和MEMORY.md未载入，tools为0，response_format为json_object。原问题和上一轮追问按user/assistant顺序保留，当前context.plant为null。只保存system哈希、长度与匹配标记，不持久化完整system或凭据。
4. IDENTITY.md和SOUL.md仍按设计共享；其中“全部价值在于编排子智能体”“先拿结果而非带着问题”等专业职责指引，与侧栏先澄清的职责形成适用范围张力。Skill位于能力契约之前，而部分筛选schema不要求plant。这是冲突风险，不等于已证明的唯一根因。

## 对照结果

脚本 scripts/diagnose_assistant_context.py 使用合成输入，诊断变体只在该独立进程中生效，不部署到8000/8642。`--repeat 3` 为两个固定输入各重复3次，不是6种独立业务场景，也不是统计显著性结论。

| 对照 | 有澄清且无候选/交接 | 总请求 |
|---|---:|---:|
| 当前生产装配baseline | 2 | 6 |
| 仅补模式优先级说明 | 1 | 6 |
| Skill置于契约后并补模式说明 | 2 | 6 |

首次小样本模式说明曾2/2补问，但扩大重复后未稳定改善，因此不能归因为单纯排序或缺少一句优先级，也没有据此修改生产装配。详细记录位于 logs/assistant-verification/context-probe-baseline-repeated、context-probe-scope-repeated、context-probe-combined。

浏览器实际/events入口再次失败：第一轮和第二轮提前生成不含plant的metrics.filter。观察模式仍发送其余补充，捕获后续请求内真实history，确认原问题、模型回答与用户补充的角色顺序未丢失。观察模式不执行任何候选，未点击或加载错误厂站。首轮即失败的原始停止记录另见 context-browser-trace。

## 结论与未完成项

已排除本次复现中的Skill未加载、短多轮历史丢失、角色顺序错误和工具泄入。剩余问题为当前完整提示词环境下的澄清行为不稳定；专业身份适用范围、Skill中动作优先表述、schema可选参数与语义完整性之间仍需统一设计，不能把未经复现的推测说成已修复原因。

本轮未把失败重试到一次成功当通过，未新增用户拒绝的业务校验器。通用澄清仍未通过，不应交付为已修复。自动刷新与检测候选竞态、专业主页面旧动作分类器仍未在本轮修复。

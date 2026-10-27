# 全系统助手意图澄清实施计划

> 使用 writing-plans 记录用户已批准的边界，原目录内执行；不提交、推送、新建服务或扩展权限。

**目标：** 页面展示与专业分析分流；目的、目标页或对象不明确时先补问，无动作及handoff；用户补充后保留已确认参数。

**架构：** 仅修改现有 system-interaction-core Skill，继续使用现有message/空actions表达语义澄清、history延续澄清；已选能力的字段缺失继续使用现有intent/pending。不新增协议、关键词路由或自然语言特判。专业主页面旧分类器和自动刷新竞态不在本次修改范围。

**测试：** 新建 scripts/verify_assistant_intent_clarification.py，调用真实8000/8642模型候选接口，不执行检测或任何业务写入。不同页面/指标/同义表达验证路由、无厂站补问、跨轮保留参数、明确分析交接及既有导航。语义追问不锁定逐字文案。

- [x] RED：旧Skill运行真实场景，保存每轮响应及断言失败。
- [x] 修改：修改三类请求表、歧义优先级与协议说明，移除数据取数一律交接的冲突；不写入用户案例。但未达成全部GREEN。
- [x] 加载：核对8642进程命令，仅重启原Agent加载Skill，等待health初始化完成。
- [x] 验证：同一脚本重跑；相关pytest；检查生成契约一致性及修改范围diff。失败如实记录。
- [x] 复核：检查提示词前后无冲突，记录准确测试范围与未解决问题，不宣称所有自然语言已可靠。
- [ ] 全部行为通过：未知厂站的候选门禁仍失败，需要准备器确定性约束；等待用户确认扩大本轮仅Skill的范围。

## 执行记录

后续用户否定新增校验器，要求先排查现有Skill与上下文；本轮据此只补诊断、不修改准备器。详见 docs/superpowers/specs/2026-10-19-assistant-context-investigation.md。已证实Skill与短多轮历史完整到达实际provider请求，提示词排序/优先级对照未稳定改善；通用澄清仍未通过，未部署诊断变体。

旧Skill基线：8组中3组失败。原测试曾错误使用指标页不支持的7d，已在修改Skill前改为支持的1h并单独复现缺厂站失败，未通过放宽断言掩盖问题。基线记录 intent-clarification-red 及 intent-clarification-red-corrected。

Skill两版均真实加载后复验；最终8组6组通过（明确指标页、指标页上下文、大屏上下文、目的澄清后专业交接、明确专业分析、独立导航），2组失败（厂站未知直接或在多轮中提前生成metrics.filter）。浏览器从/events提交用户原问题也复现，未点击错误候选，没有业务写入。记录 logs/assistant-verification/intent-clarification-final/results.json 和 intent-clarification-browser/results.json。

相关自动测试：tests/assistant 与 tests/system/test_system_interaction_turn.py 共76项通过、9项已有警告；契约生成一致性通过。没有前端生产代码/准备器/契约改动，不将该结果当作真实模型行为全部通过。

结论：提示词边界已修订、原服务已加载，但对象完整性规则不能仅靠模型服从提示词保证。建议下一步为准备器添加声明式对象前置条件，保持合法部分筛选和多轮pending，不增加自然语言关键词特判。尚未实施此扩展，自动刷新竞态也未在本轮修复。保留当前分支、未提交或推送。

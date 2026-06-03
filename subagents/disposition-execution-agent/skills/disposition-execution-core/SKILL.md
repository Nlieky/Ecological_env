# 研判预警与处置执行核心技能包

## 技能描述
本技能包提供融合共识、预警分级、工单生成、行动执行和报告生成能力，完成从违规识别到处置执行的闭环。

## 核心脚本

### 1. alert_classifier.py (AlertClassifier)
**功能**: 三级预警分级
- classify_alert(): 对异常和违规结果进行预警分级
- 支持一般/较重/严重三级预警

### 2. work_order_generator.py (WorkOrderGenerator)
**功能**: 处置工单生成
- generate_work_order(): 生成标准化处置工单
- 工单包含：数据溯源、核查要点、法规条款、历史参考

### 3. action_executor.py (ActionExecutor)
**功能**: 行动执行
- execute(): 并行执行多渠道推送
- 支持渠道：RegulatoryPlatformPush, FeishuPush, LocalArchive
- 接口抽象：PushChannel 基类

### 4. consensus_engine.py (ConsensusEngine)
**功能**: 融合共识算法
- fuse_results(): 融合异常检测和规则推理结果
- adapt_weights(): 动态调整权重
- 支持场景化融合策略（default, critical, normal）
- 提供融合过程元数据和自适应权重信息
- 配置文件：shared/configs/consensus_config.yaml

### 5. report_generator.py (ReportGenerator)
**功能**: 报告生成
- generate_alert_report(): 生成预警报告
- generate_summary_report(): 生成汇总报告
- generate_trend_report(): 生成趋势分析报告
- 支持 JSON 和 Markdown 输出格式

## LLM决策点
1. 融合策略: 根据场景动态调整定量定性权重
2. 分级判定: 综合判断预警级别
3. 工单内容: 根据违规类型生成个性化工单

## 输出格式
标准化预警信息、处置工单和报告

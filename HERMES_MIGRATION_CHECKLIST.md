# Hermes框架迁移验收检查清单

## 目录结构验收
- [ ] knowledge/ 已移入 shared/knowledge/
- [ ] 每个子智能体都有 memory/ 目录
- [ ] .hermes/ 目录和配置文件已创建
- [ ] orchestrator-core 已备份到参考目录

## 三库访问验收
- [ ] shared/operators/ 目录结构完整
- [ ] shared/data/ 目录结构完整
- [ ] shared/knowledge/ 目录结构完整（从根目录移入）

## 配置文件验收
- [ ] .hermes/config.yaml 已创建并包含正确配置
- [ ] shared/configs/hermes_config.yaml 已创建
- [ ] 接口标准化文档已创建

## 文档更新验收
- [ ] docs/architecture.md 已创建并反映新架构
- [ ] CLAUDE.md 已更新说明Hermes框架
- [ ] README.md 已更新目录结构
- [ ] 接口标准化文档完整

## 文件清理验收
- [ ] 过时专利文档已删除
- [ ] 临时垃圾文件已删除
- [ ] 过时计划文档已归档

## 下一步：Hermes框架集成测试
- [ ] 验证Hermes框架可用性
- [ ] 测试delegate_tool.py调用机制
- [ ] 验证主智能体启动
- [ ] 验证子智能体调用

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果解释与输出脚本
功能：接收子智能体执行结果，由大模型生成自然语言报告

说明：此脚本由主智能体调用，用于将各子智能体的执行结果
整合，由大模型读取主智能体身份和知识库，生成符合规范的
自然语言分析报告。
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

# 添加项目路径
# 尝试多种方式找到项目根目录
possible_roots = [
    Path(__file__).parent.parent.parent.parent.parent.parent,  # 从scripts目录向上
    Path.cwd().parent,  # 从当前工作目录
    Path(__file__).resolve().parent.parent.parent.parent.parent,  # 解析后的路径
]

for root in possible_roots:
    if (root / "workspace").exists() and (root / "subagents").exists():
        project_root = root
        break
else:
    # 默认使用相对路径
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent

sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBase:
    """知识库内容"""
    regulations: Dict[str, str] = field(default_factory=dict)
    patterns: Dict[str, str] = field(default_factory=dict)
    expert: Dict[str, str] = field(default_factory=dict)


class MasterAgentKnowledgeLoader:
    """主智能体知识与身份加载器"""

    def __init__(self, workspace_path: Path = None):
        """初始化加载器"""
        if workspace_path is None:
            workspace_path = project_root / "workspace"

        self.workspace_path = workspace_path
        self.subagents_dir = project_root / "subagents"

    def load_master_identity(self) -> Dict[str, str]:
        """
        加载主智能体完整身份

        Returns:
            身份文件内容字典
        """
        identity_files = {
            "IDENTITY": self.workspace_path / "IDENTITY.md",
            "AGENTS": self.workspace_path / "AGENTS.md",
            "MEMORY": self.workspace_path / "MEMORY.md",
            "HEARTBEAT": self.workspace_path / "HEARTBEAT.md",
            "TOOLS": self.workspace_path / "TOOLS.md",
            "SKILL": self.workspace_path / "skills" / "orchestrator-core" / "SKILL.md"
        }

        identity = {}
        for name, path in identity_files.items():
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        identity[name] = f.read()
                    logger.info(f"[IDENTITY] 已加载 {name}")
                except Exception as e:
                    logger.warning(f"[IDENTITY] 无法加载 {name}: {e}")
                    identity[name] = ""
            else:
                logger.warning(f"[IDENTITY] 文件不存在: {path}")
                identity[name] = ""

        return identity

    def load_knowledge_base(self) -> KnowledgeBase:
        """
        加载知识库

        Returns:
            KnowledgeBase对象
        """
        kb = KnowledgeBase()

        # 加载法规知识
        regulations_dir = self.subagents_dir / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "references" / "regulations"
        if regulations_dir.exists():
            for file in regulations_dir.glob("*.md"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        kb.regulations[file.stem] = f.read()
                    logger.info(f"[KB] 已加载法规: {file.stem}")
                except Exception as e:
                    logger.warning(f"[KB] 无法加载法规 {file}: {e}")

        # 加载违规模式知识
        patterns_dir = self.subagents_dir / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "references" / "expert_experience"
        if patterns_dir.exists():
            for file in patterns_dir.glob("*.md"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        kb.patterns[file.stem] = f.read()
                    logger.info(f"[KB] 已加载模式: {file.stem}")
                except Exception as e:
                    logger.warning(f"[KB] 无法加载模式 {file}: {e}")

        return kb


class ResultInterpretationModule:
    """结果解释与输出模块"""

    def __init__(self, llm_client=None):
        """
        初始化模块

        Args:
            llm_client: 大模型客户端（可选）
        """
        self.knowledge_loader = MasterAgentKnowledgeLoader()
        self.llm_client = llm_client
        logger.info("[INIT] 结果解释与输出模块初始化完成")

    def interpret_results(self, execution_results: Dict[str, Any],
                         task_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解释执行结果并生成报告

        Args:
            execution_results: 各子智能体的执行结果
            task_info: 任务信息

        Returns:
            包含解释结果的字典
        """
        timestamp = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("[INTERPRET] 开始解释执行结果")
        logger.info("=" * 60)

        # 1. 加载主智能体身份
        master_identity = self.knowledge_loader.load_master_identity()

        # 2. 加载知识库
        knowledge_base = self.knowledge_loader.load_knowledge_base()

        # 3. 分析执行结果
        analysis = self._analyze_execution_results(execution_results)

        # 4. 生成报告
        if self.llm_client is not None:
            report = self._generate_llm_report(
                master_identity, knowledge_base, analysis, task_info
            )
        else:
            report = self._generate_template_report(analysis, task_info)

        logger.info("[INTERPRET] 报告生成完成")
        logger.info("=" * 60)

        return {
            "timestamp": timestamp,
            "analysis": analysis,
            "report": report,
            "status": "success"
        }

    def _analyze_execution_results(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析执行结果"""
        analysis = {
            "agents_executed": [],
            "has_violation": False,
            "violations": [],
            "anomalies": [],
            "suspicion_level": "low",
            "data_quality": {},
            "features": {}
        }

        for agent_id, result in execution_results.items():
            analysis["agents_executed"].append(agent_id)

            if result.get("status") == "error":
                analysis["errors"] = analysis.get("errors", [])
                analysis["errors"].append({
                    "agent": agent_id,
                    "error": result.get("error", "Unknown error")
                })
                continue

            # 提取各子智能体的关键结果
            if agent_id == "data-governance-agent":
                analysis["data_quality"] = result.get("quality_report", {})
            elif agent_id == "feature-analysis-agent":
                analysis["features"] = result.get("features", {})
            elif agent_id == "anomaly-detection-agent":
                analysis["anomalies"] = result.get("anomalies", [])
                if result.get("has_anomaly"):
                    analysis["has_anomaly"] = True
            elif agent_id == "rule-reasoning-agent":
                analysis["violations"] = result.get("violations", [])
                analysis["suspicion_level"] = result.get("suspicion_level", "low")
                if result.get("has_violation"):
                    analysis["has_violation"] = True

        return analysis

    def _generate_llm_report(self, master_identity: Dict[str, str],
                            knowledge_base: KnowledgeBase,
                            analysis: Dict[str, Any],
                            task_info: Dict[str, Any]) -> str:
        """
        使用大模型生成报告

        Args:
            master_identity: 主智能体身份
            knowledge_base: 知识库
            analysis: 分析结果
            task_info: 任务信息

        Returns:
            自然语言报告
        """
        # 构建系统提示词（主智能体身份）
        system_prompt = f"""你是废水虚假排放智能监测主智能体。

{master_identity.get('IDENTITY', '')[:500]}

{master_identity.get('SOUL', '')[:500]}

你的任务是基于子智能体的分析结果，生成专业的监测分析报告。
"""

        # 构建用户消息
        user_message = f"""请生成监测分析报告。

## 知识库
### 法规
{json.dumps({k: v[:200] for k, v in list(knowledge_base.regulations.items())[:2]}, ensure_ascii=False)}

### 违规模式
{json.dumps({k: v[:200] for k, v in list(knowledge_base.patterns.items())[:2]}, ensure_ascii=False)}

## 任务信息
```json
{json.dumps(task_info or {}, ensure_ascii=False, indent=2)}
```

## 分析结果
```json
{json.dumps(analysis, ensure_ascii=False, indent=2)}
```

请生成专业的监测分析报告，使用Markdown格式，包括：
1. **执行概述**：哪些子智能体参与执行
2. **数据质量**：数据治理情况
3. **异常分析**：检测到的异常
4. **违规判定**：是否有违规，违规类型和嫌疑等级
5. **结论建议**：综合结论和建议措施
"""

        try:
            # 调用大模型
            logger.info(f"[LLM] 调用大模型生成报告")
            response = self.llm_client.chat(
                message=user_message,
                model_type="primary",
                system_prompt=system_prompt,
                temperature=0.0
            )
            logger.info(f"[LLM] 报告生成完成: {len(response)} 字符")
            return response
        except Exception as e:
            logger.error(f"[LLM] 大模型调用失败: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_template_report(analysis, task_info)

    def _build_report_prompt(self, master_identity: Dict[str, str],
                            knowledge_base: KnowledgeBase,
                            analysis: Dict[str, Any],
                            task_info: Dict[str, Any]) -> str:
        """构建大模型提示词"""
        # 提取主智能体身份摘要
        identity_summary = master_identity.get("IDENTITY", "")[:500]

        # 提取关键法规
        regulations_summary = ""
        for name, content in list(knowledge_base.regulations.items())[:2]:
            regulations_summary += f"\n## {name}\n{content[:200]}..."

        # 构建提示词
        prompt = f"""你是废水虚假排放智能监测主智能体。

{identity_summary}

## 知识库
{regulations_summary}

## 当前任务
{json.dumps(task_info or {}, ensure_ascii=False, indent=2)}

## 分析结果
{json.dumps(analysis, ensure_ascii=False, indent=2)}

## 任务
请基于以上信息，生成一份自然语言分析报告，包括：
1. **执行概述**：哪些子智能体参与执行
2. **数据质量**：数据治理情况
3. **异常分析**：检测到的异常
4. **违规判定**：是否有违规，违规类型和嫌疑等级
5. **结论建议**：综合结论和建议措施

报告格式要清晰，使用Markdown格式。
"""

        return prompt

    def _generate_template_report(self, analysis: Dict[str, Any],
                                  task_info: Dict[str, Any] = None) -> str:
        """
        使用模板生成报告（备用方案）

        Args:
            analysis: 分析结果
            task_info: 任务信息

        Returns:
            格式化报告
        """
        lines = []
        lines.append("# 废水虚假排放智能监测分析报告")
        lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("\n---\n")

        # 执行概述
        lines.append("## 一、执行概述")
        agents_executed = analysis.get("agents_executed", [])
        lines.append(f"\n参与子智能体: {', '.join(agents_executed)}")

        # 数据质量
        lines.append("\n## 二、数据质量")
        data_quality = analysis.get("data_quality", {})
        if data_quality:
            for key, value in data_quality.items():
                lines.append(f"- **{key}**: {value}")
        else:
            lines.append("- 数据质量信息不可用")

        # 异常分析
        lines.append("\n## 三、异常分析")
        anomalies = analysis.get("anomalies", [])
        if anomalies:
            lines.append(f"\n检测到 {len(anomalies)} 个异常：")
            for anom in anomalies[:5]:  # 最多显示5个
                lines.append(f"- **{anom.get('indicator', 'N/A')}**: "
                           f"{anom.get('type', 'N/A')} - {anom.get('value', 'N/A')}")
        else:
            lines.append("\n未检测到异常")

        # 违规判定
        lines.append("\n## 四、违规判定")
        violations = analysis.get("violations", [])
        suspicion_level = analysis.get("suspicion_level", "low")

        if violations:
            lines.append(f"\n**嫌疑等级**: {suspicion_level.upper()}")
            lines.append(f"\n检测到 {len(violations)} 个违规：")
            for vio in violations:
                lines.append(f"- **{vio.get('type', 'N/A')}** ({vio.get('level', 'N/A')}): "
                           f"{vio.get('message', 'N/A')}")
                if vio.get('legal_reference'):
                    lines.append(f"  - 法律依据: {vio['legal_reference']}")
        else:
            lines.append(f"\n**嫌疑等级**: {suspicion_level.upper()}")
            lines.append("\n未检测到违规")

        # 结论建议
        lines.append("\n## 五、结论建议")
        if analysis.get("has_violation"):
            lines.append("\n[WARN] **检测到违规行为，建议立即处理**")
            lines.append("- 通知现场管理人员核查")
            lines.append("- 记录违规证据")
            lines.append("- 启动应急预案（如需要）")
        elif analysis.get("has_anomaly"):
            lines.append("\n[ALERT] **检测到异常，建议关注**")
            lines.append("- 持续监测后续数据")
            lines.append("- 核查监测设备状态")
        else:
            lines.append("\n✓ **监测正常，未发现异常或违规**")

        lines.append("\n---\n")
        lines.append(f"*报告由废水虚假排放智能监测系统自动生成*")

        return "\n".join(lines)


# 便捷函数
def create_result_interpretation_module(llm_client=None) -> ResultInterpretationModule:
    """创建结果解释与输出模块"""
    return ResultInterpretationModule(llm_client=llm_client)


def interpret_execution_results(execution_results: Dict[str, Any],
                                task_info: Dict[str, Any] = None,
                                llm_client=None) -> Dict[str, Any]:
    """
    解释执行结果（便捷函数）

    Args:
        execution_results: 执行结果
        task_info: 任务信息
        llm_client: 大模型客户端（可选）

    Returns:
        解释结果
    """
    module = create_result_interpretation_module(llm_client)
    return module.interpret_results(execution_results, task_info)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("结果解释与输出模块测试")
    print("=" * 60)

    module = create_result_interpretation_module()

    # 模拟执行结果
    test_results = {
        "data-governance-agent": {
            "status": "success",
            "quality_report": {
                "completeness": 0.95,
                "records": 24
            }
        },
        "feature-analysis-agent": {
            "status": "success",
            "features": {
                "COD": {"mean": 45.2, "std": 5.3}
            }
        },
        "anomaly-detection-agent": {
            "status": "success",
            "has_anomaly": True,
            "anomalies": [
                {"indicator": "COD", "value": 75, "type": "exceedance", "limit": 50}
            ]
        },
        "rule-reasoning-agent": {
            "status": "success",
            "has_violation": True,
            "violations": [
                {
                    "type": "exceedance",
                    "level": "high",
                    "message": "COD超标: 75 > 50",
                    "legal_reference": "GB18918-2002一级A标准"
                }
            ],
            "suspicion_level": "high"
        }
    }

    test_task_info = {
        "task_id": "realtime_20260522_120000",
        "task_name": "实时监测数据分析",
        "timestamp": "2026-05-22T12:00:00"
    }

    result = module.interpret_results(test_results, test_task_info)

    print(f"状态: {result['status']}")
    print(f"\n报告:\n{result['report']}")

    print("\n" + "=" * 60)
    print("测试完成")

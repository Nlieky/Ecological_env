#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人机交互层 - 自然语言交互模块
功能：提供终端交互界面，接收监管人员的自然语言指令

专利位置：人机交互层（专利第21-22行）
- 提供自然语言输入接口
- 支持查询场景：违规检测、趋势分析、相关性分析、状态查询、报告生成
- 输入指令长度限制：500字符
"""

import os
import sys
import logging
from pathlib import Path
from typing import Tuple

# 添加项目路径
MIDDLEWARE_DIR = Path(__file__).parent
PROJECT_ROOT = MIDDLEWARE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "configs"))

from shared.configs.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class HumanComputerInterface:
    """人机交互层 - 自然语言交互模块"""

    def __init__(self):
        """初始化人机交互模块"""
        self.name = "人机交互层"
        self.version = "1.0.0"

        # 加载主智能体配置
        workspace_path = PROJECT_ROOT / "workspace"
        self.soul_content = open(workspace_path / "SOUL.md", 'r', encoding='utf-8').read()
        self.skill_content = open(workspace_path / "skills" / "orchestrator-core" / "SKILL.md", 'r', encoding='utf-8').read()
        self.agents_content = open(workspace_path / "AGENTS.md", 'r', encoding='utf-8').read()

        # 获取LLM客户端
        self.client = get_llm_client()

        # 输入长度限制（专利要求：500字符）
        self.max_input_length = 500

        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是废水虚假排放智能监测系统的主智能体。

## 你的身份（SOUL.md）
{self.soul_content[:2000]}...

## 你的能力（SKILL.md）
{self.skill_content[:2000]}...

## 子智能体配置（AGENTS.md）
{self.agents_content[:1500]}...

## 你的职责
1. 理解监管人员的自然语言查询
2. 识别意图类型（违规检测、趋势分析、相关性分析、状态查询、报告生成）
3. 提取关键实体（监测指标、时间范围、监测点位）
4. 规划需要调用的子智能体和执行计划
5. 以清晰的格式向监管人员反馈分析结果

## 支持的查询类型
- 违规检测：分析是否存在插瓶干扰、稀释排放、数据篡改、虚假停产等违规行为
- 趋势分析：分析指标的变化趋势、周期性、突变点
- 相关性分析：分析指标间的关联关系
- 状态查询：查询当前监测数据状态
- 报告生成：生成监测分析报告

## 输出格式
请以清晰、专业的自然语言回复监管人员，包括：
1. 监测概况（点位、时间、指标）
2. 分析发现
3. 结论与建议
"""

    def process_query(self, query: str) -> str:
        """
        处理用户查询

        Args:
            query: 用户输入的自然语言查询

        Returns:
            str: 主智能体的响应
        """
        try:
            # 构建用户提示词
            user_prompt = f"""监管人员查询：{query}

请分析此查询，识别意图、提取实体，并给出回复。"""

            # 调用LLM
            response = self.client.chat(
                user_prompt,
                system_prompt=self.build_system_prompt(),
                model_type="primary"
            )

            return response

        except Exception as e:
            logger.error(f"[ERROR] 处理查询失败: {e}")
            return f"抱歉，处理您的查询时出现错误：{str(e)}"

    def validate_input(self, query: str) -> Tuple[bool, str]:
        """
        验证输入

        Args:
            query: 用户输入

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if not query or query.strip() == "":
            return False, "输入不能为空"

        if len(query) > self.max_input_length:
            return False, f"输入长度超过限制（最大{self.max_input_length}字符）"

        return True, ""

    def show_welcome(self):
        """显示欢迎信息"""
        print("\n" + "=" * 60)
        print("  废水虚假排放智能监测系统 - 人机交互层")
        print("  Wastewater Fraud Detection System - HCI Layer")
        print("=" * 60)
        print("\n支持的查询类型：")
        print("  • 违规检测：分析是否存在插瓶干扰、稀释排放等违规行为")
        print("  • 趋势分析：分析指标的变化趋势、周期性、突变点")
        print("  • 相关性分析：分析指标间的关联关系")
        print("  • 状态查询：查询当前监测数据状态")
        print("  • 报告生成：生成监测分析报告")
        print("\n命令：")
        print("  /help    - 显示帮助信息")
        print("  /clear   - 清空对话历史")
        print("  /quit    - 退出系统")
        print("\n" + "-" * 60)

    def show_help(self):
        """显示帮助信息"""
        print("\n" + "=" * 60)
        print("  帮助信息")
        print("=" * 60)
        print("\n查询示例：")
        print("  • 分析最近24小时出水的COD异常情况")
        print("  • 检测是否存在插瓶干扰行为")
        print("  • 分析pH和COD的相关性")
        print("  • 查询当前监测状态")
        print("  • 生成最近一周的监测报告")
        print("\n支持的监测指标：")
        print("  • pH值、COD、氨氮(NH3-N)、总氮(TN)、总磷(TP)")
        print("\n支持的监测点位：")
        print("  • 进水、出水")
        print("\n命令：")
        print("  /help    - 显示此帮助信息")
        print("  /clear   - 清空对话历史")
        print("  /quit    - 退出系统")
        print("\n" + "-" * 60)

    def run(self):
        """运行交互循环"""
        self.show_welcome()

        conversation_history = []

        while True:
            try:
                # 获取用户输入
                query = input("\n[监管人员] >>> ").strip()

                # 处理命令
                if query.lower() == "/quit":
                    print("\n感谢使用废水虚假排放智能监测系统！")
                    break

                elif query.lower() == "/help":
                    self.show_help()
                    continue

                elif query.lower() == "/clear":
                    conversation_history = []
                    print("\n对话历史已清空。")
                    continue

                elif query == "":
                    continue

                # 验证输入
                is_valid, error_msg = self.validate_input(query)
                if not is_valid:
                    print(f"\n[系统提示] 输入无效：{error_msg}")
                    continue

                # 处理查询
                print("\n[系统] 正在分析...")
                response = self.process_query(query)

                # 显示响应
                print("\n[主智能体]")
                print("-" * 60)
                print(response)
                print("-" * 60)

                # 记录对话历史
                conversation_history.append({"query": query, "response": response})

            except KeyboardInterrupt:
                print("\n\n检测到中断信号，正在退出...")
                break

            except Exception as e:
                logger.error(f"[ERROR] 交互异常: {e}")
                print(f"\n[系统提示] 发生错误：{str(e)}")
                print("请重新输入或使用 /quit 退出。")


def main():
    """主函数"""
    interface = HumanComputerInterface()
    interface.run()


if __name__ == "__main__":
    main()

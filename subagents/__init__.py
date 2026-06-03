# Subagents package
# 处理连字符目录名到下划线模块名的映射

import sys
import os
from pathlib import Path

# 获取subagents目录路径
subagents_dir = Path(__file__).parent

# 映射：连字符目录名 -> 下划线模块名
agent_mappings = {
    'influent-monitoring-agent': 'influent_monitoring_agent',
    'effluent-monitoring-agent': 'effluent_monitoring_agent',
    'treatment-efficiency-agent': 'treatment_efficiency_agent',
    'process-diagnostics-agent': 'process_diagnostics_agent',
    'advisory-recommendation-agent': 'advisory_recommendation_agent',
    'interactive-query-agent': 'interactive_query_agent'
}

# 为每个智能体添加模块路径映射
for dir_name, module_name in agent_mappings.items():
    dir_path = subagents_dir / dir_name
    if dir_path.exists():
        # 将目录添加到sys.path，使用下划线模块名
        module_path = str(dir_path)
        if module_path not in sys.path:
            sys.path.insert(0, module_path)

# 导出智能体类（延迟导入，避免循环依赖）
def get_agent(agent_name):
    """获取智能体类"""
    from importlib import import_module

    # 映射到实际的目录名
    dir_name = agent_name.replace('_', '-')
    agent_dir = subagents_dir / dir_name

    if agent_dir.exists():
        # 动态导入
        try:
            module = import_module(f'{agent_name}.{agent_name.replace("_", "-")}')
            return getattr(module, f'{agent_name.replace("_", " ").title().replace(" ", "")}Agent', None)
        except ImportError:
            return None
    return None

__all__ = ['get_agent']

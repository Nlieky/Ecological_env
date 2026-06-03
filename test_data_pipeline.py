#!/usr/bin/env python3
"""测试多维数据感知流水线"""
import sys
from pathlib import Path

# 添加路径
project_root = Path(__file__).parent
agent_scripts = project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"
sys.path.insert(0, str(agent_scripts))

from data_pipeline import MultiDimensionalDataPipeline

# 创建测试数据
test_data = {
    "influent": {
        "监测时间": "2024-01-01 00:00",
        "pH值": 7.5,
        "化学需氧量浓度（毫克/升）": 450,
        "总氮浓度（毫克/升）": 45,
        "氨氮浓度（毫克/升）": 10,
        "总磷浓度（毫克/升）": 5,
        "流量（升/秒）": 300
    },
    "effluent": {
        "监测时间": "2024-01-01 02:00",
        "pH值": 7.8,
        "化学需氧量浓度（毫克/升）": 50,
        "总氮浓度（毫克/升）": 15,
        "氨氮浓度（毫克/升）": 2,
        "总磷浓度（毫克/升）": 0.5,
        "流量（升/秒）": 280,
        "悬浮物浓度（毫克/升）": 10
    },
    "timestamp": "2024-01-01T00:00:00"
}

# 测试流水线
print("=" * 60)
print("测试多维数据感知流水线")
print("=" * 60)

try:
    pipeline = MultiDimensionalDataPipeline()
    print("\n[OK] 流水线初始化成功")

    result = pipeline.process_stream_data(test_data)

    print("\n处理结果:")
    print(f"  状态: {result['status']}")
    print(f"  阶段数: {result['metrics']['stage_count']}")
    print(f"  分解类型: {result['output']['decomposed_types']}")

    print("\n标准化结果:")
    influent_std = result['output']['influent']['standardized']
    effluent_std = result['output']['effluent']['standardized']
    print(f"  进水标准化: {type(influent_std)}")
    print(f"  出水标准化: {type(effluent_std)}")

    print("\n清洗结果:")
    influent_cleaned = result['output']['influent']['cleaned']
    effluent_cleaned = result['output']['effluent']['cleaned']
    print(f"  进水清洗后: {len(influent_cleaned) if isinstance(influent_cleaned, list) else 'N/A'}条")
    print(f"  出水清洗后: {len(effluent_cleaned) if isinstance(effluent_cleaned, list) else 'N/A'}条")

    # 打印阶段详情
    print("\n阶段详情:")
    for stage_name, stage_result in result['stages'].items():
        print(f"  {stage_name}: {type(stage_result).__name__}")

    print("\n[OK] Test completed successfully!")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

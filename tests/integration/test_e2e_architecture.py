# tests/integration/test_e2e_architecture.py
"""
端到端架构集成测试
测试新架构的完整工作流
"""
import sys
from pathlib import Path

# 添加各模块路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator
from data_acquisition import DataAcquisitionModule
from alert_classifier import AlertClassifier
from work_order_generator import WorkOrderGenerator


def test_violation_detection_workflow():
    """测试违规检测完整工作流"""
    # 1. 初始化组件
    orchestrator = DynamicOrchestrator(
        registry_path=str(project_root / "shared" / "configs" / "agent_registry.yaml")
    )

    # 2. 创建任务
    task = {
        "task_type": "violation_detection",
        "task_id": "TEST-001",
        "data": {
            "influent": {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45},
            "effluent": {"pH值": 7.8, "化学需氧量浓度（毫克/升）": 50}
        }
    }

    # 3. 生成执行计划
    plan = orchestrator.create_execution_plan(task)

    assert plan.task_type == "violation_detection"
    assert len(plan.agents) == 4
    assert plan.agents[0].id == "multi-dimensional-data-perception-agent"
    assert plan.agents[-1].id == "disposition-execution-agent"


def test_data_perception_to_alert_workflow():
    """测试从数据感知到预警生成的简化工作流"""
    # 1. 数据获取
    data_acquisition = DataAcquisitionModule()
    raw_data = data_acquisition.acquire_from_csv(
        influent_path=str(project_root / "data" / "pollution_water_in.csv"),
        effluent_path=str(project_root / "data" / "pollution_water_out.csv"),
        limit=10
    )

    assert raw_data["influent_count"] == 10

    # 2. 模拟异常检测结果
    anomaly_result = {
        "confidence": 0.85,
        "anomalies": [
            {
                "type": "平稳异常",
                "indicator": "COD",
                "duration": "3h"
            }
        ]
    }

    # 3. 模拟违规判定结果
    violation_result = {
        "confidence": 0.92,
        "violation_type": "插瓶干扰",
        "suspicion_level": "high"
    }

    # 4. 预警分级
    alert_classifier = AlertClassifier()
    alert = alert_classifier.classify_alert(anomaly_result, violation_result)

    assert alert["level"] in ["general", "moderate", "serious"]

    # 5. 工单生成
    work_order_generator = WorkOrderGenerator()
    work_order = work_order_generator.generate_work_order(
        alert_info=alert,
        data_context={"anomaly_time_range": ["2024-05-29 02:00", "2024-05-29 05:00"]}
    )

    assert "id" in work_order
    assert "inspection_points" in work_order


def test_agent_registry_loading():
    """测试子智能体注册表加载"""
    orchestrator = DynamicOrchestrator(
        registry_path=str(project_root / "shared" / "configs" / "agent_registry.yaml")
    )

    # 验证所有智能体都已注册
    assert len(orchestrator.available_agents) == 4

    # 验证任务映射
    assert "violation_detection" in orchestrator.task_type_mapping
    assert len(orchestrator.task_type_mapping["violation_detection"]) == 4


def test_three_library_integration():
    """测试三库一体化概念验证"""
    # 验证配置文件存在
    # 知识库
    knowledge_path = project_root / "knowledge"
    assert knowledge_path.exists()

    # 算子库
    operators_path = project_root / "shared" / "operators"
    assert operators_path.exists()

    # 配置库
    configs_path = project_root / "shared" / "configs"
    assert (configs_path / "agent_registry.yaml").exists()
    assert (configs_path / "rule_config.yaml").exists()

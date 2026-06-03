# -*- coding: utf-8 -*-
"""
Simple Orchestrator-Core Pipeline Test
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Project path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Orchestrator-Core module path
orchestrator_scripts = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(orchestrator_scripts))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_test():
    """Run orchestrator-core test"""
    print("=" * 70)
    print("Orchestrator-Core Pipeline Test")
    print("=" * 70)

    from task_receiving_and_parsing import TaskReceivingAndParsingModule
    from execution_control import LLMAgentCoordinator
    from result_interpretation import ResultInterpretationModule

    # Initialize modules
    task_receiving = TaskReceivingAndParsingModule(llm_client=None)
    llm_coordinator = LLMAgentCoordinator(llm_client=None)
    result_interpretation = ResultInterpretationModule(llm_client=None)

    print("[INIT] All modules initialized successfully")

    # Test data: exceedance (COD > 50)
    data = {
        "influent": {
            "pH": 7.0,
            "COD": 100
        },
        "effluent": {
            "pH": 7.5,
            "COD": 75  # Exceeds limit of 50!
        },
        "timestamp": "2026-05-22T12:00:00"
    }

    print("\n--- Stage 1: Task Receiving and Parsing ---")
    parse_result = task_receiving.process(data)

    if parse_result['status'] != 'success':
        print("[FAIL] Task parsing failed")
        return False

    print("[OK] Task parsing successful")
    print(f"  Task ID: {parse_result['structured_task']['task_id']}")
    print(f"  Intent: {parse_result['intent'].intent_type}")

    print("\n--- Stage 2: LLM Coordinating Sub-Agents ---")
    structured_task = parse_result['structured_task']
    intent = parse_result['intent']

    execution_results = llm_coordinator.coordinate_all_agents(
        task=structured_task,
        analysis_scope=intent.analysis_scope
    )

    print(f"[OK] Sub-agents execution completed: {len(execution_results)}")
    for agent_id, result in execution_results.items():
        status = result.get('status', 'unknown')
        print(f"  - {agent_id}: {status}")

    print("\n--- Stage 3: Result Interpretation and Report ---")
    interpretation_result = result_interpretation.interpret_results(
        execution_results=execution_results,
        task_info={
            "task_id": structured_task['task_id'],
            "task_name": structured_task['task_name'],
            "timestamp": data['timestamp']
        }
    )

    print("[OK] Report generated")

    # Check results
    analysis = interpretation_result['analysis']
    print(f"\n--- Summary ---")
    print(f"  Agents executed: {len(analysis['agents_executed'])}")
    print(f"  Anomaly detected: {analysis.get('has_anomaly', False)}")
    print(f"  Violation detected: {analysis['has_violation']}")
    print(f"  Suspicion level: {analysis['suspicion_level']}")

    if analysis['has_violation']:
        print(f"\n  Violations found: {len(analysis['violations'])}")
        for vio in analysis['violations']:
            print(f"    - Type: {vio['type']}, Level: {vio['level']}")
            print(f"      Message: {vio['message']}")

    # Print report (safe version)
    print(f"\n--- Report ---")
    report = interpretation_result['report']
    # Replace Unicode characters that cause encoding issues
    try:
        print(report)
    except UnicodeEncodeError:
        # Fallback: print ASCII-safe version
        safe_report = report
        safe_report = safe_report.replace('', '[OK]').replace('[WARN]').replace('[ALERT]')
        safe_report = safe_report.replace('', '[OK]')
        print(safe_report.encode('ascii', 'replace').decode('ascii'))

    # Test passed if violation detected
    success = analysis['has_violation']

    print("\n" + "=" * 70)
    if success:
        print("[PASS] Test completed successfully")
    else:
        print("[FAIL] Test failed - expected violation not detected")
    print("=" * 70)

    return success


if __name__ == "__main__":
    try:
        success = run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

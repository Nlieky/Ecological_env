#!/usr/bin/env python
"""Verify DataAcquisitionModule implementation"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts'))

print("Verifying DataAcquisitionModule...")

try:
    from data_acquisition import DataAcquisitionModule, supported_sources
    print(f"[OK] Module imported successfully")
    print(f"[OK] DataAcquisitionModule.supported_sources = {DataAcquisitionModule.supported_sources}")
    print(f"[OK] Module-level supported_sources = {supported_sources}")

    # Check they match
    assert supported_sources == ["csv", "realtime_api", "database"], "supported_sources has wrong value"
    print(f"[OK] supported_sources has correct value")

    print("\n=== All checks passed! ===")
except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

#!/usr/bin/env python3
import json
import numpy as np
import sys
sys.path.insert(0, 'E:/project/Ecological_env')

# Test 1: Check if basic numpy types work
print("Test 1: Basic numpy types")
try:
    result = {"value": np.int64(123)}
    json_str = json.dumps(result)
    print(f"  Failed: {json_str}")
except Exception as e:
    print(f"  Error: {e}")

# Test 2: Check custom encoder
print("\nTest 2: Custom encoder")
class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if hasattr(obj, 'item'):
            return obj.item()
        return super().default(obj)

try:
    result = {"value": np.int64(123)}
    json_str = json.dumps(result, cls=NumpyJSONEncoder)
    print(f"  Success: {json_str}")
except Exception as e:
    print(f"  Error: {e}")

# Test 3: Complex nested structure
print("\nTest 3: Complex nested structure")
try:
    result = {
        "data": {
            "metrics": {
                "count": np.int64(100),
                "mean": np.float64(50.5)
            }
        }
    }
    json_str = json.dumps(result, cls=NumpyJSONEncoder)
    print(f"  Success: {json_str[:100]}")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

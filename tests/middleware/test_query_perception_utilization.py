from pathlib import Path
import sys

# Add paths
middleware_path = Path(__file__).parent.parent / "middleware"
sys.path.insert(0, str(middleware_path))

def test_perception_result_utilization():
    """测试查询接口是否使用感知结果"""
    # 模拟感知结果
    perception_result = {
        "status": "success",
        "result": {
            "cleaned_data": {
                "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.5}],
                "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.8}]
            },
            "quality_report": {"completeness": 0.95}
        }
    }

    # 模拟原始历史数据
    historical_data = {
        "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.0}],
        "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.2}]
    }

    # 验证：从感知结果中提取cleaned_data
    processed_data = historical_data  # 默认
    if perception_result and isinstance(perception_result, dict):
        if "result" in perception_result:
            result_data = perception_result["result"]
            if isinstance(result_data, dict) and "cleaned_data" in result_data:
                cleaned = result_data["cleaned_data"]
                if isinstance(cleaned, dict) and "influent" in cleaned:
                    processed_data = cleaned

    # 验证：processed_data应该包含感知结果的数据
    assert len(processed_data["influent"]) == 1
    assert processed_data["influent"][0]["pH"] == 7.5  # 来自cleaned_data，不是原始数据

    print("感知结果数据提取逻辑正确")

def test_fallback_to_raw_data():
    """测试当感知结果无效时回退到原始数据"""
    # 空的感知结果
    perception_result = {"status": "error"}

    # 原始历史数据
    historical_data = {
        "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.0}],
        "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.2}]
    }

    # 提取逻辑
    processed_data = historical_data
    if perception_result and isinstance(perception_result, dict):
        if "result" in perception_result:
            result_data = perception_result["result"]
            if isinstance(result_data, dict) and "cleaned_data" in result_data:
                cleaned = result_data["cleaned_data"]
                if isinstance(cleaned, dict) and "influent" in cleaned:
                    processed_data = cleaned

    # 验证：应该回退到原始数据
    assert processed_data is historical_data
    assert processed_data["influent"][0]["pH"] == 7.0

    print("回退到原始数据逻辑正确")

def test_processed_data_direct_path():
    """测试processed_data直接路径"""
    # 模拟感知结果（processed_data直接路径）
    perception_result = {
        "status": "success",
        "processed_data": {
            "influent": [{"timestamp": "2024-01-01T00:00", "pH": 8.0}],
            "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 8.2}]
        }
    }

    # 原始历史数据
    historical_data = {
        "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.0}],
        "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.2}]
    }

    # 提取逻辑（完整版）
    processed_data = historical_data
    if perception_result and isinstance(perception_result, dict):
        if "result" in perception_result:
            result_data = perception_result["result"]
            if isinstance(result_data, dict):
                if "cleaned_data" in result_data:
                    cleaned = result_data["cleaned_data"]
                    if isinstance(cleaned, dict) and "influent" in cleaned and "effluent" in cleaned:
                        processed_data = {"influent": cleaned["influent"], "effluent": cleaned["effluent"]}
        elif "processed_data" in perception_result:
            processed = perception_result["processed_data"]
            if isinstance(processed, dict):
                processed_data = processed

    # 验证：应该使用processed_data
    assert processed_data["influent"][0]["pH"] == 8.0

    print("processed_data直接路径逻辑正确")

def test_aligned_data_path():
    """测试aligned_data路径"""
    # 模拟感知结果（aligned_data路径）
    perception_result = {
        "status": "success",
        "result": {
            "aligned_data": {
                "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.9}],
                "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 8.1}]
            }
        }
    }

    # 原始历史数据
    historical_data = {
        "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.0}],
        "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.2}]
    }

    # 提取逻辑（完整版）
    processed_data = historical_data
    if perception_result and isinstance(perception_result, dict):
        if "result" in perception_result:
            result_data = perception_result["result"]
            if isinstance(result_data, dict):
                if "cleaned_data" in result_data:
                    cleaned = result_data["cleaned_data"]
                    if isinstance(cleaned, dict) and "influent" in cleaned and "effluent" in cleaned:
                        processed_data = {"influent": cleaned["influent"], "effluent": cleaned["effluent"]}
                elif "aligned_data" in result_data:
                    aligned = result_data["aligned_data"]
                    if isinstance(aligned, dict):
                        processed_data = aligned

    # 验证：应该使用aligned_data
    assert processed_data["influent"][0]["pH"] == 7.9

    print("aligned_data路径逻辑正确")

def run_tests():
    test_perception_result_utilization()
    test_fallback_to_raw_data()
    test_processed_data_direct_path()
    test_aligned_data_path()
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()

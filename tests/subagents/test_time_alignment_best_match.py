from pathlib import Path
import sys

subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from time_alignment import TimeAlignmentModule

def test_best_time_match_selection_pandas():
    """测试pandas方法选择时间差最小的匹配"""
    aligner = TimeAlignmentModule(default_lag_hours=2)

    influent = [
        {"监测时间": "2024-01-01 00:00", "pH": 7.5}
    ]

    # 出水有多个匹配（5分钟容差内）
    effluent = [
        {"监测时间": "2024-01-01 02:03", "pH": 7.8},  # 时间差3分钟
        {"监测时间": "2024-01-01 02:01", "pH": 7.7},  # 时间差1分钟（最佳）
        {"监测时间": "2024-01-01 02:04", "pH": 7.9},  # 时间差4分钟
    ]

    result = aligner.align_with_lag(influent, effluent)

    # 验证：应该选择时间差最小的（02:01）
    assert result["alignment_count"] == 1
    aligned_pair = result["aligned_pairs"][0]
    assert aligned_pair["effluent_time"] == "2024-01-01 02:01"
    # 验证时间差记录
    if "time_diff_seconds" in aligned_pair:
        assert aligned_pair["time_diff_seconds"] == 60  # 1分钟 = 60秒

    print("Pandas最佳时间匹配选择正确")

def test_best_time_match_selection_no_pandas():
    """测试非pandas方法选择时间差最小的匹配"""
    aligner = TimeAlignmentModule(default_lag_hours=2)

    influent = [
        {"监测时间": "2024-01-01 00:00", "pH": 7.5}
    ]

    # 出水有多个匹配（容差300秒）
    effluent = [
        {"监测时间": "2024-01-01 02:03", "pH": 7.8},  # 时间差180秒
        {"监测时间": "2024-01-01 02:01", "pH": 7.7},  # 时间差60秒（最佳）
        {"监测时间": "2024-01-01 02:04", "pH": 7.9},  # 时间差240秒
    ]

    result = aligner.align_with_lag(influent, effluent)

    # 验证：应该选择时间差最小的（02:01）
    assert result["alignment_count"] == 1
    aligned_pair = result["aligned_pairs"][0]
    assert aligned_pair["effluent_time"] == "2024-01-01 02:01"
    assert aligned_pair["time_diff_seconds"] == 60

    print("非Pandas最佳时间匹配选择正确")

def run_tests():
    test_best_time_match_selection_pandas()
    test_best_time_match_selection_no_pandas()
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()

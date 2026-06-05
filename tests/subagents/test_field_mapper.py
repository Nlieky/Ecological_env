from pathlib import Path
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from standardization import FieldMapper

def test_exact_match():
    """测试精确匹配优先于正则匹配"""
    assert FieldMapper.map_field("pH值") == "pH"
    assert FieldMapper.map_field("化学需氧量浓度（毫克/升）") == "COD"
    assert FieldMapper.map_field("总氮浓度（毫克/升）") == "TN"
    print("✅ test_exact_match passed")

def test_regex_match_variants():
    """测试正则匹配处理字段名变体"""
    # 测试带单位的变体 (mg/L与中文混合)
    assert FieldMapper.map_field("化学需氧量浓度（mg/L）") == "COD"
    assert FieldMapper.map_field("pH（单位）") == "pH"

    # 测试带其他文字的变体 - 匹配REGEX_PATTERNS中的模式
    assert FieldMapper.map_field("水体pH值") == "pH"
    assert FieldMapper.map_field("废水化学需氧量指标") == "COD"
    assert FieldMapper.map_field("总氮含量") == "TN"
    assert FieldMapper.map_field("氨氮数值") == "NH3_N"

    # 注意: "COD浓度" 不会匹配，因为REGEX模式需要"化学需氧量"
    assert FieldMapper.map_field("COD浓度") == "COD浓度"  # 保持原样
    print("✅ test_regex_match_variants passed")

def test_unmapped_fields():
    """测试未映射字段保持原样"""
    assert FieldMapper.map_field("unknown_field") == "unknown_field"
    assert FieldMapper.map_field("random_metric") == "random_metric"
    assert FieldMapper.map_field("") == ""
    print("✅ test_unmapped_fields passed")

def test_exact_match_priority():
    """验证精确匹配优先于正则匹配"""
    # "化学需氧量浓度" 在EXACT_MAPPING中，应该优先使用精确匹配
    result = FieldMapper.map_field("化学需氧量浓度")
    assert result == "COD"
    print("✅ test_exact_match_priority passed")

def test_get_unmapped_fields():
    """测试获取未映射字段列表"""
    field_names = ["pH值", "unknown_field", "COD浓度", "random_metric", "总氮浓度"]
    unmapped = FieldMapper.get_unmapped_fields(field_names)

    # pH值, 总氮浓度 应该被映射
    # unknown_field, random_metric, COD浓度 应该未映射 (COD浓度不在EXACT_MAPPING中)
    assert "unknown_field" in unmapped
    assert "random_metric" in unmapped
    assert "COD浓度" in unmapped  # COD浓度没有精确匹配也不匹配REGEX
    assert "pH值" not in unmapped
    assert "总氮浓度" not in unmapped
    print("✅ test_get_unmapped_fields passed")

def test_all_standard_fields():
    """测试所有标准字段的映射"""
    standard_mappings = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "总氮浓度（毫克/升）": "TN",
        "氨氮浓度（毫克/升）": "NH3_N",
        "总磷浓度（毫克/升）": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "流量（升/秒）": "flow_rate",
        "排放量（吨）": "discharge_volume"
    }

    for original, expected in standard_mappings.items():
        result = FieldMapper.map_field(original)
        assert result == expected, f"Expected {expected} for {original}, got {result}"

    print("✅ test_all_standard_fields passed")

def run_tests():
    """运行所有测试"""
    test_exact_match()
    test_regex_match_variants()
    test_unmapped_fields()
    test_exact_match_priority()
    test_get_unmapped_fields()
    test_all_standard_fields()
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
